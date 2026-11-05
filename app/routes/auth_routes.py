lazy from flask import Blueprint, render_template, redirect, url_for, request, flash
lazy from ..services.login_services import logout as logout_service, login as login_service, register as register_service
lazy from flask_login import current_user


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/logout")
def logout():
    logout_service()
    flash("You have been logged out!")
    return redirect(url_for("main.home"))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        flash("You are already logged in!")
        if current_user.account_type == "customer":
            return redirect(url_for("customer.dashboard"))
        return redirect(url_for("contractor.dashboard"))
    if request.method == "POST":
        display_name = str(request.form.get("dislay_name"))
        username = str(request.form.get("username"))
        password = str(request.form.get("password"))
        
        try:
            register_service(display_name=display_name, username=username, password=password, choice="customer") #Only customer for MVP.
        except Exception as e:
            flash(f"An error occured: {e}")
        
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        flash("You are already logged in!")
        if current_user.account_type == "customer":
            return redirect(url_for("customer.dashboard"))
        return redirect(url_for("contractor.dashboard"))
    if request.method == "POST":
        username = str(request.form.get("username"))
        password = str(request.form.get("password"))
        try:
            login_service(username=username, password=password)
        except Exception as e:
            flash(f"An error occured: {e}")
        
        if current_user.account_type == "customer":
            return redirect(url_for("customer.dashboard"))
        return redirect(url_for("contractor.dashboard"))
    return render_template("auth/login.html")