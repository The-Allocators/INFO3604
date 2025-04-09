from App.database import db
from .student import Student

class LabAssistant(db.Model):
    __tablename__ = 'lab_assistant'
    
    username = db.Column(db.String(20), db.ForeignKey('student.username'), primary_key=True)
    rate = db.Column(db.Float, nullable=False)
    active = db.Column(db.Boolean, nullable=False)
    
    def __init__(self, username):
        self.username = username
        self.rate = 20.00
        self.active = True
    
    def get_json(self):
        return {
            'Student ID': self.username,
            'Rate': f'${self.rate}',
            'Account State': 'Active' if self.active == True else 'Inactive',
        }
    
    def activate(self):
        self.active = True
    
    def deactivate(self):
        self.active = False
