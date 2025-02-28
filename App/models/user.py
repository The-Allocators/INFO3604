from werkzeug.security import check_password_hash, generate_password_hash
from App.database import db

class User(db.Model):
    __tablename__ = 'user'
    
    username =  db.Column(db.String(20), nullable=False, primary_key=True)
    password = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(50), nullable=False) # 'admin' or 'assistant'
    
    __mapper_args__ = {
        'polymorphic_identity': 'user',
        'polymorphic_on': type
    }

    def __init__(self, username, password):
        self.username = username
        self.set_password(password)

    def get_json(self):
        return{
            'username': self.username
        }

    def set_password(self, password):
        """Create hashed password."""
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        """Check hashed password."""
        return check_password_hash(self.password, password)

