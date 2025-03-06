from App.database import db
from datetime import datetime

class Shift(db.Model):
    __tablename__ = 'shift'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=False)
    
    def __init__(self, date:datetime, start:datetime, end:datetime):
        self.date = date
        self.start = start
        self.end = end
    
    def get_json(self):
        return {
            'Shift ID': self.id,
            'Date': self.date,
            'Start Time': self.start,
            'End Time': self.end,
        }
