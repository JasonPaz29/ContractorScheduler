from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from ..services.login_services import (
    logout as logout_service,
    login as login_service,
    register as register_service,
)


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _dashboard_url() -> str:
    endpoint = {
        "customer": "customer.dashboard",
        "contractor": "contractor.dashboard",
    }.get(current_user.account_type, "home.home")
    return url_for(endpoint)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_service()
    flash("You have been signed out.", "success")
    return redirect(url_for("home.home"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(_dashboard_url())

    form_values = {}
    if request.method == "POST":
        display_name = request.form.get("display_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        form_values = {"display_name": display_name, "username": username, "email": email}
        try:
            if not display_name or not username or not email or not password.strip():
                raise ValueError("Please fill in your name, username, email, and password.")
            if len(display_name) > 155 or len(username) > 200:
                raise ValueError("Please shorten your name or username and try again.")
            # Public registration creates customers; contractor setup stays separate.
            register_service(
                display_name=display_name,
                username=username,
                email=email,
                password=password,
                choice="1",
            )
        except SQLAlchemyError:
            flash("We couldn't create your account right now. Please try again.", "error")
        except Exception as error:
            flash(str(error), "error")
        else:
            flash("Your account is ready. Sign in to view your schedule.", "success")
            return redirect(url_for("auth.login"))
        return render_template("auth/register.html", form_values=form_values), 400

    return render_template("auth/register.html", form_values=form_values)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_dashboard_url())

    form_values = {}
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")
        form_values = {"identifier": identifier}
        try:
            if not identifier or not password.strip():
                raise ValueError("Please enter your username or email and password.")
            login_service(identifier=identifier, password=password)
        except SQLAlchemyError:
            flash("Sign in is unavailable right now. Please try again.", "error")
        except Exception:
            flash("The username/email or password is incorrect. Please try again.", "error")
        else:
            return redirect(_dashboard_url())
        return render_template("auth/login.html", form_values=form_values), 400

    return render_template("auth/login.html", form_values=form_values)
