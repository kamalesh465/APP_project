from datetime import date, timedelta

import pandas as pd

from app.extensions import db
from app.models import Attendance, Student, Subject
from app.services import analytics_service


def _student(roll_no, name):
    return Student(
        roll_no=roll_no,
        name=name,
        department="CSE",
        semester=3,
    )


def _add_attendance(student, subject, statuses, start_date=date(2026, 1, 5)):
    for offset, status in enumerate(statuses):
        db.session.add(
            Attendance(
                student_id=student.id,
                subject_id=subject.id,
                date=start_date + timedelta(days=offset),
                status=status,
            )
        )


def test_attendance_submission_saves_and_updates_existing_records(app, client):
    student_one = _student("TEST001", "Student One")
    student_two = _student("TEST002", "Student Two")
    subject = Subject(code="TEST101", name="Test Subject", semester=3)
    db.session.add_all([student_one, student_two, subject])
    db.session.commit()

    attendance_date = "2026-02-03"
    form_data = {
        "subject_id": str(subject.id),
        "date": attendance_date,
        f"present_{student_one.id}": "on",
    }

    response = client.post("/attendance/mark", data=form_data)
    assert response.status_code == 302
    assert {
        record.student_id: record.status
        for record in Attendance.query.filter_by(
            subject_id=subject.id, date=date.fromisoformat(attendance_date)
        )
    } == {
        student_one.id: "Present",
        student_two.id: "Absent",
    }

    response = client.post(
        "/attendance/mark",
        data={
            "subject_id": str(subject.id),
            "date": attendance_date,
            f"present_{student_two.id}": "on",
        },
    )

    assert response.status_code == 302
    records = Attendance.query.filter_by(
        subject_id=subject.id, date=date.fromisoformat(attendance_date)
    ).all()
    assert len(records) == 2
    assert {record.student_id: record.status for record in records} == {
        student_one.id: "Absent",
        student_two.id: "Present",
    }


def test_student_attendance_percentage_is_exactly_75_percent(app):
    student = _student("PCT001", "Percentage Student")
    subject = Subject(code="PCT101", name="Percentage Subject", semester=3)
    db.session.add_all([student, subject])
    db.session.commit()
    _add_attendance(student, subject, ["Present", "Present", "Present", "Absent"])
    db.session.commit()

    attendance_df = analytics_service.load_attendance_df()
    percentages = analytics_service.student_percentages(
        attendance_df, app.config["ATTENDANCE_THRESHOLD"]
    )

    student_percentage = percentages.loc[
        percentages["student_id"] == student.id, "percentage"
    ].item()
    assert student_percentage == 75.0


def test_defaulters_include_only_students_below_configured_threshold(app, client):
    threshold = app.config["ATTENDANCE_THRESHOLD"]
    below = _student("RISK001", "Below Threshold")
    at_threshold = _student("RISK002", "At Threshold")
    above = _student("RISK003", "Above Threshold")
    subject = Subject(code="RISK101", name="Risk Subject", semester=3)
    db.session.add_all([below, at_threshold, above, subject])
    db.session.commit()

    _add_attendance(below, subject, ["Present", "Absent"])
    _add_attendance(
        at_threshold,
        subject,
        ["Present"] * 3 + ["Absent"],
        start_date=date(2026, 2, 1),
    )
    _add_attendance(
        above,
        subject,
        ["Present"] * 4,
        start_date=date(2026, 3, 1),
    )
    db.session.commit()

    attendance_df = analytics_service.load_attendance_df()
    percentages = analytics_service.student_percentages(attendance_df, threshold)
    exact_percentage = percentages.loc[
        percentages["student_id"] == at_threshold.id, "percentage"
    ].item()
    assert exact_percentage == threshold

    response = client.get("/analytics/defaulters")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Below Threshold" in page
    assert "At Threshold" not in page
    assert "Above Threshold" not in page


def test_weekly_trend_returns_hand_calculated_attendance_percentages():
    attendance_df = pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2026-01-05", "2026-01-06", "2026-01-12", "2026-01-13"]
            ),
            "present": [1, 0, 1, 1],
        }
    )

    labels, values = analytics_service.weekly_trend(attendance_df)

    assert labels == ["11 Jan", "18 Jan"]
    assert values == [50.0, 100.0]


def test_core_pages_return_successful_responses(app, client):
    student = _student("PAGE001", "Page Test Student")
    subject = Subject(code="PAGE101", name="Page Test Subject", semester=3)
    db.session.add_all([student, subject])
    db.session.commit()
    _add_attendance(student, subject, ["Present", "Absent"])
    db.session.commit()

    for path in (
        "/",
        "/attendance/mark",
        "/attendance/report",
        "/analytics/defaulters",
        "/analytics/trends",
    ):
        response = client.get(path)
        assert response.status_code == 200, f"{path} returned {response.status_code}"


def test_attendance_page_shows_student_in_subject_semester(app, client):
    matching_student = _student("ROSTER001", "Matching Semester Student")
    subject = Subject(code="ROSTER101", name="Roster Subject", semester=3)
    db.session.add_all([matching_student, subject])
    db.session.commit()

    response = client.get(f"/attendance/mark?subject_id={subject.id}")

    assert response.status_code == 200
    assert "Matching Semester Student" in response.get_data(as_text=True)


def test_attendance_page_hides_student_from_another_semester(app, client):
    student = _student("ROSTER002", "Other Semester Student")
    student.semester = 5
    subject = Subject(code="ROSTER102", name="Different Semester Subject", semester=3)
    db.session.add_all([student, subject])
    db.session.commit()

    response = client.get(f"/attendance/mark?subject_id={subject.id}")

    assert response.status_code == 200
    assert "Other Semester Student" not in response.get_data(as_text=True)


def test_attendance_post_ignores_out_of_semester_student(app, client):
    matching_student = _student("POST001", "Matching Semester Student")
    other_student = _student("POST002", "Other Semester Student")
    other_student.semester = 5
    subject = Subject(code="POST101", name="Post Subject", semester=3)
    db.session.add_all([matching_student, other_student, subject])
    db.session.commit()
    attendance_date = "2026-04-10"

    response = client.post(
        "/attendance/mark",
        data={
            "subject_id": str(subject.id),
            "date": attendance_date,
            f"present_{matching_student.id}": "on",
            f"present_{other_student.id}": "on",
        },
    )

    assert response.status_code == 302
    records = Attendance.query.filter_by(
        subject_id=subject.id, date=date.fromisoformat(attendance_date)
    ).all()
    assert len(records) == 1
    assert records[0].student_id == matching_student.id
    assert records[0].status == "Present"


def test_attendance_page_shows_message_for_empty_roster(app, client):
    student = _student("EMPTY001", "Semester Three Student")
    subject = Subject(code="EMPTY101", name="Empty Roster Subject", semester=5)
    db.session.add_all([student, subject])
    db.session.commit()

    response = client.get(f"/attendance/mark?subject_id={subject.id}")

    assert response.status_code == 200
    assert "No students are assigned to semester 5 for this subject." in response.get_data(as_text=True)
