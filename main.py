import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------
# 1. DATABASE CONFIGURATION
# --------------------------------------------------

# Use DATABASE_PATH if provided by the deployment service.
# Otherwise, create students.db in the project folder.
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = Path(
    os.getenv("DATABASE_PATH", str(BASE_DIR / "students.db"))
)
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection():
    """Create a connection to the SQLite database."""
    connection = sqlite3.connect(str(DATABASE_PATH))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    """Create the students table if it does not exist."""
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                student_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                date_of_birth TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT,
                course TEXT,
                address TEXT,
                enrollment_date TEXT
            )
            """
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Students Database CRUD API",
    description="An internship project using FastAPI and SQLite.",
    version="1.0.0",
    lifespan=lifespan,
)


# --------------------------------------------------
# 2. INPUT AND OUTPUT MODELS
# --------------------------------------------------

class StudentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    date_of_birth: date
    email: str = Field(min_length=3, max_length=254)
    phone: Optional[str] = Field(default=None, max_length=20)
    course: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = Field(default=None, max_length=250)
    enrollment_date: Optional[date] = None

    model_config = ConfigDict(str_strip_whitespace=True)

    # Validate a basic email format without extra dependencies.
    @classmethod
    def validate_email(cls, value):
        return value


class StudentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    date_of_birth: Optional[date] = None
    email: Optional[str] = Field(default=None, min_length=3, max_length=254)
    phone: Optional[str] = Field(default=None, max_length=20)
    course: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = Field(default=None, max_length=250)
    enrollment_date: Optional[date] = None

    model_config = ConfigDict(str_strip_whitespace=True)


class StudentResponse(BaseModel):
    student_id: int
    name: str
    date_of_birth: date
    email: str
    phone: Optional[str] = None
    course: Optional[str] = None
    address: Optional[str] = None
    enrollment_date: Optional[date] = None


# --------------------------------------------------
# 3. HELPER FUNCTIONS
# --------------------------------------------------

def get_student_or_404(student_id: int):
    """Return a student or raise a 404 error."""
    with get_connection() as connection:
        student = connection.execute(
            "SELECT * FROM students WHERE student_id = ?",
            (student_id,),
        ).fetchone()

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Student not found",
        )

    return dict(student)


def handle_database_error(error: sqlite3.IntegrityError):
    """Convert database constraint errors into API errors."""
    if "UNIQUE constraint failed: students.email" in str(error):
        raise HTTPException(
            status_code=409,
            detail="A student with this email already exists.",
        )
    raise HTTPException(
        status_code=400,
        detail="The student data violates a database constraint.",
    )


def validate_email_format(email: str):
    """Perform a basic email-format check."""
    import re

    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    if not re.fullmatch(pattern, email):
        raise HTTPException(
            status_code=422,
            detail="Please provide a valid email address.",
        )


# --------------------------------------------------
# 4. HOME / HEALTH CHECK
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "Students Database CRUD API is running!",
        "documentation": "/docs",
    }


# --------------------------------------------------
# 5. CREATE: ADD A STUDENT
# --------------------------------------------------

@app.post(
    "/students",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_student(student: StudentCreate):
    validate_email_format(student.email)

    if student.date_of_birth > date.today():
        raise HTTPException(
            status_code=422,
            detail="Date of birth cannot be in the future.",
        )

    if (
        student.enrollment_date is not None
        and student.enrollment_date > date.today()
    ):
        raise HTTPException(
            status_code=422,
            detail="Enrollment date cannot be in the future.",
        )

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO students (
                    name, date_of_birth, email, phone,
                    course, address, enrollment_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    student.name,
                    student.date_of_birth.isoformat(),
                    student.email,
                    student.phone,
                    student.course,
                    student.address,
                    (
                        student.enrollment_date.isoformat()
                        if student.enrollment_date
                        else None
                    ),
                ),
            )
            student_id = cursor.lastrowid

    except sqlite3.IntegrityError as error:
        handle_database_error(error)

    return get_student_or_404(student_id)


# --------------------------------------------------
# 6. READ: LIST AND FILTER STUDENTS
# --------------------------------------------------

@app.get("/students", response_model=list[StudentResponse])
def list_students(
    name: Optional[str] = None,
    dob_after: Optional[date] = None,
):
    query = "SELECT * FROM students WHERE 1=1"
    parameters = []

    if name:
        query += " AND name LIKE ?"
        parameters.append(f"%{name}%")

    if dob_after:
        query += " AND date_of_birth > ?"
        parameters.append(dob_after.isoformat())

    query += " ORDER BY student_id"

    with get_connection() as connection:
        students = connection.execute(
            query, parameters
        ).fetchall()

    return [dict(student) for student in students]


# --------------------------------------------------
# 7. READ: GET ONE STUDENT
# --------------------------------------------------

@app.get(
    "/students/{student_id}",
    response_model=StudentResponse,
)
def get_student(student_id: int):
    return get_student_or_404(student_id)


# --------------------------------------------------
# 8. UPDATE: MODIFY A STUDENT
# --------------------------------------------------

@app.put(
    "/students/{student_id}",
    response_model=StudentResponse,
)
def update_student(student_id: int, student: StudentUpdate):
    # Confirm that the student exists.
    get_student_or_404(student_id)

    changes = student.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one field to update.",
        )

    if "name" in changes and changes["name"] is None:
        raise HTTPException(
            status_code=422,
            detail="Name cannot be null.",
        )

    if "date_of_birth" in changes:
        dob = changes["date_of_birth"]
        if dob is None or dob > date.today():
            raise HTTPException(
                status_code=422,
                detail="Provide a valid date of birth.",
            )

    if "email" in changes:
        if changes["email"] is None:
            raise HTTPException(
                status_code=422,
                detail="Email cannot be null.",
            )
        validate_email_format(changes["email"])

    if "enrollment_date" in changes:
        enrollment = changes["enrollment_date"]
        if enrollment is not None and enrollment > date.today():
            raise HTTPException(
                status_code=422,
                detail="Enrollment date cannot be in the future.",
            )

    # Convert date values to strings for SQLite.
    for field, value in changes.items():
        if isinstance(value, date):
            changes[field] = value.isoformat()

    allowed_fields = {
        "name", "date_of_birth", "email", "phone",
        "course", "address", "enrollment_date",
    }

    fields = [
        field for field in changes if field in allowed_fields
    ]
    assignments = ", ".join(f"{field} = ?" for field in fields)
    values = [changes[field] for field in fields]

    try:
        with get_connection() as connection:
            connection.execute(
                f"UPDATE students SET {assignments} WHERE student_id = ?",
                values + [student_id],
            )
    except sqlite3.IntegrityError as error:
        handle_database_error(error)

    return get_student_or_404(student_id)


# --------------------------------------------------
# 9. DELETE: REMOVE A STUDENT
# --------------------------------------------------

@app.delete("/students/{student_id}")
def delete_student(student_id: int):
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM students WHERE student_id = ?",
            (student_id,),
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Student not found",
            )

    return {
        "message": "Student deleted successfully",
        "student_id": student_id,
    }