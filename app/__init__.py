from flask import Flask, current_app
from .config import Config
from .extensions import db, migrate, login_manager

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    migrate.init_app(app, db)
    
    login_manager.init_app(app)
    login_manager.login_view = "auth.login" #type: ignore

    # Register account types and the session loader before serving requests.
    from .models import User, Customer, Contractor, Schedule, Appointment
    from .services import login_services
    
    from .routes import auth_routes, contractor_routes, customer_routes, home_routes
    app.register_blueprint(auth_routes.auth_bp)
    app.register_blueprint(contractor_routes.contractor_bp)
    app.register_blueprint(customer_routes.customer_bp)
    app.register_blueprint(home_routes.home_bp)
    
    return app
