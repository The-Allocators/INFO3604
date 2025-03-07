from App.models import Availability
from App.database import db

def create_availability(username, shift):
    new_availability = Availability(username, shift)
    db.session.add(new_availability)
    db.session.commit()
    return new_availability

def get_all_availability():
    return Availability.query.all()
