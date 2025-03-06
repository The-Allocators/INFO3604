from App.models import Shift
from App.database import db

def create_shift(day, start_time, end_time):
    new_shift = Shift(day, start_time, end_time)
    db.session.add(new_shift)
    db.session.commit()
    return new_shift

