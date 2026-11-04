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
    db.create_all()

    existing_subjects = Subject.query.all()
    subjects = []
    new_subjects = []
    for code, name in SUBJECTS:
        subject = next((item for item in existing_subjects
                        if item.code.casefold() == code.casefold()), None)
        if subject is None:
            subject = next((item for item in existing_subjects
                            if item.name.casefold() == name.casefold()), None)
        if subject is None:
            subject = Subject(code=code, name=name)
            new_subjects.append(subject)
        subjects.append(subject)
    db.session.add_all(new_subjects)
    db.session.flush()
    subjects = list({subject.id: subject for subject in subjects}.values())

    roll_nos = [f"23{DEPTS[i % 5]}{i + 1:03d}" for i in range(N_STUDENTS)]
    students_by_roll = {student.roll_no: student for student in
                        Student.query.filter(Student.roll_no.in_(roll_nos)).all()}
    students = []
    new_students = []
    for i in range(N_STUDENTS):
        roll_no = roll_nos[i]
        student = students_by_roll.get(roll_no)
        if student is None:
            student = Student(
                roll_no=roll_no,
                name=f"{rng.choice(FIRST)} {rng.choice(LAST)}",
                department=DEPTS[i % 5],
                semester=int(rng.choice([3, 5])))
            new_students.append(student)
            students_by_roll[roll_no] = student
        students.append(student)
    db.session.add_all(new_students)
    db.session.flush()
    db.session.commit()

    days = pd.bdate_range(end=date.today(), periods=N_DAYS).date
    t = np.linspace(-1, 1, N_DAYS)

    subject_ids = [subject.id for subject in subjects]
    attendance_keys = {
        (row.student_id, row.subject_id, row.date)
        for row in Attendance.query.filter(Attendance.subject_id.in_(subject_ids)).all()
    }
    mark_keys = {
        (row.student_id, row.subject_id, row.exam_type)
        for row in Mark.query.filter(Mark.subject_id.in_(subject_ids)).all()
    }
    att_rows, mark_rows = [], []
    for st in students:
        base = rng.beta(8, 2.5)                  # student's typical attendance rate
        drift = rng.normal(0, 0.08)              # improving or declining over time
        for sub in subjects:
            prob = np.clip(base + drift * t + rng.normal(0, 0.03), 0.2, 0.99)
            present = rng.random(N_DAYS) < prob
            for d, p in zip(days, present):
                key = (st.id, sub.id, d)
                if key not in attendance_keys:
                    att_rows.append(dict(student_id=st.id, subject_id=sub.id, date=d,
                                         status="Present" if p else "Absent"))
            for exam in EXAMS:                   # marks loosely depend on attendance
                key = (st.id, sub.id, exam)
                if key in mark_keys:
                    continue
                score = np.clip(30 + 60 * base + rng.normal(0, 8), 0, 100)
                mark_rows.append(dict(student_id=st.id, subject_id=sub.id,
                                      exam_type=exam, score=round(float(score), 1),
                                      max_score=100))

    db.session.bulk_insert_mappings(Attendance, att_rows)
    db.session.bulk_insert_mappings(Mark, mark_rows)
    db.session.commit()
    print(f"Ensured {len(students)} students and {len(subjects)} seed subjects; "
          f"added {len(att_rows)} attendance rows and {len(mark_rows)} marks.")
