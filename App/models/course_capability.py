from App.database import db

class CourseCapability(db.Model):
    __tablename__ = 'course_capability'
    
    id = db.Column(db.Integer, primary_key=True)
    assistant_username = db.Column(db.String(20), db.ForeignKey('help_desk_assistant.username'), nullable=False)
    course_code = db.Column(db.String(10), nullable=False)
    
    def __init__(self, assistant_username, course_code):
        self.assistant_username = assistant_username
        self.course_code = course_code
    
    def get_json(self):
        return {
            'Assistant ID': self.assistant_username,
            'Course Code': self.course_code
        }