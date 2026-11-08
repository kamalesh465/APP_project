from datetime import date, timedelta

import pandas as pd

from app.extensions import db
from app.models import Attendance, Student, Subject
from app.services import analytics_service as an


def _attendance_rows(student_id, subject_id, subject, name, present, total):
    rows = []
    for index in range(total):
        rows.append({
            "student_id": student_id,
            "subject_id": subject_id,
            "roll_no": f"R{student_id}",
            "name": name,
            "department": "CSE",
            "subject": subject,
            "present": int(index < present),
        })
    return rows


def test_subject_percentages_use_per_student_subject_counts():
    rows = (
        _attendance_rows(1, 10, "Subject A", "Student One", 3, 4)
        + _attendance_rows(1, 11, "Subject B", "Student One", 2, 4)
    )

    result = an.subject_percentages(pd.DataFrame(rows), threshold=60)
    percentages = result.set_index("subject")["percentage"].to_dict()

    assert percentages == {"Subject A": 75.0, "Subject B": 50.0}


def test_subject_percentage_flags_threshold_and_below_threshold():
    rows = (
        _attendance_rows(1, 10, "Subject A", "Student One", 3, 4)
        + _attendance_rows(1, 11, "Subject B", "Student One", 2, 4)
        + _attendance_rows(2, 12, "Subject C", "Student Two", 3, 5)
    )

    result = an.subject_percentages(pd.DataFrame(rows), threshold=60)
    flags = result.set_index("subject")["below_threshold"].to_dict()

    assert flags == {
        "Subject A": False,
        "Subject B": True,
        "Subject C": False,
    }


def _correlation_data():
    attendance_rows = []
    marks_rows = []
    subject_attendance = {
        10: [20, 50, 80],
        11: [80, 50, 20],
    }
    subject_names = {10: "Subject A", 11: "Subject B"}
    for subject_id, percentages in subject_attendance.items():
        for index, attendance_pct in enumerate(percentages, start=1):
            attendance_rows += _attendance_rows(
                index, subject_id, subject_names[subject_id],
                f"Student {index}", attendance_pct // 10, 10
            )
            # Each subject has marks that rise from 20% to 80%.
            mark_pct = index * 30 - 10
            for exam_score in (mark_pct - 10, mark_pct + 10):
                marks_rows.append({
                    "student_id": index,
                    "subject_id": subject_id,
                    "score": exam_score,
                    "max_score": 100,
                })
    return pd.DataFrame(attendance_rows), pd.DataFrame(marks_rows)


def test_correlation_pairs_attendance_and_marks_within_same_subject():
    attendance_df, marks_df = _correlation_data()

    correlation, pair_count, points, reason = (
        an.subject_attendance_marks_correlation(attendance_df, marks_df)
    )

    assert correlation == 0.0
    assert pair_count == 6
    assert reason is None
    assert {point["subject"] for point in points} == {"Subject A", "Subject B"}
    assert {(point["x"], point["y"]) for point in points} == {
        (20.0, 20.0), (50.0, 50.0), (80.0, 80.0),
        (80.0, 20.0), (50.0, 50.0), (20.0, 80.0),
    }


def test_subject_correlation_requires_three_pairs():
    attendance_df = pd.DataFrame(
        _attendance_rows(1, 10, "Subject A", "Student One", 3, 4)
        + _attendance_rows(2, 10, "Subject A", "Student Two", 2, 4)
    )
    marks_df = pd.DataFrame([
        {"student_id": 1, "subject_id": 10, "score": 80, "max_score": 100},
        {"student_id": 2, "subject_id": 10, "score": 60, "max_score": 100},
    ])

    correlation, pair_count, points, reason = (
        an.subject_attendance_marks_correlation(attendance_df, marks_df)
    )

    assert correlation is None
    assert pair_count == 2
    assert len(points) == 2
    assert "at least 3" in reason.lower()


def test_subject_correlation_returns_reason_for_zero_variance():
    attendance_df = pd.DataFrame(
        _attendance_rows(1, 10, "Subject A", "Student One", 2, 4)
        + _attendance_rows(2, 10, "Subject A", "Student Two", 2, 4)
        + _attendance_rows(3, 10, "Subject A", "Student Three", 2, 4)
    )
    marks_df = pd.DataFrame([
        {"student_id": student_id, "subject_id": 10,
         "score": score, "max_score": 100}
        for student_id, score in ((1, 60), (2, 70), (3, 80))
    ])

    correlation, pair_count, _, reason = (
        an.subject_attendance_marks_correlation(attendance_df, marks_df)
    )

    assert correlation is None
    assert pair_count == 3
    assert "zero variance" in reason.lower()


def test_empty_subject_analytics_and_pages_return_empty_results(app, client):
    attendance_df = an.load_attendance_df()
    marks_df = an.load_marks_df()

    assert an.subject_percentages(attendance_df, threshold=75).empty
    assert an.subject_attendance_marks_correlation(attendance_df, marks_df) == (
        None, 0, [], "No matching attendance and marks data."
    )
    assert client.get("/analytics/trends").status_code == 200
    assert client.get("/analytics/defaulters").status_code == 200


def test_attendance_without_marks_is_skipped_in_subject_correlation():
    attendance_rows = []
    marks_rows = []
    for student_id, attended, score in (
        (1, 1, 80),
        (2, 2, 60),
        (3, 3, 40),
        (4, 4, None),
    ):
        attendance_rows += _attendance_rows(
            student_id, 10, "Subject A", f"Student {student_id}", attended, 4
        )
        if score is not None:
            marks_rows.append({
                "student_id": student_id,
                "subject_id": 10,
                "score": score,
                "max_score": 100,
            })

    correlation, pair_count, points, reason = (
        an.subject_attendance_marks_correlation(
            pd.DataFrame(attendance_rows), pd.DataFrame(marks_rows)
        )
    )

    assert correlation == -1.0
    assert pair_count == 3
    assert {point["name"] for point in points} == {
        "Student 1", "Student 2", "Student 3"
    }
    assert reason is None


def test_existing_overall_percentages_and_defaulters_are_unchanged(app, client):
    subject = Subject(code="AN101", name="Analytics Subject",
                      department="CSE", semester=3)
    students = [
        Student(roll_no=f"AN00{i}", name=name, department="CSE", semester=3)
        for i, name in enumerate(("Below Threshold", "At Threshold", "Above Threshold"), 1)
    ]
    db.session.add_all([subject, *students])
    db.session.commit()

    statuses = (
        ["Present", "Absent"],
        ["Present", "Present", "Present", "Absent"],
        ["Present", "Present", "Present", "Present"],
    )
    for student, student_statuses in zip(students, statuses):
        for offset, status in enumerate(student_statuses):
            db.session.add(Attendance(
                student_id=student.id,
                subject_id=subject.id,
                date=date(2026, 1, 1) + timedelta(days=offset),
                status=status,
            ))
    db.session.commit()

    overall = an.student_percentages(
        an.load_attendance_df(), app.config["ATTENDANCE_THRESHOLD"]
    ).set_index("name")
    assert overall.loc["Below Threshold", "percentage"] == 50.0
    assert overall.loc["At Threshold", "percentage"] == 75.0
    assert overall.loc["At Threshold", "status"] == "Safe"
    assert overall.loc["Above Threshold", "percentage"] == 100.0

    response = client.get("/analytics/defaulters")
    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Below Threshold" in page
    assert "At Threshold" not in page
    assert "Above Threshold" not in page
