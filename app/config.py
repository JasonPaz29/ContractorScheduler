import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "placeholder")
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///itscheduler.db')
    SQLALCHEMY_DATABASE_TRACK_MODIFICATIONS = False
    