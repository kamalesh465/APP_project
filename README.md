# Smart Attendance and Student Progress Monitoring System

A Flask application for recording subject-wise attendance for students whose
department and semester match the subject. It calculates attendance
percentages, identifies students below the required threshold, and analyzes
trends using Pandas, NumPy, and optional PySpark workflows.

## Features

- Dashboard with student and subject totals, average attendance, below-
  threshold counts, lowest-attendance students, and weekly trends.
- Student create, edit, search, detail, and delete pages; student details
  include overall and subject-wise attendance and marks.
- Subject create, edit, and delete with department and semester fields. The
  subject delete modal displays related attendance and marks record counts.
- Attendance entry restricted to students matching both the subject's
  department and semester, ordered by roll number. Existing records for the
  same student, subject, and date are updated instead of duplicated.
- Attendance reports with overall percentages, below-threshold status, and a
  student-by-subject attendance matrix.
- Marks entry with subjects filtered to the selected student's department and
  semester, and a marks list capped at 200 rows.
- Trends and analytics pages with weekly, department, and subject summaries,
  overall and subject-matched attendance/marks correlation, and a subject-wise
  student attendance table.
- Optional Spark analyses for department attendance, subject ranking, rolling
  four-week attendance, consecutive-absence streaks, and at-risk counts. The
  Spark workflow exports attendance data to `data/attendance_export.csv`.

## Technology stack

- Python and Flask
- Flask-SQLAlchemy and SQLite
- Pandas and NumPy
- PySpark
- Jinja2 templates, Bootstrap, and Chart.js

## Project structure

The repository root is the folder containing `run.py`.

```text
APP_project/
├── .github/
│   └── copilot-instructions.md
├── app/
│   ├── __init__.py
│   ├── extensions.py
│   ├── models.py
│   ├── blueprints/
│   │   ├── analytics.py
│   │   ├── attendance.py
│   │   ├── main.py
│   │   ├── marks.py
│   │   ├── subjects.py
│   │   └── students.py
│   ├── services/
│   │   ├── analytics_service.py
│   │   └── spark_service.py
│   └── templates/
│       ├── base.html
│       ├── dashboard.html
│       ├── partials/
│       │   ├── _flash.html
│       │   ├── _macros.html
│       │   ├── _navbar.html
│       │   └── _subject_manager.html
│       ├── analytics/
│       ├── attendance/
│       ├── marks/
│       └── students/
├── data/
│   ├── .gitkeep
│   └── attendance_export.csv
├── .env.example
├── .gitignore
├── config.py
├── README.md
├── requirements.txt
├── run.py
└── seed.py
```

The SQLite database is created in the project root and is intentionally
ignored by Git. The CSV in `data/` is kept in version control.

## How each project criterion is met

| Criterion | Implementation |
|---|---|
| Flask | Application factory and startup in `app/__init__.py` and `run.py`. |
| SQLAlchemy | Database extension, models, and database configuration in `app/extensions.py`, `app/models.py`, and `config.py`. |
| Blueprints | Feature routes in `app/blueprints/main.py`, `students.py`, `subjects.py`, `attendance.py`, `marks.py`, and `analytics.py`. |
| Jinja2 | Shared layout and macros in `app/templates/base.html` and `app/templates/partials/`; feature pages are in the `analytics/`, `attendance/`, `marks/`, and `students/` template directories. |
| NumPy/Pandas | Standard attendance and marks analytics in `app/services/analytics_service.py`. |
| PySpark | Spark analyses in `app/services/spark_service.py`, invoked by `app/blueprints/analytics.py`. |

## Windows setup

1. Install Python (Python 3.12 is recommended) and Git. For the Spark workflow,
   install a JDK as described below.
2. Clone the team repository and enter its root folder (the folder containing
   `run.py`):

   ```powershell
   git clone <repository-url> APP_project
   Set-Location .\APP_project
   ```

3. Create and activate a virtual environment:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use
   `.\.venv\Scripts\python.exe` in place of `python` in the following commands.

4. Install the pinned Python dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. Copy the environment-variable example:

   ```powershell
   Copy-Item .env.example .env
   ```

   Replace the placeholder with a unique random value before running the app.
   `config.py` loads this file from the project root and also accepts
   `SECRET_KEY` from the process environment. To set the value for the current
   PowerShell session instead:

   ```powershell
   $env:SECRET_KEY = "<your-private-random-value>"
   ```

   The application exits with a clear error if `SECRET_KEY` is not set.

6. (Optional) Create the demonstration database and data:

   ```powershell
   python seed.py
   ```

   `seed.py` adds any missing sample subjects, students, attendance, and marks.
   It does not remove existing attendance or marks rows and can be run again
   without duplicating seeded records.

7. Start the Flask application:

   ```powershell
   python run.py
   ```

   Open <http://127.0.0.1:5000> in a browser. Keep the terminal open while
   using the application; press **Ctrl+C** to stop the server.

## Database rebuild

`create_all()` creates missing tables but does not add columns to an existing
database. If the local database has an outdated schema, first stop the
application and back up any data you need. From the project root, run:

```powershell
if (Test-Path .\attendance.db) { Remove-Item .\attendance.db }
python seed.py
```

This deletes the local database and all its records, then creates the current
schema and demonstration data.

## PySpark and Java

The optional PySpark analytics page requires Java. Install a JDK and set
`JAVA_HOME` to its installation directory, adding its `bin` folder to `Path`.
For the pinned PySpark 4.3.0 dependency, use JDK 17; JDK 11 may not be
compatible with this Spark version. Restart PowerShell after changing system
environment variables. Check the setup with:

```powershell
java -version
echo $env:JAVA_HOME
```

The regular Flask application and Pandas/NumPy analytics do not require Java.
Spark starts only when its analytics workflow is run. The first Spark run may
take several seconds.

## Testing

Run the test suite from the project root:

```powershell
python -m pytest
```

The current suite contains 25 tests across `tests/test_core_features.py` and
`tests/test_subject_analytics.py`. It covers attendance recording and updates,
overall percentages and threshold behavior, weekly trends, department- and
semester-matched rosters, marks subject matching, subject-wise percentages,
subject-matched correlation, and empty or insufficient analytics data.

## Limitations and future enhancements

- Server-side input validation is incomplete: malformed attendance dates or
  IDs and non-numeric mark values are not consistently handled; student
  semester values are not constrained to 1–8, and mark scores are not checked
  against their maximum on the server.
- CSRF protection is limited to subject add, edit, and delete; other POST
  forms are not protected.
- Student deletion uses a confirmation prompt but does not show related record
  counts. Deleting a student cascades to related attendance and marks.
- Debug mode is enabled directly in `run.py`, rather than controlled by a
  `FLASK_DEBUG` environment variable.
- Spark cache invalidation is called after subject changes, but not after
  attendance or marks changes.
- The marks list is limited to 200 rows and displays “Showing up to 200 rows”;
  it is not ordered by recency and does not provide pagination.
- Add login and role-based access control.
- Add an enrollment table to support electives and subjects shared across
  departments or semesters.
- Support multiple attendance sessions per day, an excused attendance status,
  and an audit log of attendance changes.
- Consider PostgreSQL or MySQL for production deployments.

## Team Git workflow

1. Clone the repository and enter the project root.
2. Before starting work, update your local `main` branch:

   ```powershell
   git switch main
   git pull origin main
   ```

3. Create a feature branch:

   ```powershell
   git switch -c feature/<name>
   ```

4. Make and test your changes, then commit them:

   ```powershell
   git add <files>
   git commit -m "Describe the change"
   ```

5. Push the feature branch and open a Pull Request targeting `main`:

   ```powershell
   git push -u origin feature/<name>
   ```

   Do not push feature work directly to `main`.

## Team module assignments

Fill in the team member column together.

| Module | Description | Team Member |
|---|---|---|
| Application and dashboard | Flask app factory, configuration, and dashboard | TBD |
| Student management | Student records and CRUD pages | TBD |
| Attendance and marks | Attendance entry, reports, and mark records | TBD |
| Standard analytics | Pandas and NumPy reports and trends | TBD |
| Spark analytics | PySpark export and analytical workflow | TBD |
| Database and sample data | SQLAlchemy models and seed script | TBD |

## Notes

- `run.py` uses Flask's development server with debug mode enabled. Do not
  expose it to the public internet.
- The templates load Bootstrap and Chart.js from CDNs, so those assets require
  internet access in the browser.
- The project creates missing database tables at application startup. The
  seed script is only needed when you want demonstration data.
