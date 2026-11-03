"""Pandas + NumPy processing. All heavy logic lives here, not in the routes."""
import numpy as np
import pandas as pd
from sqlalchemy import text

from ..extensions import db


# ---------------------------------------------------------------- loading ---
def load_attendance_df():
    """Load attendance joined with student & subject info into a DataFrame."""
    query = text("""
        SELECT a.student_id, a.subject_id, a.date, a.status,
               s.roll_no, s.name, s.department, sub.name AS subject
        FROM attendance a
        JOIN students s  ON s.id  = a.student_id
        JOIN subjects sub ON sub.id = a.subject_id
    """)
    df = pd.read_sql(query, db.engine, parse_dates=["date"])
    df["present"] = (df["status"] == "Present").astype(int)
    return df


def load_marks_df():
    query = text("""
        SELECT m.student_id, m.subject_id, m.exam_type, m.score, m.max_score,
               s.roll_no, s.name, sub.name AS subject
        FROM marks m
        JOIN students s ON s.id = m.student_id
        JOIN subjects sub ON sub.id = m.subject_id
    """)
    df = pd.read_sql(query, db.engine)
    df["score_pct"] = df["score"] / df["max_score"] * 100
    return df


# ------------------------------------------------------------ percentages ---
def student_percentages(df, threshold):
    """Attendance % per student + risk flag + classes needed + z-score."""
    cols = ["student_id", "roll_no", "name", "department", "total",
            "attended", "percentage", "status", "classes_needed", "z_score"]
    if df.empty:
        return pd.DataFrame(columns=cols)

    g = (df.groupby(["student_id", "roll_no", "name", "department"])
           .agg(total=("present", "size"), attended=("present", "sum"))
           .reset_index())

    g["percentage"] = np.round(g["attended"] / g["total"] * 100, 2)
    g["status"] = np.where(g["percentage"] < threshold, "At Risk", "Safe")

    # consecutive classes x a student must attend so that
    # (attended + x) / (total + x) >= threshold / 100
    needed = np.ceil((threshold * g["total"] - 100 * g["attended"]) / (100 - threshold))
    g["classes_needed"] = np.where(g["percentage"] < threshold, needed, 0).astype(int)

    # z-score: how far each student is from the class mean (NumPy)
    pct = g["percentage"].to_numpy(dtype=float)
    std = pct.std()
    g["z_score"] = np.round((pct - pct.mean()) / std, 2) if std > 0 else 0.0
    return g[cols]


def subject_percentages(df):
    if df.empty:
        return pd.DataFrame(columns=["subject", "percentage"])
    s = df.groupby("subject")["present"].mean().mul(100).round(2).reset_index()
    s.columns = ["subject", "percentage"]
    return s.sort_values("percentage")


def department_percentages(df):
    if df.empty:
        return pd.DataFrame(columns=["department", "percentage"])
    d = df.groupby("department")["present"].mean().mul(100).round(2).reset_index()
    d.columns = ["department", "percentage"]
    return d.sort_values("percentage")


def subject_matrix(df):
    """Pivot table: students x subjects (attendance %)."""
    if df.empty:
        return [], []
    pv = (df.pivot_table(index=["roll_no", "name"], columns="subject",
                         values="present", aggfunc="mean") * 100).round(1)
    rows = [{"roll_no": r, "name": n, "values": vals.tolist()}
            for (r, n), vals in zip(pv.index, pv.to_numpy())]
    return list(pv.columns), rows


# ----------------------------------------------------------------- trends ---
def weekly_trend(df):
    """Weekly attendance % -> (labels, values)."""
    if df.empty:
        return [], []
    w = df.set_index("date")["present"].resample("W").mean().dropna() * 100
    w = w.round(1)
    return [d.strftime("%d %b") for d in w.index], w.tolist()


def trend_direction(values):
    """Fit a straight line with np.polyfit; slope tells the direction."""
    if len(values) < 3:
        return "Not enough data", 0.0
    slope = float(np.polyfit(np.arange(len(values)), values, 1)[0])
    if slope > 0.5:
        return "Improving", round(slope, 2)
    if slope < -0.5:
        return "Declining", round(slope, 2)
    return "Stable", round(slope, 2)


# ------------------------------------------------------------- statistics ---
def class_stats(percent_df):
    if percent_df.empty:
        return {"mean": 0, "median": 0, "std": 0, "min": 0, "max": 0}
    p = percent_df["percentage"].to_numpy(dtype=float)
    return {"mean": round(float(np.mean(p)), 2),
            "median": round(float(np.median(p)), 2),
            "std": round(float(np.std(p)), 2),
            "min": round(float(p.min()), 2),
            "max": round(float(p.max()), 2)}


def attendance_marks_correlation(att_df, marks_df, threshold):
    """Pearson correlation between attendance % and average marks %."""
    if att_df.empty or marks_df.empty:
        return None, []
    pct = student_percentages(att_df, threshold)[["student_id", "name", "percentage"]]
    avg = marks_df.groupby("student_id")["score_pct"].mean().round(2).reset_index()
    m = pct.merge(avg, on="student_id")
    if len(m) < 3:
        return None, []
    r = float(np.corrcoef(m["percentage"], m["score_pct"])[0, 1])
    points = [{"x": float(a), "y": float(b), "name": n}
              for a, b, n in zip(m["percentage"], m["score_pct"], m["name"])]
    return round(r, 3), points


# ---------------------------------------------------------- student level ---
def student_subject_percentages(df, student_id):
    d = df[df["student_id"] == student_id]
    if d.empty:
        return []
    s = d.groupby("subject")["present"].agg(["size", "sum"]).reset_index()
    s["percentage"] = np.round(s["sum"] / s["size"] * 100, 2)
    return s.rename(columns={"size": "total", "sum": "attended"}).to_dict("records")


def student_weekly_trend(df, student_id):
    return weekly_trend(df[df["student_id"] == student_id])
