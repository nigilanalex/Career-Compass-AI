from flask import Flask, render_template, request
from google import genai
from pypdf import PdfReader
from werkzeug.utils import secure_filename
import os

try:
    from config import GEMINI_API_KEY
except ImportError:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")


app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

client = genai.Client(api_key=GEMINI_API_KEY)


def allowed_pdf(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


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
    interest = request.form["interest"]
    skills = request.form["skills"]
    languages = request.form["languages"]
    experience = request.form["experience"]
    industry = request.form["industry"]
    work = request.form["work"]
    location = request.form["location"]
    goal = request.form["goal"]

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
Experience Level: {experience}
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
    except Exception as e:
        ai_result = f"Error generating AI recommendation.\n\n{str(e)}"

    return render_template(
        "result.html",
        degree=degree,
        year=year,
        specialization=specialization,
        interest=interest,
        skills=skills,
        languages=languages,
        experience=experience,
        industry=industry,
        work=work,
        location=location,
        goal=goal,
        ai_result=ai_result
    )


@app.route("/summarizer")
def summarizer():
    return render_template("summarizer.html")


@app.route("/summarize", methods=["POST"])
def summarize():
    try:
        if "pdf" not in request.files:
            return render_template("summarizer.html", error="No PDF uploaded.")

        pdf = request.files["pdf"]

        if pdf.filename == "":
            return render_template("summarizer.html", error="Please select a PDF file.")

        if not allowed_pdf(pdf.filename):
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
            return render_template("summarizer.html", error="No readable text found in PDF.")

        prompt = f"""
Summarize this report.

Provide:
- Main Topic
- Key Findings
- Important Points
- Conclusion

Report:
{text}
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        summary = response.text

        return render_template("summary.html", summary=summary)

    except Exception as e:
        return render_template("summarizer.html", error=f"Error: {e}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
