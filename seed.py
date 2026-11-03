"""Fills the database with realistic sample data (NumPy-generated).

Usage:  python seed.py
"""
from datetime import date

import numpy as np
import pandas as pd

from app import create_app
from app.extensions import db
from app.models import Student, Subject, Attendance, Mark

N_STUDENTS = 60
N_DAYS = 60
rng = np.random.default_rng(42)

FIRST = ["Aarav", "Diya", "Karthik", "Meera", "Rohan", "Sneha", "Vikram", "Anjali",
         "Arjun", "Priya", "Nikhil", "Divya", "Surya", "Lakshmi", "Harish", "Kavya",
         "Rahul", "Nisha", "Gokul", "Swathi"]
LAST = ["Kumar", "Raj", "Nair", "Iyer", "Reddy", "Sharma", "Pillai", "Menon", "Das", "Singh"]
DEPTS = ["CSE", "ECE", "MECH", "CIVIL", "IT"]
SUBJECTS = [("CS101", "Python Programming"), ("CS102", "Data Structures"),
            ("CS103", "Database Systems"), ("CS104", "Mathematics"), ("CS105", "Operating Systems")]
EXAMS = ["Internal 1", "Internal 2", "Model Exam"]

app = create_app()
with app.app_context():
    db.drop_all()
    db.create_all()

    subjects = [Subject(code=c, name=n) for c, n in SUBJECTS]
    students = []
    for i in range(N_STUDENTS):
        students.append(Student(
            roll_no=f"23{DEPTS[i % 5]}{i + 1:03d}",
            name=f"{rng.choice(FIRST)} {rng.choice(LAST)}",
            department=DEPTS[i % 5],
            semester=int(rng.choice([3, 5]))))
    db.session.add_all(subjects + students)
    db.session.commit()

    days = pd.bdate_range(end=date.today(), periods=N_DAYS).date
    t = np.linspace(-1, 1, N_DAYS)

    att_rows, mark_rows = [], []
    for st in students:
        base = rng.beta(8, 2.5)                  # student's typical attendance rate
        drift = rng.normal(0, 0.08)              # improving or declining over time
        for sub in subjects:
            prob = np.clip(base + drift * t + rng.normal(0, 0.03), 0.2, 0.99)
            present = rng.random(N_DAYS) < prob
            for d, p in zip(days, present):
                att_rows.append(dict(student_id=st.id, subject_id=sub.id, date=d,
                                     status="Present" if p else "Absent"))
            for exam in EXAMS:                   # marks loosely depend on attendance
                score = np.clip(30 + 60 * base + rng.normal(0, 8), 0, 100)
                mark_rows.append(dict(student_id=st.id, subject_id=sub.id,
                                      exam_type=exam, score=round(float(score), 1),
                                      max_score=100))

    db.session.bulk_insert_mappings(Attendance, att_rows)
    db.session.bulk_insert_mappings(Mark, mark_rows)
    db.session.commit()
    print(f"Seeded {len(students)} students, {len(subjects)} subjects, "
          f"{len(att_rows)} attendance rows, {len(mark_rows)} marks.")
