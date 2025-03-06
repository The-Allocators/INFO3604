from App.models import Student
from App.database import db

def create_student(username, password, degree):
    new_student = Student(username, password, degree)
    db.session.add(new_student)
    db.session.commit()
    return new_student

