from flask import Flask, redirect, render_template, request, session, url_for
from google import genai
from pypdf import PdfReader
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps
import os
import requests
import sqlite3

try:
    import config
except ImportError:
    config = None


def config_value(name, default=None):
    if config and hasattr(config, name):
        return getattr(config, name)
    return os.environ.get(name, default)


app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf"}
DATABASE_PATH = "career_compass.db"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.secret_key = os.environ.get("SECRET_KEY", "career-compass-dev-secret")

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

AI_PROVIDER = config_value("AI_PROVIDER", "auto").lower()
OPENAI_API_KEY = config_value("OPENAI_API_KEY")
OPENAI_MODEL = config_value("OPENAI_MODEL", "gpt-4.1-mini")
GEMINI_API_KEY = config_value("GEMINI_API_KEY")
GEMINI_MODEL = config_value("GEMINI_MODEL", "gemini-2.5-flash")
ENABLE_DEMO_FALLBACK = str(config_value("ENABLE_DEMO_FALLBACK", "true")).lower() == "true"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
client = gemini_client



def allowed_pdf(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)

    return wrapped_view


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
You are Career Compass AI, a senior career strategist and technical mentor.

Analyze the student's profile and write a polished, professional career advisory brief.
Use confident, specific language. Avoid generic filler. Make the report sound like it was written by a real career consultant.

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

Generate a detailed professional report using this exact structure:

# Career Advisory Brief

## Executive Summary
Write 4-5 crisp lines explaining the student's current direction, strongest signal, and most realistic career path.

## Career Fit Snapshot
Overall Fit Score:
Primary Career Direction:
Strongest Current Skills:
Biggest Skill Gap:
Best Next Action:

## Priority Recommendation 1
Role:
Match Score:
Expected Salary:
Job Demand:
Best-Fit Companies:
Why This Role Fits:
Skills To Build Next:
- Skill
- Skill
- Skill
- Skill
Starter Project:

## Priority Recommendation 2
Role:
Match Score:
Expected Salary:
Job Demand:
Best-Fit Companies:
Why This Role Fits:
Skills To Build Next:
- Skill
- Skill
- Skill
- Skill
Starter Project:

## Priority Recommendation 3
Role:
Match Score:
Expected Salary:
Job Demand:
Best-Fit Companies:
Why This Role Fits:
Skills To Build Next:
- Skill
- Skill
- Skill
- Skill
Starter Project:

## Skill Gap Tracker
Already Strong:
- Skill
- Skill

Need to Learn:
- Skill
- Skill
- Skill

Suggested Projects:
- Project
- Project
- Project

## 90-Day Action Plan
Days 1-30:
Days 31-60:
Days 61-90:

## 6-Month Growth Roadmap
Month 1-2:
Month 3-4:
Month 5-6:

## Recommended Certifications
- Certification
- Certification
- Certification

## Industry Outlook
Explain the demand, market direction, and hiring outlook for these roles.

## Consultant's Final Advice
Write a direct, motivating final paragraph with a clear next step.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
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


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            log_event("info", "Admin login successful", f"Username: {username}")
            return redirect(request.args.get("next") or url_for("admin_logs"))

        error = "Invalid username or password."
        log_event("warning", "Admin login failed", f"Username: {username}")

    return render_template("admin_login.html", error=error)


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))


@app.route("/admin/logs")
@admin_required
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


@app.route("/history")
@admin_required
def history():
    with get_db_connection() as connection:
        career_analyses = connection.execute(
            "SELECT * FROM career_analyses ORDER BY id DESC"
        ).fetchall()
        resume_analyses = connection.execute(
            "SELECT * FROM resume_analyses ORDER BY id DESC"
        ).fetchall()

    return render_template(
        "history.html",
        career_analyses=career_analyses,
        resume_analyses=resume_analyses
    )


@app.route("/admin/logs/clear", methods=["POST"])
@admin_required
def clear_logs():
    level = request.form.get("level", "all")

    with get_db_connection() as connection:
        if level == "all":
            connection.execute("DELETE FROM app_events")
            message = "All logs cleared"
        else:
            connection.execute("DELETE FROM app_events WHERE level = ?", (level,))
            message = f"{level.title()} logs cleared"

    log_event("info", "Admin maintenance", message)
    return redirect(url_for("admin_logs"))


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

## Resume Score
Overall Resume Score: /100
ATS Friendliness: /100
Skills Clarity: /100
Project Strength: /100
Experience Quality: /100

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
- Expected Salary Range
- Why it matches
- Skills to improve

## Skill Gap Tracker
Already Strong:
- Skill 1
- Skill 2

Need to Improve:
- Skill 1
- Skill 2
- Skill 3

Suggested Projects:
- Project 1
- Project 2

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
            model="gemini-2.0-flash",
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
