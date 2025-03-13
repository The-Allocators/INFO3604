from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user
from werkzeug.utils import secure_filename
from App.middleware import volunteer_required
from App.models import Student, HelpDeskAssistant, CourseCapability, Availability, User, Course, TimeEntry
from App.controllers.tracking import get_student_stats
from App.database import db
from App.controllers.notification import notify_availability_updated
import datetime
import os
import json

volunteer_views = Blueprint('volunteer_views', __name__, template_folder='../templates')

@volunteer_views.route('/volunteer/dashboard')
@jwt_required()
@volunteer_required
def dashboard():
    # Get current date for next shift calculation
    now = datetime.datetime.now()
    current_date = now.strftime("%d %B, %Y")
    
    # Mock data - in a real implementation, this would come from a database
    my_shifts = [
        {"date": "30 Sept", "time": "3:00 pm to 4:00 pm"},
        {"date": "01 Oct", "time": "10:00 am to 12:00 pm"},
        {"date": "02 Oct", "time": "1:00 pm to 2:00 pm"},
        {"date": "03 Oct", "time": "11:00 am to 12:00 pm"},
        {"date": "04 Oct", "time": "9:00 am to 11:00 am"}
    ]
    
    # Get next shift (first one in our list for this example)
    next_shift = {
        "date": "30 September, 2024",
        "time": "03:00 pm to 04:00 pm",
        "starts_now": True  # This would be calculated based on current time
    }
    
    # In a real application, this data would be pulled from your database
    # or calculated by your scheduling algorithm
    days_of_week = ['MON', 'TUE', 'WED', 'THUR', 'FRI']
    time_slots = ['9:00 am', '10:00 am', '11:00 am', '12:00 pm', '1:00 pm', '2:00 pm', '3:00 pm', '4:00 pm']
    
    # Sample staff assignments
    staff_schedule = {
        '9:00 am': {
            'MON': ['Liam Johnson', 'Joshua Anderson', 'Daniel Martinez'],
            'TUE': ['Liam Johnson', 'Joshua Anderson'],
            'WED': ['Liam Johnson', 'Joshua Anderson'],
            'THUR': ['Liam Johnson', 'Joshua Anderson', 'Daniel Martinez'],
            'FRI': ['Liam Johnson', 'Joshua Anderson', 'Daniel Martinez']
        },
        # ... other time slots
    }
    
    return render_template('volunteer/dashboard/dashboard.html', 
                          my_shifts=my_shifts,
                          next_shift=next_shift, 
                          days_of_week=days_of_week,
                          time_slots=time_slots,
                          staff_schedule=staff_schedule,
                          current_user=current_user)

@volunteer_views.route('/volunteer/profile')
@jwt_required()
@volunteer_required
def profile():
    # Get current user data from database
    username = current_user.username
    
    # Get the user details
    student = Student.query.get(username)
    if not student:
        flash("Student profile not found", "error")
        return redirect(url_for('volunteer_views.dashboard'))
    
    # Get help desk assistant details
    assistant = HelpDeskAssistant.query.get(username)
    if not assistant:
        flash("Assistant profile not found", "error")
        return redirect(url_for('volunteer_views.dashboard'))
    
    # Get course capabilities
    course_capabilities = CourseCapability.query.filter_by(assistant_username=username).all()
    
    # Get availabilities
    availabilities = Availability.query.filter_by(username=username).all()
    
    # Format availabilities by day
    availability_by_day = {
        'MON': [], 'TUE': [], 'WED': [], 'THUR': [], 'FRI': []
    }
    
    days_mapping = {
        0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THUR', 4: 'FRI'
    }
    
    for avail in availabilities:
        day_name = days_mapping.get(avail.day_of_week)
        if day_name:
            time_slot = f"{avail.start_time.strftime('%I:%M %p').lstrip('0').lower()} - {avail.end_time.strftime('%I:%M %p').lstrip('0').lower()}"
            # Convert to simpler format like "9am - 10am"
            time_slot = time_slot.replace(':00', '').replace(' ', '')
            availability_by_day[day_name].append(time_slot)
    
    # Get stats
    stats = get_student_stats(username) or {
        'daily': {'hours': 0, 'date': datetime.datetime.now().strftime('%Y-%m-%d')},
        'weekly': {'hours': 0, 'start_date': (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d'), 'end_date': datetime.datetime.now().strftime('%Y-%m-%d')},
        'monthly': {'hours': 0, 'month': datetime.datetime.now().strftime('%B %Y')},
        'semester': {'hours': 0},
        'absences': 0
    }
    
    # Build user data dictionary with metadata from the profile table if it exists
    # In a real app, you might have a UserProfile table to store this data
    profile_data = getattr(student, 'profile_data', None)
    if profile_data and isinstance(profile_data, str):
        try:
            profile_data = json.loads(profile_data)
        except:
            profile_data = {}
    else:
        profile_data = {}
    
    # Determine image URL
    image_url = None
    if profile_data and 'image_filename' in profile_data:
        image_url = url_for('static', filename=f'uploads/{profile_data["image_filename"]}')
    
    # Build user data dictionary
    user_data = {
        "name": student.name if student.name else username,
        "id": username,
        "phone": profile_data.get('phone', '398-3921'),
        "email": profile_data.get('email', f"{username}@my.uwi.edu"),
        "image_url": image_url,
        "degree": student.degree,
        "address": {
            "street": profile_data.get('street', '45 Coconut Drive'),
            "city": profile_data.get('city', 'San Fernando'),
            "country": profile_data.get('country', 'Trinidad and Tobago')
        },
        "enrolled_courses": [cap.course_code for cap in course_capabilities],
        "availability": availability_by_day,
        "stats": {
            "weekly": {
                "date_range": f"Week {datetime.datetime.now().isocalendar()[1]}, {datetime.datetime.strptime(stats['weekly']['start_date'], '%Y-%m-%d').strftime('%b %d')} - {datetime.datetime.strptime(stats['weekly']['end_date'], '%Y-%m-%d').strftime('%b %d')}",
                "hours": f"{stats['weekly']['hours']:.1f}"
            },
            "monthly": {
                "date_range": stats['monthly']['month'],
                "hours": f"{stats['monthly']['hours']:.1f}"
            },
            "semester": {
                "date_range": "Current Semester",
                "hours": f"{stats['semester']['hours']:.1f}"
            },
            "absences": str(stats['absences'])
        }
    }
    
    return render_template('volunteer/profile/index.html', user=user_data)

@volunteer_views.route('/volunteer/update_profile', methods=['POST'])
@jwt_required()
@volunteer_required
def update_profile():
    try:
        username = current_user.username
        
        # Get the student
        student = Student.query.get(username)
        if not student:
            return jsonify({'success': False, 'message': 'Student profile not found'})
        
        # Update name and degree
        student.name = request.form.get('name')
        student.degree = request.form.get('degree')
        
        # Load existing profile data if available
        profile_data = {}
        if student.profile_data:
            try:
                profile_data = json.loads(student.profile_data)
            except:
                profile_data = {}
        
        # Update profile data
        profile_data['phone'] = request.form.get('phone')
        profile_data['email'] = request.form.get('email')
        profile_data['street'] = request.form.get('street')
        profile_data['city'] = request.form.get('city')
        profile_data['country'] = request.form.get('country')
        
        # Track if we need to update the image URL
        image_url = None
        
        # Handle profile image upload
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and file.filename:
                # Secure the filename
                filename = secure_filename(file.filename)
                # Add a timestamp to prevent filename collisions
                timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"{username}_{timestamp}_{filename}"
                
                # Make sure the upload directory exists
                upload_dir = os.path.join('App', 'static', 'uploads')
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                
                # Save the file
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                
                # Add the filename to profile data
                profile_data['image_filename'] = f"uploads/{filename}"
                
                # Prepare the URL for the response
                image_url = url_for('static', filename=f"uploads/{filename}")
        
        # Save profile data as JSON in the student model
        student.profile_data = json.dumps(profile_data)
        db.session.add(student)
        db.session.commit()
        
        response_data = {'success': True, 'message': 'Profile updated successfully'}
        
        # Include the image URL if it was updated
        if image_url:
            response_data['image_url'] = image_url
        
        return jsonify(response_data)
    
    except Exception as e:
        db.session.rollback()
        print(f"Error updating profile: {e}")
        return jsonify({'success': False, 'message': str(e)})

@volunteer_views.route('/volunteer/update_courses', methods=['POST'])
@jwt_required()
@volunteer_required
def update_courses():
    try:
        username = current_user.username
        
        # Get the help desk assistant
        assistant = HelpDeskAssistant.query.get(username)
        if not assistant:
            return jsonify({'success': False, 'message': 'Assistant profile not found'})
        
        # Get the list of selected courses
        data = request.json
        selected_courses = data.get('courses', [])
        
        # First, remove all existing course capabilities
        CourseCapability.query.filter_by(assistant_username=username).delete()
        db.session.commit()
        
        # Add new course capabilities
        for course_code in selected_courses:
            # Verify the course exists
            course = Course.query.get(course_code)
            if not course:
                # Create the course if it doesn't exist
                course = Course(course_code, f"Course {course_code}")
                db.session.add(course)
            
            # Add the capability
            capability = CourseCapability(username, course_code)
            db.session.add(capability)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Courses updated successfully'})
    
    except Exception as e:
        db.session.rollback()
        print(f"Error updating courses: {e}")
        return jsonify({'success': False, 'message': str(e)})

@volunteer_views.route('/volunteer/update_availability', methods=['POST'])
@jwt_required()
@volunteer_required
def update_availability():
    try:
        data = request.json
        username = current_user.username
        
        print(f"Received availability data: {data}")
        
        # First, clear existing availabilities
        Availability.query.filter_by(username=username).delete()
        db.session.commit()
        
        # Add new availabilities
        if 'availabilities' in data and data['availabilities']:
            for day_info in data['availabilities']:
                try:
                    day = day_info.get('day', 0)  # 0 for Monday, 1 for Tuesday, etc.
                    start_time = datetime.time.fromisoformat(day_info.get('start_time', '00:00:00'))
                    end_time = datetime.time.fromisoformat(day_info.get('end_time', '00:00:00'))
                    
                    availability = Availability(username, day, start_time, end_time)
                    db.session.add(availability)
                    print(f"Added availability: Day {day}, {start_time}-{end_time}")
                except Exception as e:
                    print(f"Error adding individual availability: {e}")
                    # Continue with other availabilities even if this one failed
        
        db.session.commit()
        
        # Create notification
        notify_availability_updated(username)
        
        # Get updated availabilities to return
        updated_availabilities = Availability.query.filter_by(username=username).all()
        
        print(f"Successfully updated {len(updated_availabilities)} availability slots")
        
        return jsonify({
            "success": True, 
            "message": "Availability updated successfully",
            "count": len(updated_availabilities)
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error updating availability: {e}")
        return jsonify({
            "success": False,
            "message": f"Error updating availability: {str(e)}"
        }), 500

@volunteer_views.route('/api/courses')
@jwt_required()
def get_courses():
    """Get all available courses"""
    try:
        courses = Course.query.all()
        return jsonify({
            'success': True,
            'courses': [{'code': course.code, 'name': course.name} for course in courses]
        })
    except Exception as e:
        print(f"Error getting courses: {e}")
        return jsonify({'success': False, 'message': str(e)})

@volunteer_views.route('/volunteer/time_tracking')
@jwt_required()
@volunteer_required
def time_tracking():
    username = current_user.username
    
    # Get student stats
    stats = get_student_stats(username) or {
        'daily': {'hours': 0, 'date': datetime.datetime.now().strftime('%Y-%m-%d')},
        'weekly': {'hours': 0, 'start_date': (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d'), 'end_date': datetime.datetime.now().strftime('%Y-%m-%d')},
        'monthly': {'hours': 0, 'month': datetime.datetime.now().strftime('%B %Y')},
        'semester': {'hours': 0},
        'absences': 0
    }
    
    # Get current date
    now = datetime.datetime.now()
    today = now.strftime("%d %B, %Y")
    
    # Find today's shift if any
    today_start = datetime.datetime.combine(now.date(), datetime.time.min)
    today_end = datetime.datetime.combine(now.date(), datetime.time.max)
    
    # Get all shifts for today
    from App.models import Shift, Allocation
    today_shifts = db.session.query(Shift).filter(
        Shift.date >= today_start,
        Shift.date <= today_end
    ).all()
    
    # Check if the user is assigned to any of today's shifts
    today_shift = None
    for shift in today_shifts:
        allocation = Allocation.query.filter_by(
            username=username,
            shift_id=shift.id
        ).first()
        
        if allocation:
            # Check if there's an active time entry
            time_entry = TimeEntry.query.filter_by(
                username=username,
                shift_id=shift.id
            ).order_by(TimeEntry.id.desc()).first()
            
            status = 'future'
            if time_entry:
                if time_entry.status == 'active':
                    status = 'active'
                elif time_entry.status == 'completed':
                    status = 'completed'
            elif now >= shift.start_time and now <= shift.end_time:
                status = 'now'
            
            # Calculate time until/left
            time_until = ''
            time_left = ''
            if status == 'future':
                time_diff = shift.start_time - now
                hours = time_diff.seconds // 3600
                minutes = (time_diff.seconds % 3600) // 60
                time_until = f"{hours} hours {minutes} minutes"
            elif status == 'active':
                time_diff = shift.end_time - now
                hours = time_diff.seconds // 3600
                minutes = (time_diff.seconds % 3600) // 60
                time_left = f"{hours} hours {minutes} minutes"
            
            today_shift = {
                "date": shift.date.strftime("%d %B, %Y"),
                "start_time": shift.start_time.strftime("%I:%M %p"),
                "end_time": shift.end_time.strftime("%I:%M %p"),
                "status": status,
                "time_until": time_until,
                "time_left": time_left
            }
            break
    
    # If no shift found for today, create a placeholder
    if not today_shift:
        today_shift = {
            "date": today,
            "start_time": "No shift scheduled",
            "end_time": "N/A",
            "status": "none"
        }
    
    # Get shift history
    time_entries = TimeEntry.query.filter_by(
        username=username,
        status='completed'
    ).order_by(TimeEntry.clock_in.desc()).limit(5).all()
    
    shift_history = []
    for entry in time_entries:
        shift = Shift.query.get(entry.shift_id) if entry.shift_id else None
        
        if entry.clock_out:
            hours_worked = (entry.clock_out - entry.clock_in).total_seconds() / 3600
            hours_str = f"{hours_worked:.1f} hrs"
        else:
            hours_str = "N/A"
            
        shift_history.append({
            "date": entry.clock_in.strftime("%d %b") if entry.clock_in else "Unknown",
            "time_range": f"{entry.clock_in.strftime('%I:%M %p')} to {entry.clock_out.strftime('%I:%M %p')}" if entry.clock_in and entry.clock_out else "N/A",
            "hours": hours_str
        })
    
    # Mock time distribution data for chart
    # In a real app, calculate this from actual time records
    time_distribution = [
        {"label": "Mon", "percentage": 80},
        {"label": "Tue", "percentage": 40},
        {"label": "Wed", "percentage": 0},
        {"label": "Thur", "percentage": 30},
        {"label": "Fri", "percentage": 85}
    ]
    
    # Format stats for display
    daily = {
        "date_range": now.strftime("%d %b, %I:%M %p"),
        "hours": f"{stats['daily']['hours']:.1f}"
    }
    
    week_start = datetime.datetime.strptime(stats['weekly']['start_date'], '%Y-%m-%d')
    week_end = datetime.datetime.strptime(stats['weekly']['end_date'], '%Y-%m-%d')
    
    weekly = {
        "date_range": f"Week {now.isocalendar()[1]}, {week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}",
        "hours": f"{stats['weekly']['hours']:.1f}"
    }
    
    monthly = {
        "date_range": stats['monthly']['month'],
        "hours": f"{stats['monthly']['hours']:.1f}"
    }
    
    semester = {
        "date_range": "Current Semester",
        "hours": f"{stats['semester']['hours']:.1f}"
    }
    
    return render_template('volunteer/time_tracking/index.html',
                          today_shift=today_shift,
                          shift_history=shift_history,
                          time_distribution=time_distribution,
                          daily=daily,
                          weekly=weekly,
                          monthly=monthly,
                          semester=semester)

@volunteer_views.route('/volunteer/time_tracking/clock_in', methods=['POST'])
@jwt_required()
@volunteer_required
def clock_in():
    from App.controllers.tracking import clock_in as clock_in_controller
    
    username = current_user.username
    
    # Get the current active shift for this user
    now = datetime.datetime.now()
    today_start = datetime.datetime.combine(now.date(), datetime.time.min)
    today_end = datetime.datetime.combine(now.date(), datetime.time.max)
    
    from App.models import Shift, Allocation
    today_shifts = db.session.query(Shift).filter(
        Shift.date >= today_start,
        Shift.date <= today_end,
        Shift.start_time <= now,
        Shift.end_time >= now
    ).all()
    
    # Find the first shift the user is assigned to
    shift_id = None
    for shift in today_shifts:
        allocation = Allocation.query.filter_by(
            username=username,
            shift_id=shift.id
        ).first()
        
        if allocation:
            shift_id = shift.id
            break
    
    # Call the clock_in controller
    result = clock_in_controller(username, shift_id)
    return jsonify(result)

@volunteer_views.route('/volunteer/time_tracking/clock_out', methods=['POST'])
@jwt_required()
@volunteer_required
def clock_out():
    from App.controllers.tracking import clock_out as clock_out_controller
    
    username = current_user.username
    
    # Call the clock_out controller
    result = clock_out_controller(username)
    return jsonify(result)

@volunteer_views.route('/volunteer/requests')
@jwt_required()
@volunteer_required
def requests():
    # Use the real controller to get the user's requests
    from App.controllers.request import (
        get_student_requests,
        get_available_shifts_for_student,
        get_available_replacements
    )
    
    username = current_user.username
    
    # Get the student's requests
    requests_list = get_student_requests(username)
    
    # Categorize by status
    pending_requests = [r for r in requests_list if r['status'] == 'PENDING']
    approved_requests = [r for r in requests_list if r['status'] == 'APPROVED']
    rejected_requests = [r for r in requests_list if r['status'] == 'REJECTED']
    
    # Get available shifts for new requests
    available_shifts = get_available_shifts_for_student(username)
    
    # Get available replacements
    available_replacements = get_available_replacements(username)
    
    return render_template('volunteer/requests/index.html',
                          pending_requests=pending_requests,
                          approved_requests=approved_requests,
                          rejected_requests=rejected_requests,
                          available_shifts=available_shifts,
                          available_replacements=available_replacements)

@volunteer_views.route('/volunteer/submit_request', methods=['POST'])
@jwt_required()
@volunteer_required
def submit_request():
    """Submit a new shift change request"""
    from App.controllers.request import create_student_request
    
    data = request.form
    
    # Extract data from form
    shift_id = data.get('shiftToChange')
    reason = data.get('reasonForChange')
    replacement = data.get('proposedReplacement')
    
    # Validate required fields
    if not shift_id or not reason:
        flash("Shift and reason are required fields", "error")
        return redirect(url_for('requests_views.volunteer_requests'))
    
    # Create the request
    success, message = create_student_request(
        current_user.username,
        shift_id,
        reason,
        replacement
    )
    
    if success:
        flash(message, "success")
    else:
        flash(message, "error")
        
    return redirect(url_for('volunteer_views.requests'))