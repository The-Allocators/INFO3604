from ortools.sat.python import cp_model
from datetime import datetime, timedelta, time
from flask import jsonify

from App.models import (
    Schedule, Shift, Student, HelpDeskAssistant, 
    CourseCapability, Availability, ShiftCourseDemand, 
    Allocation, Course
)
from App.database import db
from App.controllers.notification import notify_schedule_published

def help_desk_scheduler(start_date=None, end_date=None, week_number=None):
    """
    Generate a help desk schedule using actual availability data from the database.
    
    Args:
        start_date: Start date for the schedule (datetime object)
        end_date: End date for the schedule (datetime object)
        week_number: Week number for this schedule
        
    Returns:
        Dictionary with the schedule information
    """
    try:
        # --- Get actual data from the database ---
        # If no dates provided, default to next week
        if not start_date:
            today = datetime.utcnow()
            # Get the next Monday
            days_ahead = (0 - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7  # If today is Monday, go to next Monday
            start_date = today + timedelta(days=days_ahead)
            
        if not end_date:
            # Default to 5 days (Monday-Friday)
            end_date = start_date + timedelta(days=4)
            
        if not week_number:
            week_number = start_date.isocalendar()[1]  # ISO week number
            
        print(f"Generating schedule for week {week_number}: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Get all active help desk assistants
        assistants = HelpDeskAssistant.query.filter_by(active=True).all()
        if not assistants:
            return {
                'status': 'error',
                'message': 'No active assistants found'
            }
        
        # Map to keep track of assistant names by username
        assistant_names = {}
        for assistant in assistants:
            student = Student.query.get(assistant.username)
            if student:
                assistant_names[assistant.username] = student.name if student.name else assistant.username
            else:
                assistant_names[assistant.username] = assistant.username
        
        # Get availability for each assistant
        availability_map = {}
        for assistant in assistants:
            # Get all availability records for this assistant
            availabilities = Availability.query.filter_by(username=assistant.username).all()
            
            # Initialize empty availability grid (5 days x 8 hours)
            # Represents Monday-Friday, 9am-5pm
            assistant_availability = [[0 for _ in range(8)] for _ in range(5)]
            
            # Fill in the availability grid
            for avail in availabilities:
                day = avail.day_of_week  # 0=Monday, 4=Friday
                if day < 0 or day > 4:  # Skip weekends or invalid days
                    continue
                    
                # Convert time to hour index (9am = 0, 10am = 1, etc.)
                if avail.start_time:
                    start_hour = avail.start_time.hour
                    if start_hour >= 9 and start_hour < 17:
                        hour_idx = start_hour - 9
                        # Mark as available (assuming 1-hour slots)
                        assistant_availability[day][hour_idx] = 1
            
            # Store the availability grid for this assistant
            availability_map[assistant.username] = assistant_availability
        
        # --- Setup CP-SAT model ---
        model = cp_model.CpModel()
        
        # Get course capabilities for each assistant
        course_capabilities = {}
        all_courses = [course.code for course in Course.query.all()]
        
        for assistant in assistants:
            # Get all course capabilities for this assistant
            capabilities = CourseCapability.query.filter_by(assistant_username=assistant.username).all()
            
            # Initialize with all courses set to 0 (not capable)
            assistant_capabilities = {course: 0 for course in all_courses}
            
            # Mark the courses this assistant can help with
            for capability in capabilities:
                assistant_capabilities[capability.course_code] = 1
                
            # Store the capabilities for this assistant
            course_capabilities[assistant.username] = assistant_capabilities
        
        # Initialize parameters for the model
        I = len(assistants)  # Number of assistants
        J = 5 * 8  # Number of shifts (5 days x 8 hours)
        K = len(all_courses)  # Number of courses
        
        # Create a mapping from assistant username to index
        assistant_index = {assistant.username: i for i, assistant in enumerate(assistants)}
        
        # Create a mapping from course code to index
        course_index = {course: k for k, course in enumerate(all_courses)}
        
        # Initialize t_i_k matrix (staff i can help with course k)
        t = {}
        for i, assistant in enumerate(assistants):
            for k, course in enumerate(all_courses):
                capability = course_capabilities[assistant.username].get(course, 0)
                t[i, k] = capability
        
        # Initialize a_i_j matrix (staff i is available for shift j)
        a = {}
        for i, assistant in enumerate(assistants):
            availability = availability_map[assistant.username]
            for day in range(5):  # Monday to Friday
                for hour in range(8):  # 9am to 5pm
                    j = day * 8 + hour  # Shift index
                    a[i, j] = availability[day][hour]
        
        # Initialize d_j_k matrix (desired tutors for shift j and course k)
        # Default to 2 tutors for each course in each shift
        d = {}
        for j in range(J):
            for k in range(K):
                d[j, k] = 2
                
        # Initialize w_j_k matrix (weights for each shift and course)
        # Default weight = d_j_k
        w = {}
        for j in range(J):
            for k in range(K):
                w[j, k] = d[j, k]
        
        # Initialize minimum shifts per assistant (r_i)
        # Use the hours_minimum from the database
        r = {}
        for i, assistant in enumerate(assistants):
            r[i] = assistant.hours_minimum
        
        # --- Create Variables ---
        x = {}  # x[i, j] = 1 if staff i is assigned to shift j
        for i in range(I):
            for j in range(J):
                x[i, j] = model.NewBoolVar(f'x_{i}_{j}')
        
        # --- Objective Function ---
        objective_terms = []
        for j in range(J):
            for k in range(K):
                # For each shift and course, calculate the number of assigned tutors who can teach it
                assigned_tutors = sum(x[i, j] * t[i, k] for i in range(I))
                
                # Create a variable for the shortfall
                shortfall = model.NewIntVar(0, I, f'shortfall_{j}_{k}')
                model.Add(shortfall >= d[j, k] - assigned_tutors)
                
                # Add weighted shortfall to objective
                objective_terms.append(shortfall * w[j, k])
        
        model.Minimize(sum(objective_terms))
        
        # --- Constraints ---
        # Constraint 1: Σxij * tik ≤ djk for all j,k pairs
        for j in range(J):
            for k in range(K):
                constraint = sum(x[i, j] * t[i, k] for i in range(I))
                model.Add(constraint <= d[j, k])
        
        # Constraint 2: Σxij >= r_i for all i
        for i in range(I):
            constraint = sum(x[i, j] for j in range(J))
            model.Add(constraint >= r[i])
        
        # Constraint 3: Each shift must have at least 2 assistants
        for j in range(J):
            constraint = sum(x[i, j] for i in range(I))
            model.Add(constraint >= 2)
        
        # Constraint 4: xij <= aij for all i,j
        for i in range(I):
            for j in range(J):
                model.Add(x[i, j] <= a[i, j])
        
        # --- Solve ---
        solver = cp_model.CpSolver()
        status = solver.Solve(model)
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            # Create a mapping from staff index to name/username
            staff_index = {i: assistant.username for i, assistant in enumerate(assistants)}
            staff_names = {i: assistant_names[assistant.username] for i, assistant in enumerate(assistants)}
            
            # Create a schedule assignment by shift
            assignments = {}
            for j in range(J):
                staff_assigned = []
                for i in range(I):
                    if solver.Value(x[i, j]) == 1:
                        staff_assigned.append(i)
                assignments[j] = staff_assigned
            
            # Create a new Schedule object
            schedule = Schedule(week_number, start_date, end_date)
            db.session.add(schedule)
            db.session.flush()  # Get the schedule ID
            
            # Create shift objects and allocations
            for day in range(5):  # Monday to Friday
                date = start_date + timedelta(days=day)
                for hour in range(8):  # 9am to 5pm
                    hour_time = hour + 9  # Convert to actual hour (9am to 5pm)
                    
                    # Create the shift
                    shift_start = datetime.combine(date.date(), datetime.min.time()) + timedelta(hours=hour_time)
                    shift_end = shift_start + timedelta(hours=1)
                    
                    shift = Shift(date, shift_start, shift_end, schedule.id)
                    db.session.add(shift)
                    db.session.flush()  # Get the shift ID
                    
                    # Assign staff to this shift
                    j = day * 8 + hour  # Shift index
                    for i in assignments.get(j, []):
                        assistant_username = staff_index[i]
                        allocation = Allocation(assistant_username, shift.id, schedule.id)
                        db.session.add(allocation)
            
            # Commit the database changes
            db.session.commit()
            
            return {
                'status': 'success',
                'schedule_id': schedule.id,
                'staff_index': staff_names,
                'assignments': assignments,
                'message': 'Schedule generated successfully'
            }
        else:
            message = 'No solution found.'
            if status == cp_model.INFEASIBLE:
                message = 'Problem is infeasible with current constraints.'
            elif status == cp_model.MODEL_INVALID:
                message = 'Model is invalid.'
            elif status == cp_model.UNKNOWN:
                message = 'Solver status is unknown.'
            
            return {
                'status': 'error',
                'message': message
            }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        return {
            'status': 'error',
            'message': str(e)
        }

def generate_help_desk_schedule(week_number, start_date, semester_id=None):
    """
    A wrapper function that calls the new help_desk_scheduler and handles any additional setup.
    
    Args:
        week_number: The week number for this schedule
        start_date: The start date for this schedule (datetime object)
        semester_id: Optional semester ID
    
    Returns:
        A dictionary with the schedule information
    """
    try:
        # Calculate end date (5 days from start_date)
        end_date = start_date + timedelta(days=4)
        
        # Call the updated scheduler
        result = help_desk_scheduler(start_date, end_date, week_number)
        
        # Handle errors
        if result['status'] != 'success':
            return result
        
        # Schedule was created successfully
        return {
            "status": "success",
            "schedule_id": result['schedule_id'],
            "message": "Schedule generated successfully"
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        return {
            "status": "error",
            "message": str(e)
        }

def publish_schedule(schedule_id):
    """Publish a schedule and notify all assigned staff"""
    try:
        schedule = Schedule.query.get(schedule_id)
        if not schedule:
            return {"status": "error", "message": "Schedule not found"}
            
        if schedule.publish():
            # Get all unique students assigned to this schedule
            allocations = Allocation.query.filter_by(schedule_id=schedule_id).all()
            students = set(allocation.username for allocation in allocations)
            
            # Notify each student
            for username in students:
                notify_schedule_published(username, schedule.week_number)
                
            return {"status": "success", "message": "Schedule published and notifications sent"}
        else:
            return {"status": "error", "message": "Schedule is already published"}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_schedule_for_week(week_number, semester_id=None):
    """Get a detailed schedule for a specific week"""
    query = Schedule.query.filter_by(week_number=week_number)
    if semester_id:
        query = query.filter_by(semester_id=semester_id)
    
    schedule = query.first()
    if not schedule:
        return None
        
    # Format the schedule for display
    shifts_by_day = {}
    
    for shift in schedule.shifts:
        day_idx = shift.date.weekday()  # 0=Monday, 6=Sunday
        if day_idx >= 5:  # Skip weekend shifts
            continue
            
        hour = shift.start_time.hour
        
        if day_idx not in shifts_by_day:
            shifts_by_day[day_idx] = {}
            
        shifts_by_day[day_idx][hour] = {
            "shift_id": shift.id,
            "time": shift.formatted_time(),
            "assistants": get_assistants_for_shift(shift.id)
        }
    
    # Format into days array with shifts
    days = []
    for day_idx in range(5):  # Monday to Friday
        day_date = schedule.start_date + timedelta(days=day_idx)
        day_shifts = []
        
        if day_idx in shifts_by_day:
            for hour in range(9, 17):  # 9am to 4pm
                if hour in shifts_by_day[day_idx]:
                    day_shifts.append(shifts_by_day[day_idx][hour])
                else:
                    day_shifts.append({
                        "shift_id": None,
                        "time": f"{hour}:00 - {hour+1}:00",
                        "assistants": []
                    })
        
        days.append({
            "day": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"][day_idx],
            "date": day_date.strftime("%d %b"),
            "shifts": day_shifts
        })
    
    return {
        "schedule_id": schedule.id,
        "week_number": schedule.week_number,
        "date_range": schedule.get_formatted_date_range(),
        "is_published": schedule.is_published,
        "days": days
    }

def get_assistants_for_shift(shift_id):
    """Get all assistants assigned to a specific shift"""
    allocations = Allocation.query.filter_by(shift_id=shift_id).all()
    assistants = []
    
    for allocation in allocations:
        student = Student.query.get(allocation.username)
        if student:
            assistants.append({
                "username": student.username,
                "name": student.get_name(),
                "degree": student.degree
            })
    
    return assistants

def update_schedule_and_publish(schedule_id, schedule_data):
    """Update a schedule and automatically publish it to all students"""
    try:
        print(f"Updating schedule ID: {schedule_id}")
        
        # Get the schedule
        schedule = Schedule.query.get(schedule_id)
        if not schedule:
            return {"status": "error", "message": "Schedule not found"}
        
        # Delete existing allocations for this schedule
        old_allocations = Allocation.query.filter_by(schedule_id=schedule_id).all()
        print(f"Deleting {len(old_allocations)} old allocations")
        Allocation.query.filter_by(schedule_id=schedule_id).delete()
        db.session.commit()
        
        # Process each day and shift
        total_allocations = 0
        for day_idx, day_data in enumerate(schedule_data):
            day_name = day_data.get('day')
            shifts = day_data.get('shifts', [])
            
            print(f"Processing day {day_idx} ({day_name}): {len(shifts)} shifts")
            
            for time_idx, shift_data in enumerate(shifts):
                time_slot = shift_data.get('time')
                staff_ids = shift_data.get('staff', [])
                
                if staff_ids:
                    print(f"  - Shift at {time_slot}: {len(staff_ids)} staff members")
                
                # Find the corresponding shift
                date = schedule.start_date + timedelta(days=day_idx)
                hour = time_idx + 9  # 9am to 4pm
                
                shift = Shift.query.filter_by(
                    schedule_id=schedule_id,
                    date=date,
                ).filter(
                    Shift.start_time.between(
                        datetime.combine(date.date(), time(hour=hour)),
                        datetime.combine(date.date(), time(hour=hour, minute=15))
                    )
                ).first()
                
                if not shift and staff_ids:
                    # If no shift exists but we have staff assigned, create a new shift
                    print(f"    - Creating new shift for {date.date()} at {hour}:00")
                    shift_start = datetime.combine(date.date(), time(hour=hour))
                    shift_end = datetime.combine(date.date(), time(hour=hour+1))
                    shift = Shift(date, shift_start, shift_end, schedule_id)
                    db.session.add(shift)
                    db.session.flush()  # Get the shift ID
                elif not shift or not staff_ids:
                    # Skip if no shift and no staff
                    continue
                else:
                    print(f"    - Found existing shift ID {shift.id}")
                
                # Create allocations for each staff member
                for staff_id in staff_ids:
                    allocation = Allocation(staff_id, shift.id, schedule_id)
                    db.session.add(allocation)
                    total_allocations += 1
        
        # Explicitly set the schedule to published
        if not schedule.is_published:
            print(f"Publishing schedule {schedule_id}")
            schedule.is_published = True
            db.session.add(schedule)
        else:
            print(f"Schedule {schedule_id} was already published")
        
        # Commit all changes
        db.session.commit()
        print(f"Saved {total_allocations} allocations and published schedule")
        
        # Notify all assigned staff
        from App.controllers.notification import notify_schedule_published
        
        # Get all unique students assigned to this schedule
        allocations = Allocation.query.filter_by(schedule_id=schedule_id).all()
        students = set(allocation.username for allocation in allocations)
        
        # Notify each student
        for username in students:
            notify_schedule_published(username, schedule.week_number)
            print(f"Sent notification to {username}")
        
        return {
            "status": "success",
            "message": "Schedule updated and published successfully",
            "schedule_id": schedule_id
        }
    
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        
        return {
            "status": "error",
            "message": f"Error updating schedule: {str(e)}"
        }