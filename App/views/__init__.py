from .user import user_views
from .index import index_views
from .auth import auth_views
from .admin import setup_admin
from .schedule import schedule_views
from .tracking import tracking_views
from .requests import requests_views
from .profile import profile_views
from .lab import lab_views

# All blueprints to be registered
views = [
    user_views,        # API endpoints for user management
    index_views,       # Root route and initialization
    auth_views,        # Authentication routes
    schedule_views,    # Schedule management
    tracking_views,    # Time tracking
    requests_views,    # Request management
    profile_views,     # User profiles
]

# Note: lab_bp is registered separately in main.py