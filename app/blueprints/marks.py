from flask import Blueprint, render_template, request, redirect, url_for, flash

from ..extensions import db
from ..models import Student, Subject, Mark

bp = Blueprint("marks", __name__)


@bp.route("/")
def index():
    marks = (Mark.query.join(Student).join(Subject)
             .order_by(Student.roll_no, Subject.name).limit(200).all())
    return render_template("marks/index.html", marks=marks)


@bp.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        db.session.add(Mark(student_id=int(request.form["student_id"]),
                            subject_id=int(request.form["subject_id"]),
                            exam_type=request.form["exam_type"].strip(),
                            score=float(request.form["score"]),
                            max_score=float(request.form["max_score"])))
        db.session.commit()
        flash("Mark recorded.", "success")
        return redirect(url_for("marks.index"))
    return render_template("marks/form.html",
                           students=Student.query.order_by(Student.roll_no).all(),
                           subjects=Subject.query.order_by(Subject.name).all())
