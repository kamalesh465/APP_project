import os

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

SECRET_KEY_VALUE = os.environ.get("SECRET_KEY")
if not SECRET_KEY_VALUE:
    raise RuntimeError(
        "SECRET_KEY is required. Set it in the environment or project .env file."
    )


class Config:
    SECRET_KEY = SECRET_KEY_VALUE
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "attendance.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ATTENDANCE_THRESHOLD = 75          # minimum required attendance (%)
    EXPORT_DIR = os.path.join(BASE_DIR, "data")
