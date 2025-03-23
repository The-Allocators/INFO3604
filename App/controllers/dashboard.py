from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user
from App.middleware import volunteer_required
from App.models import Student, HelpDeskAssistant, Shift, Allocation, TimeEntry, Schedule
from App.database import db
from datetime import datetime, timedelta

def get_dashboard_data(username):
    """Get all required data for the volunteer dashboard"""
    try:
        print(f"Fetching dashboard data for user: {username}")
        
        # Get current date and time
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get student info
        student = Student.query.get(username)
        if not student:
            print(f"Student with username {username} not found")
            return None
        
        print(f"Fetching next shift for {username}...")
        # 1. Get the user's next scheduled shift
        next_shift = get_next_shift(username, now)
        
        print(f"Fetching upcoming shifts for {username}...")
        # 2. Get the user's upcoming shifts (my schedule section)
        my_shifts = get_my_upcoming_shifts(username, today)
        
        print(f"Fetching full schedule...")
        # 3. Get the full schedule for all staff
        full_schedule = get_full_schedule(today)
        
        # Log some useful debugging info
        print(f"Dashboard data summary for {username}:")
        print(f"- Next shift: {next_shift['date']} {next_shift['time'] if 'time' in next_shift else 'No time'}")
        print(f"- Upcoming shifts: {len(my_shifts)}")
        
        return {
            'student': student,
            'next_shift': next_shift,
            'my_shifts': my_shifts,
            'full_schedule': full_schedule
        }
    except Exception as e:
        print(f"Error getting dashboard data: {e}")
        import traceback
        traceback.print_exc()
        
        # Return at least a minimal set of valid data
        return {
            'student': Student.query.get(username),
            'next_shift': {"date": "Error loading shifts", "time": "", "starts_now": False},
            'my_shifts': [],
            'full_schedule': {
                'days_of_week': ['MON', 'TUE', 'WED', 'THUR', 'FRI'],
                'time_slots': ['9:00 am', '10:00 am', '11:00 am', '12:00 pm', '1:00 pm', '2:00 pm', '3:00 pm', '4:00 pm'],
                'staff_schedule': {}
            }
        }

def get_next_shift(username, now):
    """Get the next shift for this user"""
    try:
        # Find the next scheduled shift for this user
        # First check for an active shift (currently happening)
        active_allocation = db.session.query(Allocation, Shift)\
            .join(Shift, Allocation.shift_id == Shift.id)\
            .filter(
                Allocation.username == username,
                Shift.start_time <= now,
                Shift.end_time >= now
            )\
            .first()
        
        if active_allocation:
            allocation, shift = active_allocation
            
            # Format the currently active shift
            return {
                "date": shift.date.strftime("%d %B, %Y"),
                "time": f"{shift.start_time.strftime('%I:%M %p')} to {shift.end_time.strftime('%I:%M %p')}",
                "starts_now": True,
                "time_until": ""
            }
        
        # If no active shift, find the next upcoming shift
        next_allocation = db.session.query(Allocation, Shift)\
            .join(Shift, Allocation.shift_id == Shift.id)\
            .filter(
                Allocation.username == username,
                Shift.start_time > now
            )\
            .order_by(Shift.start_time)\
            .first()
        
        if not next_allocation:
            # No upcoming shifts found
            return {
                "date": "No upcoming shifts",
                "time": "",
                "starts_now": False,
                "time_until": ""
            }
        
        allocation, shift = next_allocation
        
        # Calculate time until shift starts
        time_until = ""
        time_diff = shift.start_time - now
        
        # Convert to hours and minutes
        hours = time_diff.total_seconds() // 3600
        minutes = (time_diff.total_seconds() % 3600) // 60
        
        if hours > 0:
            time_until = f"{int(hours)} hours"
            if minutes > 0:
                time_until += f" {int(minutes)} minutes"
        else:
            time_until = f"{int(minutes)} minutes"
        
        # Format the next shift data
        return {
            "date": shift.date.strftime("%d %B, %Y"),
            "time": f"{shift.start_time.strftime('%I:%M %p')} to {shift.end_time.strftime('%I:%M %p')}",
            "starts_now": False,
            "time_until": time_until
        }
        
    except Exception as e:
        print(f"Error getting next shift: {e}")
        import traceback
        traceback.print_exc()
        return {
            "date": "No upcoming shifts",
            "time": "",
            "starts_now": False,
            "time_until": ""
        }

def get_my_upcoming_shifts(username, today):
    """Get the user's upcoming shifts for the next two weeks"""
    try:
        # Look ahead for the next 14 days to show more upcoming shifts
        next_two_weeks = today + timedelta(days=14)
        
        # Find all published schedules
        published_schedules = Schedule.query.filter(
            Schedule.is_published == True
        ).order_by(Schedule.id.desc()).all()
        
        published_schedule_ids = [s.id for s in published_schedules]
        
        # Query allocations for this user from published schedules
        allocations = db.session.query(Allocation, Shift)\
            .join(Shift, Allocation.shift_id == Shift.id)\
            .filter(
                Allocation.username == username,
                Allocation.schedule_id.in_(published_schedule_ids) if published_schedule_ids else False,
                Shift.date >= today,
                Shift.date <= next_two_weeks
            )\
            .order_by(Shift.date, Shift.start_time)\
            .all()
        
        # If no allocations found in published schedules, try direct shift allocations
        if not allocations:
            print(f"No allocations in published schedules for {username}, trying direct shift allocations")
            allocations = db.session.query(Allocation, Shift)\
                .join(Shift, Allocation.shift_id == Shift.id)\
                .filter(
                    Allocation.username == username,
                    Shift.date >= today,
                    Shift.date <= next_two_weeks
                )\
                .order_by(Shift.date, Shift.start_time)\
                .all()
        
        # Format the shifts
        my_shifts = []
        for allocation, shift in allocations:
            try:
                # Ensure shifts have date and time values before formatting
                if shift.date and shift.start_time and shift.end_time:
                    my_shifts.append({
                        "date": shift.date.strftime("%d %b"),
                        "time": f"{shift.start_time.strftime('%I:%M %p')} to {shift.end_time.strftime('%I:%M %p')}"
                    })
            except Exception as e:
                print(f"Error formatting shift: {e}")
                continue
        
        print(f"Found {len(my_shifts)} upcoming shifts for {username}")
        return my_shifts
        
    except Exception as e:
        print(f"Error getting upcoming shifts: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_full_schedule(today):
    """Get the full schedule for all staff - clean version without hardcoded defaults"""
    try:
        print(f"Getting full schedule for {today.strftime('%Y-%m-%d')}")
        
        # Prepare the staff schedule structure
        days_of_week = ['MON', 'TUE', 'WED', 'THUR', 'FRI']
        time_slots = ['9:00 am', '10:00 am', '11:00 am', '12:00 pm', '1:00 pm', '2:00 pm', '3:00 pm', '4:00 pm']
        
        # Initialize empty schedule grid
        staff_schedule = {}
        for time_slot in time_slots:
            staff_schedule[time_slot] = {day: [] for day in days_of_week}
        
        # Find the most recent published schedule
        latest_schedule = Schedule.query.filter(
            Schedule.is_published == True
        ).order_by(Schedule.id.desc()).first()
        
        if latest_schedule:
            print(f"Found published schedule: ID={latest_schedule.id}")
            
            # Get all shifts for this schedule
            shifts = Shift.query.filter_by(schedule_id=latest_schedule.id).all()
            print(f"Found {len(shifts)} shifts in schedule")
            
            # Process each shift
            for shift in shifts:
                try:
                    # Skip if shift has no date or time
                    if not shift.date or not shift.start_time:
                        continue
                        
                    # Get the day of week (0 = Monday, 4 = Friday)
                    day_idx = shift.date.weekday()
                    if day_idx > 4:  # Skip weekends
                        continue
                        
                    day = days_of_week[day_idx]
                    
                    # Get the hour and map to time slot
                    hour = shift.start_time.hour
                    time_slot = None
                    
                    # Map hour to time slot
                    if hour == 9:
                        time_slot = "9:00 am"
                    elif hour == 10:
                        time_slot = "10:00 am"
                    elif hour == 11:
                        time_slot = "11:00 am"
                    elif hour == 12:
                        time_slot = "12:00 pm"
                    elif hour == 13:
                        time_slot = "1:00 pm"
                    elif hour == 14:
                        time_slot = "2:00 pm"
                    elif hour == 15:
                        time_slot = "3:00 pm"
                    elif hour == 16:
                        time_slot = "4:00 pm"
                    
                    if not time_slot:
                        continue
                    
                    # Get allocations for this shift
                    allocations = Allocation.query.filter_by(shift_id=shift.id).all()
                    print(f"Shift {shift.id} on {day} at {time_slot} has {len(allocations)} allocations")
                    
                    # Get student names
                    for allocation in allocations:
                        student = Student.query.get(allocation.username)
                        name = student.name if student and student.name else allocation.username
                        
                        # Add to schedule grid
                        if time_slot in staff_schedule and day in staff_schedule[time_slot]:
                            staff_schedule[time_slot][day].append(name)
                            print(f"Added {name} to {day} at {time_slot}")
                        
                except Exception as e:
                    print(f"Error processing shift {shift.id}: {e}")
                    continue
        else:
            print("No published schedule found")
        
        # Print the full schedule for debugging
        print("Final schedule:")
        for time_slot, days in staff_schedule.items():
            for day, staff in days.items():
                if staff:
                    print(f"{day} {time_slot}: {', '.join(staff)}")
                    
        return {
            'days_of_week': days_of_week,
            'time_slots': time_slots,
            'staff_schedule': staff_schedule
        }
        
    except Exception as e:
        print(f"Error getting full schedule: {e}")
        import traceback
        traceback.print_exc()
        
        # Return empty schedule structure
        days_of_week = ['MON', 'TUE', 'WED', 'THUR', 'FRI']
        time_slots = ['9:00 am', '10:00 am', '11:00 am', '12:00 pm', '1:00 pm', '2:00 pm', '3:00 pm', '4:00 pm']
        
        # Initialize empty staff schedule
        staff_schedule = {}
        for time_slot in time_slots:
            staff_schedule[time_slot] = {day: [] for day in days_of_week}
        
        return {
            'days_of_week': days_of_week,
            'time_slots': time_slots,
            'staff_schedule': staff_schedule
        }