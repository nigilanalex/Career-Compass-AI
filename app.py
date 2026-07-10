from flask import Flask, render_template, request
from google import genai
from pypdf import PdfReader
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import sqlite3

try:
    from config import GEMINI_API_KEY
except ImportError:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")


app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf"}
DATABASE_PATH = "career_compass.db"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

client = genai.Client(api_key=GEMINI_API_KEY)


def allowed_pdf(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS app_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS career_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                degree TEXT,
                year TEXT,
                specialization TEXT,
                interest TEXT,
                skills TEXT,
                languages TEXT,
                industry TEXT,
                work_style TEXT,
                location TEXT,
                goal TEXT,
                ai_result TEXT,
                created_at TEXT NOT NULL
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS resume_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                summary TEXT,
                created_at TEXT NOT NULL
            )
        """)


def log_event(level, message, details=""):
    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO app_events (level, message, details, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (level, message, details, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )


def save_career_analysis(profile, ai_result):
    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO career_analyses (
                degree, year, specialization, interest, skills, languages,
                industry, work_style, location, goal, ai_result, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile["degree"],
                profile["year"],
                profile["specialization"],
                profile["interest"],
                profile["skills"],
                profile["languages"],
                profile["industry"],
                profile["work"],
                profile["location"],
                profile["goal"],
                ai_result,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )


def save_resume_analysis(filename, summary):
    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO resume_analyses (filename, summary, created_at)
            VALUES (?, ?, ?)
            """,
            (filename, summary, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )


init_db()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/career")
def career():
    return render_template("career.html")


@app.route("/result", methods=["POST"])
def result():
    degree = request.form["degree"]
    year = request.form["year"]
    specialization = request.form["specialization"]
    interest = ", ".join(request.form.getlist("interest"))
    skills = ", ".join(request.form.getlist("skills"))
    languages = ", ".join(request.form.getlist("languages")) or "Not specified"
    industry = request.form["industry"]
    work = request.form["work"]
    location = ", ".join(request.form.getlist("location"))
    goal = request.form["goal"]

    profile = {
        "degree": degree,
        "year": year,
        "specialization": specialization,
        "interest": interest,
        "skills": skills,
        "languages": languages,
        "industry": industry,
        "work": work,
        "location": location,
        "goal": goal
    }

    prompt = f"""
You are Career Compass AI, an expert AI career counselor.

Analyze the student's profile and recommend the top 3 most suitable careers.

Student Profile
-----------------------
Degree: {degree}
Year of Study: {year}
Specialization: {specialization}
Career Interest: {interest}
Technical Skills: {skills}
Programming Languages: {languages}
Preferred Industry: {industry}
Preferred Work Style: {work}
Preferred Location: {location}
Career Goal: {goal}

Generate a detailed professional report using this structure:

# AI Career Analysis Report

## Recommendation 1
Career:
Match Score:
Expected Salary:
Job Demand:
Top Hiring Companies:
Why this Career:
Skills to Learn:
- Skill 1
- Skill 2
- Skill 3
- Skill 4
- Skill 5

## Recommendation 2
Career:
Match Score:
Expected Salary:
Job Demand:
Top Hiring Companies:
Why this Career:
Skills to Learn:
- Skill 1
- Skill 2
- Skill 3
- Skill 4
- Skill 5

## Recommendation 3
Career:
Match Score:
Expected Salary:
Job Demand:
Top Hiring Companies:
Why this Career:
Skills to Learn:
- Skill 1
- Skill 2
- Skill 3
- Skill 4
- Skill 5

## 6-Month Learning Roadmap
Month 1:
Month 2:
Month 3:
Month 4:
Month 5:
Month 6:

## Recommended Certifications
- Certification 1
- Certification 2
- Certification 3

## Industry Outlook
Explain future demand for these careers over the next 5 years.

## Final Advice
Write personalized career advice based on the student's profile.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        ai_result = response.text
        save_career_analysis(profile, ai_result)
        log_event("info", "Career analysis completed", f"Degree: {degree}; Interests: {interest}")
    except Exception as e:
        ai_result = f"Error generating AI recommendation.\n\n{str(e)}"
        log_event("error", "Career analysis failed", str(e))

    return render_template(
        "result.html",
        degree=degree,
        year=year,
        specialization=specialization,
        interest=interest,
        skills=skills,
        languages=languages,
        industry=industry,
        work=work,
        location=location,
        goal=goal,
        ai_result=ai_result
    )


@app.route("/summarizer")
def summarizer():
    return render_template("summarizer.html")


@app.route("/admin/logs")
def admin_logs():
    with get_db_connection() as connection:
        events = connection.execute(
            "SELECT * FROM app_events ORDER BY id DESC LIMIT 100"
        ).fetchall()
        career_analyses = connection.execute(
            "SELECT * FROM career_analyses ORDER BY id DESC LIMIT 20"
        ).fetchall()
        resume_analyses = connection.execute(
            "SELECT * FROM resume_analyses ORDER BY id DESC LIMIT 20"
        ).fetchall()

    return render_template(
        "admin_logs.html",
        events=events,
        career_analyses=career_analyses,
        resume_analyses=resume_analyses
    )


@app.route("/summarize", methods=["POST"])
def summarize():
    try:
        if "pdf" not in request.files:
            log_event("warning", "Resume upload failed", "No PDF uploaded.")
            return render_template("summarizer.html", error="No PDF uploaded.")

        pdf = request.files["pdf"]

        if pdf.filename == "":
            log_event("warning", "Resume upload failed", "Empty filename.")
            return render_template("summarizer.html", error="Please select a PDF file.")

        if not allowed_pdf(pdf.filename):
            log_event("warning", "Resume upload rejected", f"Invalid file type: {pdf.filename}")
            return render_template("summarizer.html", error="Only PDF files are allowed.")

        filename = secure_filename(pdf.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        pdf.save(filepath)

        reader = PdfReader(filepath)
        text = ""

        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted

        if text.strip() == "":
            log_event("warning", "Resume analysis failed", f"No readable text found in {filename}")
            return render_template("summarizer.html", error="No readable text found in PDF.")

        prompt = f"""
You are Career Compass AI, an expert resume reviewer and career advisor.

Analyze this resume and create a professional resume summary with job recommendations.

Provide the output using this structure:

# Resume Analysis Report

## Candidate Summary
Write a concise 4-5 line professional summary based on the resume.

## Key Skills Found
- Skill 1
- Skill 2
- Skill 3
- Skill 4
- Skill 5

## Experience Level
Classify the candidate as Fresher, Entry Level, Mid Level, or Senior Level.
Explain the reason briefly.

## Best Job Recommendations
Recommend the top 5 suitable job roles.
For each role, include:
- Job Role
- Match Score
- Why it matches
- Skills to improve

## Resume Strengths
- Strength 1
- Strength 2
- Strength 3

## Missing Skills or Gaps
- Gap 1
- Gap 2
- Gap 3

## Improvement Suggestions
Give practical resume and career improvement suggestions.

## Final Career Advice
Give short personalized advice for the candidate's next step.

Resume Text:
{text}
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        summary = response.text
        save_resume_analysis(filename, summary)
        log_event("info", "Resume analysis completed", f"Filename: {filename}")

        return render_template("summary.html", summary=summary)

    except Exception as e:
        log_event("error", "Resume analysis failed", str(e))
        return render_template("summarizer.html", error=f"Error: {e}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
