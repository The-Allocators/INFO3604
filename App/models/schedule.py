from App.database import db
from datetime import datetime

class Schedule(db.Model):
    __tablename__ = 'schedule'
    
    id = db.Column(db.Integer, primary_key=True)
    semester = db.Column(db.Integer, db.ForeignKey('semester.id'), nullable=False)
    week = db.Column(db.Integer, nullable=False)
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=False)
    
    def __init__(self, semester, week, start:datetime, end:datetime):
        self.semester = semester
        self.week = week
        self.start = start
        self.end = end
    
    def get_json(self):
        return {
            'Schedule ID': self.id,
            'Semester ID': self.semester,
            'Week': self.week,
            'Start Date': self.start.date(),
            'End Date': self.end.date()
        }

