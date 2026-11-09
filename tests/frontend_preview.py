"""Run a local preview with synthetic accounts and a disposable in-memory DB.

From the project root: .venv/bin/python -m tests.frontend_preview
Accounts: alex (customer), sam (contractor), robin (customer with no appointments).
Password for each: preview-password-only
"""

import argparse

from tests.test_frontend import make_frontend_test_app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=5094)
    parser.add_argument("--scenario", choices=("normal", "unavailable", "long-name", "no-schedule"), default="normal")
    args = parser.parse_args()
    app = make_frontend_test_app()
    if args.scenario == "unavailable":
        from app.routes import customer_routes, contractor_routes

        def unavailable_schedule():
            raise ValueError("Synthetic unavailable-schedule fixture")

        customer_routes.get_booking_schedule = unavailable_schedule
        contractor_routes.get_my_schedule = unavailable_schedule
    elif args.scenario == "no-schedule":
        from app.extensions import db
        from app.models.Schedule import Schedule

        with app.app_context():
            db.session.delete(Schedule.query.one())
            db.session.commit()
    elif args.scenario == "long-name":
        from app.extensions import db
        from app.models.User import User

        with app.app_context():
            user = User.query.filter_by(username="alex").one()
            user.display_name = "Alexandria Montgomery-Williams and Christopher Josephine Morgan-Santiago"
            db.session.commit()
    print("Synthetic fixture day:", app.config["PREVIEW_DAY"])
    app.run(host="127.0.0.1", port=args.port, debug=False, use_reloader=False)
