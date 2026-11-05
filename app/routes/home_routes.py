lazy from flask import Blueprint, render_template, redirect, url_for, request, flash
lazy from ..services.login_services import logout as logout_service, login as login_service, register as register_service
lazy from flask_login import current_user

home_bp = Blueprint("home", __name__)

@home_bp.route("/")
def home():
    return render_template('home/index.html')