from App.database import db
from .student import Student

class HelpDeskAssistant(db.Model):
    __tablename__ = 'help_desk_assistant'
    
    username = db.Column(db.String(20), db.ForeignKey('student.username'), primary_key=True)
    rate = db.Column(db.Float, nullable=False)
    active = db.Column(db.Boolean, nullable=False)
    hours_worked = db.Column(db.Integer, nullable=False)
    hours_minimum = db.Column(db.Integer, nullable=False)
    
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
            'Degree Level': self.degree,
            'Rate': f'${self.rate}',
            'Account State': 'Active' if self.active == True else 'Inactive',
            'Hours Worked': self.hours_worked,
            'Minimum Hours': self.hours_minimum
        }
    
    def activate(self):
        self.active = True
    
    def deactivate(self):
        self.active = False
    
    def set_minimum_hours(self, hours):
        self.hours_minimum = hours
    
    def update_hours_worked(self, hours):
        self.hours_worked += hours
    
