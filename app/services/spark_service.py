"""PySpark analytical workflow.

Pipeline:  SQLite --(Pandas)--> CSV export --> Spark DataFrame --> analyses
Requires Java 17 (or 11) installed and JAVA_HOME / PATH set.
"""
import os
import sys

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

# make Spark workers use the same interpreter as Flask
os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)

_spark = None


def get_spark():
    global _spark
    if _spark is None:
        _spark = (SparkSession.builder
                  .master("local[2]")
                  .appName("AttendanceAnalytics")
                  .config("spark.sql.shuffle.partitions", "4")
                  .config("spark.ui.enabled", "false")
                  .getOrCreate())
        _spark.sparkContext.setLogLevel("ERROR")
    return _spark


def _rows(sdf):
    return [r.asDict() for r in sdf.collect()]


def run_spark_analysis(att_df, export_dir, threshold):
    """att_df: pandas DataFrame from load_attendance_df()."""
    # 1. export from the database (via Pandas) to CSV
    csv_path = os.path.join(export_dir, "attendance_export.csv")
    att_df.assign(date=att_df["date"].dt.strftime("%Y-%m-%d")).to_csv(csv_path, index=False)

    spark = get_spark()

    # 2. read into a Spark DataFrame
    sdf = (spark.read.csv(csv_path, header=True, inferSchema=True)
                .withColumn("date", F.to_date("date")))
    sdf.createOrReplaceTempView("attendance")

    results = {"total_rows": sdf.count()}

    # 3. department-wise attendance (DataFrame API groupBy)
    dept = (sdf.groupBy("department")
               .agg(F.round(F.avg("present") * 100, 2).alias("percentage"),
                    F.count("*").alias("records"))
               .orderBy("percentage"))
    results["department"] = _rows(dept)

    # 4. subject ranking (Spark SQL)
    subj = spark.sql("""
        SELECT subject, ROUND(AVG(present) * 100, 2) AS percentage,
               RANK() OVER (ORDER BY AVG(present)) AS worst_rank
        FROM attendance GROUP BY subject ORDER BY percentage
    """)
    results["subjects"] = _rows(subj)

    # 5. rolling 4-week attendance per student (window function)
    weekly = (sdf.withColumn("week", F.date_trunc("week", "date"))
                 .groupBy("student_id", "name", "week")
                 .agg(F.avg("present").alias("weekly_rate")))
    w = Window.partitionBy("student_id").orderBy("week").rowsBetween(-3, 0)
    rolling = weekly.withColumn("rolling_4wk", F.avg("weekly_rate").over(w))
    latest = Window.partitionBy("student_id").orderBy(F.col("week").desc())
    worst_recent = (rolling.withColumn("rn", F.row_number().over(latest))
                           .filter("rn = 1")
                           .select("name", F.round(F.col("rolling_4wk") * 100, 2).alias("rolling_pct"))
                           .orderBy("rolling_pct").limit(10))
    results["rolling"] = _rows(worst_recent)

    # 6. longest streak of consecutive absences (gaps-and-islands with windows)
    base = Window.partitionBy("student_id", "subject").orderBy("date")
    by_status = Window.partitionBy("student_id", "subject", "status").orderBy("date")
    islands = (sdf.withColumn("grp", F.row_number().over(base) - F.row_number().over(by_status))
                  .filter(F.col("status") == "Absent")
                  .groupBy("student_id", "name", "subject", "grp")
                  .agg(F.count("*").alias("streak")))
    streaks = (islands.groupBy("name")
                      .agg(F.max("streak").alias("longest_absence_streak"))
                      .orderBy(F.col("longest_absence_streak").desc()).limit(10))
    results["streaks"] = _rows(streaks)

    # 7. count of students below the threshold
    per_student = sdf.groupBy("student_id").agg(F.avg("present").alias("rate"))
    results["at_risk_count"] = per_student.filter(F.col("rate") * 100 < threshold).count()
    return results
