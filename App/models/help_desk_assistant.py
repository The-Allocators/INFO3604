from App.database import db
from .student import Student

class HelpDeskAssistant(db.Model):
    __tablename__ = 'help_desk_assistant'
    
    username = db.Column(db.String(20), db.ForeignKey('student.username'), primary_key=True)
    rate = db.Column(db.Float, nullable=False)
    active = db.Column(db.Boolean, nullable=False)
    hours_worked = db.Column(db.Integer, nullable=False)
    hours_minimum = db.Column(db.Integer, nullable=False)
    
    # Course competency
    course_capabilities = db.relationship('CourseCapability', backref='assistant', lazy=True, cascade="all, delete-orphan")
    
    def __init__(self, username):
        self.username = username
        student = Student.query.get(username)
        self.rate = 20.00 if student.degree == 'BSc' else 35.00 if student.degree == 'MSc' else 0.00
        self.active = True
        self.hours_worked = 0
        self.hours_minimum = 4
    
    def get_json(self):
        return {
            'Student ID': self.username,
            'Rate': f'${self.rate}',
            'Account State': 'Active' if self.active == True else 'Inactive',
            'Hours Worked': self.hours_worked,
            'Minimum Hours': self.hours_minimum,
            'Course Capabilities': [cap.course_code for cap in self.course_capabilities]
        }
    
    def activate(self):
        self.active = True
    
    def deactivate(self):
        self.active = False
    
    def set_minimum_hours(self, hours):
        self.hours_minimum = hours
    
    def update_hours_worked(self, hours):
        self.hours_worked += hours
    
    def add_course_capability(self, course_code):
        capability = CourseCapability(self.username, course_code)
        self.course_capabilities.append(capability)
        return capability