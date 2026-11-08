from datetime import date

from app.blueprints import analytics
from app.extensions import db
from app.models import Student, Subject


def test_saving_attendance_clears_spark_cache(app, client):
    student = Student(
        roll_no="CACHE001",
        name="Cache Test Student",
        department="CSE",
        semester=3,
    )
    subject = Subject(
        code="CACHE101",
        name="Cache Test Subject",
        department="CSE",
        semester=3,
    )
    db.session.add_all([student, subject])
    db.session.commit()

    analytics._spark_cache["result"] = {"stale": True}
    response = client.post(
        "/attendance/mark",
        data={
            "subject_id": str(subject.id),
            "date": date(2026, 11, 8).isoformat(),
            f"present_{student.id}": "on",
        },
    )

    assert response.status_code == 302
    assert "result" not in analytics._spark_cache
    assert analytics._spark_cache["invalidated"] is True
