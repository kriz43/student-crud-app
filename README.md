# Students Database CRUD Application

## Project Overview
A Python backend application for managing student records.
Built using FastAPI and SQLite for the EWB Edu Tech internship assignment.

## Features
- Create student records
- List and filter students
- Retrieve an individual student
- Update existing student information
- Delete student records
- Input validation and error handling
- SQLite database persistence
- Interactive API documentation

## Technologies
- Python
- FastAPI
- SQLite
- Uvicorn
- Git and GitHub

## Prerequisites
- Python 3
- Git
- Visual Studio Code (recommended)

## Installation

Clone the repository:

git clone YOUR_GITHUB_REPOSITORY_URL

Enter the project folder:

cd student-crud-app

Create a virtual environment:

python -m venv .venv

Activate it on Windows:

.venv\Scripts\activate

Activate it on macOS/Linux:

source .venv/bin/activate

Install dependencies:

python -m pip install -r requirements.txt

## Run the Application

python -m uvicorn main:app --reload

Home:
http://127.0.0.1:8000/

Interactive API documentation:
http://127.0.0.1:8000/docs

## API Endpoints

POST /students
GET /students
GET /students/{student_id}
PUT /students/{student_id}
DELETE /students/{student_id}

Optional list filters:
GET /students?name=Aarav
GET /students?dob_after=2005-01-01

## Database
SQLite stores student records in students.db.
The database table is created automatically when the application starts.

## Testing
Use the interactive Swagger UI at /docs to test
create, read, update and delete operations.

Use only dummy student information in demonstrations.

## Deployment
The application can be deployed as a Python web service.
Configure a persistent storage location for the SQLite database
if records must survive deployment restarts.

## Future Enhancement
An optional Ollama integration can answer natural-language
questions using student records retrieved by backend code.