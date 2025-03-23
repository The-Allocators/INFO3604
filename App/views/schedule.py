from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user
from datetime import datetime, timedelta, time
from App.controllers.schedule import (
    # help_desk_scheduler,  # Commented out the old function
    generate_help_desk_schedule,
    publish_schedule,
    get_schedule_for_week,
    help_desk_scheduler  # Using the new function
)
from App.models import db, Shift, Allocation, Schedule
from App.middleware import admin_required

schedule_views = Blueprint('schedule_views', __name__, template_folder='../templates')

@schedule_views.route('/schedule')
@jwt_required()
@admin_required
def schedule():
    return render_template('admin/schedule/view.html')

@schedule_views.route('/api/schedule/details', methods=['GET'])
@jwt_required()
@admin_required
def get_schedule_details():
    """Get detailed schedule data for the admin UI"""
    try:
        # Get the week from the request, or use the current week
        week_str = request.args.get('week')
        if week_str:
            # Parse the week string (e.g., "Week 42")
            try:
                week_number = int(week_str.split(' ')[1])
            except:
                week_number = datetime.utcnow().isocalendar()[1]  # Current ISO week
        else:
            # Use current week
            week_number = datetime.utcnow().isocalendar()[1]  # ISO week number
        
        # Check if we have an existing schedule for this week
        schedule = get_schedule_for_week(week_number)
        
        if schedule:
            # Format the data from the existing schedule
            days = []
            for day_data in schedule["days"]:
                shifts = []
                for shift_data in day_data["shifts"]:
                    # Convert assistant data to staff indices
                    staff_list = [assistant["username"] for assistant in shift_data["assistants"]]
                    
                    shifts.append({
                        "time": shift_data["time"].split(" to ")[0],  # Just use the start time
                        "staff": staff_list
                    })
                
                days.append({
                    "day": day_data["day"],
                    "shifts": shifts
                })
            
            # Create a mapping from staff username to name
            staff_index = {}
            for day_data in schedule["days"]:
                for shift_data in day_data["shifts"]:
                    for assistant in shift_data["assistants"]:
                        staff_index[assistant["username"]] = assistant["name"]
            
            return jsonify({
                "status": "success",
                "schedule": days,
                "staff_index": staff_index,
                "schedule_id": schedule["schedule_id"],
                "is_published": schedule["is_published"]
            })
        
        # No existing schedule, generate a new one
        # Calculate the start date for the given week
        today = datetime.utcnow()
        # Calculate start of the requested week (Monday)
        year = today.year
        # Use the strptime/strftime trick to get the first day of the target week
        first_day = datetime.strptime(f'{year}-{week_number}-1', '%Y-%W-%w')
        
        # Call the updated scheduler with actual data
        result = help_desk_scheduler(first_day, first_day + timedelta(days=4), week_number)
        
        if result['status'] != 'success':
            return jsonify(result), 400
        
        # Format the data for the UI
        assignments = result['assignments']
        staff_index = result['staff_index']
        
        # Define days and shift times for hourly slots
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        shift_times = ["9:00 am", "10:00 am", "11:00 am", "12:00 pm", 
                      "1:00 pm", "2:00 pm", "3:00 pm", "4:00 pm"]
        
        # Create a formatted schedule
        formatted_schedule = []
        for day_idx, day in enumerate(days):
            day_shifts = []
            for time_idx, time in enumerate(shift_times):
                shift_id = day_idx * len(shift_times) + time_idx
                staff_list = assignments.get(shift_id, [])
                day_shifts.append({
                    'time': time,
                    'staff': staff_list
                })
            formatted_schedule.append({
                'day': day,
                'shifts': day_shifts
            })
            
        return jsonify({
            'status': 'success',
            'schedule': formatted_schedule,
            'staff_index': staff_index,
            'schedule_id': result['schedule_id']
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@schedule_views.route('/api/schedule/generate', methods=['POST'])
@jwt_required()
@admin_required
def generate_schedule():
    """Generate a new schedule using the model-based approach"""
    try:
        data = request.json
        week_number = data.get('week_number')
        
        if not week_number:
            # Default to next week
            today = datetime.utcnow()
            week_number = (today + timedelta(days=7)).isocalendar()[1]
        
        # Parse the start date or default to next Monday
        start_date_str = data.get('start_date')
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        else:
            # Default to next Monday
            today = datetime.utcnow()
            days_ahead = (0 - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            start_date = today + timedelta(days=days_ahead)
        
        # Call the new schedule generator
        result = generate_help_desk_schedule(week_number, start_date)
        return jsonify(result)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@schedule_views.route('/api/schedule/<int:schedule_id>/publish', methods=['POST'])
@jwt_required()
@admin_required
def publish_schedule_endpoint(schedule_id):
    """Publish a schedule and notify all assigned staff"""
    result = publish_schedule(schedule_id)
    return jsonify(result)

@schedule_views.route('/api/schedule/week/<int:week_number>', methods=['GET'])
@jwt_required()
def get_week_schedule(week_number):
    """Get the schedule for a specific week"""
    schedule = get_schedule_for_week(week_number)
    if schedule:
        return jsonify({'status': 'success', 'schedule': schedule})
    else:
        return jsonify({'status': 'error', 'message': 'Schedule not found'}), 404
    
    
@schedule_views.route('/api/schedule/<int:schedule_id>/update', methods=['POST'])
@jwt_required()
@admin_required
def update_schedule(schedule_id):
    """Update an existing schedule with new staff assignments"""
    try:
        data = request.json
        schedule_data = data.get('schedule', [])
        
        # Get the schedule
        schedule = Schedule.query.get(schedule_id)
        if not schedule:
            return jsonify({"status": "error", "message": "Schedule not found"})
        
        # Delete existing allocations for this schedule
        Allocation.query.filter_by(schedule_id=schedule_id).delete()
        db.session.commit()
        
        # Process each day and shift
        for day_idx, day_data in enumerate(schedule_data):
            day_name = day_data.get('day')
            shifts = day_data.get('shifts', [])
            
            for time_idx, shift_data in enumerate(shifts):
                time_slot = shift_data.get('time')
                staff_ids = shift_data.get('staff', [])
                
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
                    shift_start = datetime.combine(date.date(), time(hour=hour))
                    shift_end = datetime.combine(date.date(), time(hour=hour+1))
                    shift = Shift(date, shift_start, shift_end, schedule_id)
                    db.session.add(shift)
                    db.session.flush()  # Get the shift ID
                elif not shift or not staff_ids:
                    # Skip if no shift and no staff
                    continue
                
                # Create allocations for each staff member
                for staff_id in staff_ids:
                    allocation = Allocation(staff_id, shift.id, schedule_id)
                    db.session.add(allocation)
        
        # Commit all changes
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Schedule updated successfully",
            "schedule_id": schedule_id
        })
    
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "status": "error",
            "message": f"Error updating schedule: {str(e)}"
        }), 500