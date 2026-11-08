import hmac
import secrets

from flask import Blueprint, flash, redirect, request, session, url_for, current_app
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import DEPARTMENTS, Attendance, Mark, Subject
from .analytics import invalidate_spark_cache

bp = Blueprint("subjects", __name__)
VALID_SEMESTERS = tuple(str(semester) for semester in range(1, 9))


def subject_csrf_token():
    """Return a session-bound token for subject management forms."""
    token = session.get("_subject_csrf_token")
    if token is None:
        token = secrets.token_urlsafe(32)
        session["_subject_csrf_token"] = token
    return token


def _valid_csrf_token():
    """Validate the submitted token against the signed session value."""
    token = request.form.get("csrf_token", "")
    expected = session.get("_subject_csrf_token", "")
    return bool(token and expected and hmac.compare_digest(token, expected))


def _dashboard_redirect():
    """Return to the dashboard after a subject management request."""
    return redirect(url_for("main.dashboard"))


@bp.route("/add", methods=["POST"])
def add():
    """Create a subject after validating its details and form token."""
    if not _valid_csrf_token():
        flash("The form expired or was invalid. Please try again.", "danger")
        return _dashboard_redirect()

    name = request.form.get("name", "").strip()
    code = request.form.get("code", "").strip()
    department = request.form.get("department", "")
    semester = request.form.get("semester", "")
    if not name or not code or department not in DEPARTMENTS:
        flash("Subject name, code, and a valid department are required.", "danger")
        return _dashboard_redirect()
    if semester not in VALID_SEMESTERS:
        flash("Select a valid semester (1 through 8).", "danger")
        return _dashboard_redirect()

    try:
        existing_subjects = Subject.query.all()
        if any(subject.code.casefold() == code.casefold()
               or (subject.name.casefold() == name.casefold()
                   and subject.department == department
                   and subject.semester == int(semester))
               for subject in existing_subjects):
            flash("That subject code or name, department, and semester combination already exists.",
                  "danger")
            return _dashboard_redirect()
        db.session.add(Subject(name=name, code=code, department=department,
                               semester=int(semester)))
        db.session.commit()
        invalidate_spark_cache()
        flash(f"Subject {name} added.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Unable to add subject")
        flash("The subject could not be added because of a database error.", "danger")
    return _dashboard_redirect()


@bp.route("/edit/<int:subject_id>", methods=["POST"])
def edit(subject_id):
    """Update a subject's department and semester after validating its form."""
    if not _valid_csrf_token():
        flash("The form expired or was invalid. Please try again.", "danger")
        return _dashboard_redirect()

    department = request.form.get("department", "")
    semester = request.form.get("semester", "")
    if department not in DEPARTMENTS or semester not in VALID_SEMESTERS:
        flash("Select a valid department and semester.", "danger")
        return _dashboard_redirect()

    subject = db.session.get(Subject, subject_id)
    if subject is None:
        flash("That subject no longer exists.", "warning")
        return _dashboard_redirect()

    duplicate = any(
        other.id != subject.id
        and other.name.casefold() == subject.name.casefold()
        and other.department == department
        and other.semester == int(semester)
        for other in Subject.query.all()
    )
    if duplicate:
        flash("Another subject has that name, department, and semester combination.",
              "danger")
        return _dashboard_redirect()

    subject.department = department
    subject.semester = int(semester)
    db.session.commit()
    invalidate_spark_cache()
    flash(f"Department and semester updated for {subject.name}.", "success")
    return _dashboard_redirect()


@bp.route("/delete/<int:subject_id>", methods=["POST"])
def delete(subject_id):
    """Delete a subject and its attendance and marks in one transaction."""
    if not _valid_csrf_token():
        flash("The form expired or was invalid. Please try again.", "danger")
        return _dashboard_redirect()

    try:
        subject = db.session.get(Subject, subject_id)
        if subject is None:
            flash("That subject no longer exists.", "warning")
            return _dashboard_redirect()

        name = subject.name
        attendance_count = Attendance.query.filter_by(subject_id=subject_id).count()
        marks_count = Mark.query.filter_by(subject_id=subject_id).count()
        Attendance.query.filter_by(subject_id=subject_id).delete(synchronize_session=False)
        Mark.query.filter_by(subject_id=subject_id).delete(synchronize_session=False)
        db.session.delete(subject)
        db.session.commit()
        invalidate_spark_cache()
        flash(f"Deleted {name}; removed {attendance_count} attendance records "
              f"and {marks_count} marks records.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Unable to delete subject %s", subject_id)
        flash("The subject and its records could not be deleted.", "danger")
    return _dashboard_redirect()
