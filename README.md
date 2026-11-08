# APP_project — Smart Attendance and Student Progress Monitoring System

A Flask application for managing student records, recording attendance and
marks, and exploring attendance and academic trends. It stores data in SQLite,
uses Pandas and NumPy for standard analytics, and provides an optional
PySpark-based analytics workflow.

## Features

- Dashboard with student and subject totals, attendance summaries, at-risk
  counts, and weekly attendance trends.
- Create, view, update, search, and delete student records.
- Add and delete subjects from the dashboard, including their related records.
- Record attendance by subject and date; review attendance reports.
- Record and view student marks.
- Analyze attendance defaulters, trends, departments, subjects, and the
  relationship between attendance and marks.
- Run optional Spark analyses for department attendance, subject ranking,
  rolling four-week attendance, consecutive-absence streaks, and at-risk
  counts.
- Export the sample/analysis attendance data as a CSV in `data/`.

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

   `create_all()` does not add the new required subject department column to
   an existing SQLite database. To rebuild the local database with the current
   schema and sample data, stop the application and run these commands from the
   project root:

   ```powershell
   Remove-Item .\attendance.db
   python seed.py
   ```

   Rebuilding deletes the existing local database and its records.

7. Start the Flask application:

   ```powershell
   python run.py
   ```

   Open <http://127.0.0.1:5000> in a browser. Keep the terminal open while
   using the application; press **Ctrl+C** to stop the server.

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
