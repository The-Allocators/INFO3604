from .user import create_user
from .admin import create_admin
from .student import create_student
from .schedule import create_schedule
from .semester import create_semester, get_semester
# from .shift import create_shift
from .notification import (
    create_notification,
    notify_shift_approval,
    notify_clock_in,
    notify_clock_out,
    notify_schedule_published,
    notify_shift_reminder,
    notify_request_submitted,
    notify_missed_shift,
    notify_availability_updated
)
from App.models import Notification
from App.database import db

def initialize():
    db.drop_all()
    db.create_all()
    
    # Create default admin account
    admin = create_admin('a', '123')
    
    # Create default volunteer/assistant account
    student = create_student('8', 'a', 'BSc')

    # Create sample notifications for demo purposes
    create_sample_notifications(admin.username, student.username)
    
    # Create sample semester
    create_sample_semester()
    
    # Create sample schedule
    create_sample_schedule()
    
    print('Database initialized with default accounts:')
    
    print(admin.get_json(), "Password: 123")
    print(student.get_json(), "Password: a")


def create_sample_notifications(admin_username, student_username):
    """Create sample notifications for the demo"""
    
    # Admin notifications
    create_notification(
        admin_username,
        "New volunteer request from Michelle Liu (816031284).", 
        Notification.TYPE_REQUEST
    )
    
    create_notification(
        admin_username,
        "Schedule for Week 5 has been published.", 
        Notification.TYPE_SCHEDULE
    )
    
    create_notification(
        admin_username,
        "Daniel Rasheed missed his shift on Monday.", 
        Notification.TYPE_MISSED
    )
    
    # Volunteer notifications
    notify_shift_approval(student_username, "Monday, Sept 30, 3:00 PM to 4:00 PM")
    
    notify_clock_in(student_username, "Friday, Sept 27, 3:00 PM to 4:00 PM")
    
    notify_clock_out(student_username, "Friday, Sept 27, 3:00 PM to 4:00 PM")
    
    notify_schedule_published(student_username, 5)
    
    notify_shift_reminder(student_username, "Monday, Sept 30, 3:00 PM to 4:00 PM", 15)
    
    notify_request_submitted(student_username, "Tuesday, Oct 1, 11:00 AM to 12:00 PM")
    
    # Mark some notifications as read to demonstrate that functionality
    notifications = Notification.query.filter_by(username=student_username).limit(2).all()
    for notification in notifications:
        notification.is_read = True
        db.session.add(notification)
    
    db.session.commit()


def create_sample_semester():
    semester = create_semester('2025-01-19', '2025-05-09')


def create_sample_schedule():
    semester = get_semester('2024/2025', '2')
    if semester:
        schedule = create_schedule(semester.id, 1, '2025-01-20', '2025-01-26')
