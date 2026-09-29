from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_from_directory
)

import os
import json
import sqlite3
from datetime import datetime

from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash

from database import initialize_database, create_user


# ==================================================
# FLASK APPLICATION
# ==================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "aapatma_saath_secret_key_2026"
)


# ==================================================
# SETTINGS
# ==================================================

UPLOAD_FOLDER = "uploads"
DATA_FOLDER = "data"

REPORT_FILE = os.path.join(
    DATA_FOLDER,
    "reports.json"
)

USER_DATABASE = os.path.join(
    DATA_FOLDER,
    "users.db"
)


# ==================================================
# CREATE REQUIRED FOLDERS
# ==================================================

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

os.makedirs(
    DATA_FOLDER,
    exist_ok=True
)


# ==================================================
# INITIALIZE USER DATABASE
# ==================================================

initialize_database()


# ==================================================
# REPORT FUNCTIONS
# ==================================================

def load_reports():

    if not os.path.exists(REPORT_FILE):
        return []

    try:

        with open(
            REPORT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

            if isinstance(data, list):
                return data

            return []

    except Exception as e:

        print(
            "Could not read reports:",
            e
        )

        return []


def save_reports(reports):

    try:

        with open(
            REPORT_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                reports,
                file,
                indent=4,
                ensure_ascii=False
            )

        return True

    except Exception as e:

        print(
            "Could not save reports:",
            e
        )

        return False


def create_report_id():

    reports = load_reports()

    number = len(reports) + 1

    return f"AS-{number:06d}"


# ==================================================
# HOME PAGE
# ==================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ==================================================
# REGISTER
# ==================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()

        # ------------------------------------------
        # VALIDATION
        # ------------------------------------------

        if not full_name:

            return render_template(
                "register.html",
                error="Full name is required."
            )

        if not email:

            return render_template(
                "register.html",
                error="Email address is required."
            )

        if not username:

            return render_template(
                "register.html",
                error="Username is required."
            )

        if not password:

            return render_template(
                "register.html",
                error="Password is required."
            )

        if len(password) < 6:

            return render_template(
                "register.html",
                error="Password must be at least 6 characters."
            )

        # ------------------------------------------
        # CREATE USER
        # ------------------------------------------

        created = create_user(
            full_name,
            username,
            email,
            password
        )

        if not created:

            return render_template(
                "register.html",
                error="Username or email already exists."
            )

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# ==================================================
# LOGIN
# ==================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()

        # ------------------------------------------
        # ADMIN LOGIN
        # ------------------------------------------

        admin_username = os.environ.get(
            "ADMIN_USERNAME",
            "admin"
        )

        admin_password = os.environ.get(
            "ADMIN_PASSWORD",
            "admin123"
        )

        if (
            username == admin_username
            and password == admin_password
        ):

            session.clear()

            session["admin_logged_in"] = True

            return redirect(
                url_for("admin")
            )

        # ------------------------------------------
        # NORMAL USER LOGIN
        # ------------------------------------------

        connection = sqlite3.connect(
            USER_DATABASE
        )

        connection.row_factory = sqlite3.Row

        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        connection.close()

        if user:

            if check_password_hash(
                user["password"],
                password
            ):

                session.clear()

                session["user_logged_in"] = True

                session["user_id"] = user["id"]

                session["username"] = user["username"]

                session["full_name"] = user["full_name"]

                return redirect(
                    url_for("user_dashboard")
                )

        # ------------------------------------------
        # INVALID LOGIN
        # ------------------------------------------

        return render_template(
            "login.html",
            error="Invalid username or password."
        )

    return render_template(
        "login.html"
    )


# ==================================================
# USER DASHBOARD
# ==================================================

@app.route("/dashboard")
def user_dashboard():

    if not session.get(
        "user_logged_in"
    ):

        return redirect(
            url_for("login")
        )

    user_id = session.get(
        "user_id"
    )

    reports = load_reports()

    user_reports = []

    for report in reports:

        if report.get(
            "user_id"
        ) == user_id:

            user_reports.append(
                report
            )

    user = {

        "id": user_id,

        "username": session.get(
            "username"
        ),

        "full_name": session.get(
            "full_name"
        )
    }

    return render_template(
        "user_dashboard.html",
        user=user,
        reports=user_reports
    )


# ==================================================
# LOGOUT
# ==================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# ==================================================
# EMERGENCY REPORT PAGE
# ==================================================

@app.route("/report")
def report():

    if not session.get(
        "user_logged_in"
    ):

        return redirect(
            url_for("login")
        )

    emergency_type = request.args.get(
        "type",
        ""
    )

    return render_template(
        "report.html",
        emergency_type=emergency_type
    )


# ==================================================
# SUBMIT EMERGENCY REPORT
# ==================================================

@app.route(
    "/submit-report",
    methods=["POST"]
)
def submit_report():

    if not session.get(
        "user_logged_in"
    ):

        return redirect(
            url_for("login")
        )

    try:

        # ------------------------------------------
        # FORM DATA
        # ------------------------------------------

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        emergency_type = request.form.get(
            "emergency_type",
            ""
        ).strip()

        location = request.form.get(
            "location",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        # ------------------------------------------
        # VALIDATION
        # ------------------------------------------

        if not full_name:

            return """
            <h2>Full Name is required.</h2>
            <a href="/report">Go Back</a>
            """, 400

        if not phone:

            return """
            <h2>Phone Number is required.</h2>
            <a href="/report">Go Back</a>
            """, 400

        if not emergency_type:

            return """
            <h2>Emergency Type is required.</h2>
            <a href="/report">Go Back</a>
            """, 400

        if not location:

            return """
            <h2>Emergency Location is required.</h2>
            <a href="/report">Go Back</a>
            """, 400

        # ------------------------------------------
        # REPORT ID
        # ------------------------------------------

        report_id = create_report_id()

        # ------------------------------------------
        # PHOTO UPLOAD
        # ------------------------------------------

        photo_filename = ""

        photo = request.files.get(
            "photo"
        )

        if (
            photo
            and photo.filename
        ):

            original_filename = secure_filename(
                photo.filename
            )

            if original_filename:

                photo_filename = (
                    report_id
                    + "_"
                    + original_filename
                )

                photo_path = os.path.join(
                    UPLOAD_FOLDER,
                    photo_filename
                )

                photo.save(
                    photo_path
                )

        # ------------------------------------------
        # CREATE REPORT
        # ------------------------------------------

        report_data = {

            "report_id":
                report_id,

            "user_id":
                session.get(
                    "user_id"
                ),

            "full_name":
                full_name,

            "phone":
                phone,

            "emergency_type":
                emergency_type,

            "location":
                location,

            "description":
                description,

            "photo":
                photo_filename,

            "status":
                "Pending",

            "date":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
        }

        # ------------------------------------------
        # SAVE REPORT
        # ------------------------------------------

        reports = load_reports()

        reports.append(
            report_data
        )

        saved = save_reports(
            reports
        )

        if not saved:

            return """
            <h2>
                Unable to save the emergency report.
            </h2>

            <p>
                Please check the data folder permissions.
            </p>

            <a href="/report">
                Go Back
            </a>
            """, 500

        # ------------------------------------------
        # SUCCESS PAGE
        # ------------------------------------------

        return render_template(
            "success.html",
            report=report_data
        )

    except Exception as e:

        print(
            "REPORT ERROR:",
            e
        )

        return f"""
        <h2>
            Unable to submit emergency report.
        </h2>

        <p>Error:</p>

        <pre>{e}</pre>

        <br>

        <a href="/report">
            Go Back
        </a>
        """, 500


# ==================================================
# ADMIN DASHBOARD
# ==================================================

@app.route("/admin")
def admin():

    if not session.get(
        "admin_logged_in"
    ):

        return redirect(
            url_for("login")
        )

    reports = load_reports()

    return render_template(
        "admin.html",
        reports=reports
    )


# ==================================================
# UPDATE REPORT STATUS
# ==================================================

@app.route(
    "/admin/update-status/<report_id>",
    methods=["POST"]
)
def update_status(report_id):

    if not session.get(
        "admin_logged_in"
    ):

        return redirect(
            url_for("login")
        )

    new_status = request.form.get(
        "status",
        "Pending"
    ).strip()

    allowed_statuses = [

        "Pending",

        "In Progress",

        "Resolved"
    ]

    if new_status not in allowed_statuses:

        new_status = "Pending"

    reports = load_reports()

    for report in reports:

        if report.get(
            "report_id"
        ) == report_id:

            report["status"] = new_status

            break

    save_reports(
        reports
    )

    return redirect(
        url_for("admin")
    )


# ==================================================
# VIEW UPLOADED PHOTOS
# ==================================================

@app.route(
    "/uploads/<filename>"
)
def uploaded_file(filename):

    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )


# ==================================================
# GOOGLE SEARCH CONSOLE VERIFICATION
# ==================================================

@app.route(
    "/google192127543091e14d.html"
)
def google_verification():

    return send_from_directory(
        ".",
        "google192127543091e14d.html"
    )


# ==================================================
# DELETE ALL REPORTS
# ==================================================

@app.route(
    "/admin/delete-all",
    methods=["POST"]
)
def delete_all_reports():

    if not session.get(
        "admin_logged_in"
    ):

        return redirect(
            url_for("login")
        )

    save_reports(
        []
    )

    # ------------------------------------------
    # DELETE PHOTOS
    # ------------------------------------------

    for filename in os.listdir(
        UPLOAD_FOLDER
    ):

        file_path = os.path.join(
            UPLOAD_FOLDER,
            filename
        )

        try:

            if os.path.isfile(
                file_path
            ):

                os.remove(
                    file_path
                )

        except Exception as e:

            print(
                "Could not delete:",
                e
            )

    return redirect(
        url_for("admin")
    )


# ==================================================
# SERVER
# ==================================================

if __name__ == "__main__":

    print()

    print(
        "========================================"
    )

    print(
        "       AAPATMA SAATH SERVER"
    )

    print(
        "========================================"
    )

    print()

    print("Home:")

    print(
        "http://127.0.0.1:5000/"
    )

    print()

    print("Register:")

    print(
        "http://127.0.0.1:5000/register"
    )

    print()

    print("Login:")

    print(
        "http://127.0.0.1:5000/login"
    )

    print()

    print("User Dashboard:")

    print(
        "http://127.0.0.1:5000/dashboard"
    )

    print()

    print("Emergency Report:")

    print(
        "http://127.0.0.1:5000/report"
    )

    print()

    print("Admin Dashboard:")

    print(
        "http://127.0.0.1:5000/admin"
    )

    print()

    print("Google Verification:")

    print(
        "http://127.0.0.1:5000/"
        "google192127543091e14d.html"
    )

    print()

    print(
        "Default Admin Username:"
    )

    print(
        os.environ.get(
            "ADMIN_USERNAME",
            "admin"
        )
    )

    print()

    print(
        "Server is starting..."
    )

    print(
        "========================================"
    )

    print()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )