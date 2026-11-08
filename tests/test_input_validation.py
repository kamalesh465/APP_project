from app.extensions import db
from app.models import Mark, Student, Subject


def _student():
    return Student(
        roll_no="VALID001",
        name="Validation Student",
        department="CSE",
        semester=3,
    )


def _subject():
    return Subject(
        code="VALID101",
        name="Validation Subject",
        department="CSE",
        semester=3,
    )


def test_invalid_attendance_date_flashes_and_redirects(client):
    response = client.post(
        "/attendance/mark",
        data={"subject_id": "1", "date": "not-a-date"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Select a valid subject and date." in response.get_data(as_text=True)


def test_mark_score_above_maximum_is_rejected(app, client):
    student = _student()
    subject = _subject()
    db.session.add_all([student, subject])
    db.session.commit()

    response = client.post(
        "/marks/add",
        data={
            "student_id": str(student.id),
            "subject_id": str(subject.id),
            "exam_type": "Internal 1",
            "score": "101",
            "max_score": "100",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Score must be between 0" in response.get_data(as_text=True)
    assert Mark.query.count() == 0


def test_unknown_mark_subject_id_is_handled(app, client):
    student = _student()
    db.session.add(student)
    db.session.commit()

    response = client.post(
        "/marks/add",
        data={
            "student_id": str(student.id),
            "subject_id": "99999",
            "exam_type": "Internal 1",
            "score": "80",
            "max_score": "100",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Select a valid student and subject." in response.get_data(as_text=True)
    assert Mark.query.count() == 0


def test_invalid_student_semester_is_rejected(app, client):
    response = client.post(
        "/students/add",
        data={
            "roll_no": "INVALIDSEM001",
            "name": "Invalid Semester Student",
            "department": "CSE",
            "semester": "9",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "valid department and semester" in response.get_data(as_text=True)
    assert Student.query.filter_by(roll_no="INVALIDSEM001").first() is None
