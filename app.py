from flask import Flask, render_template, request
from dataset.career_data import career_database
from google import genai
from config import GEMINI_API_KEY
from pypdf import PdfReader
import os

app = Flask(__name__)

# Upload folder
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Create uploads folder automatically
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)


# ---------------- HOME ---------------- #

@app.route("/")
def home():
    return render_template("index.html")


# ---------------- CAREER PAGE ---------------- #

@app.route("/career")
def career():
    return render_template("career.html")


# ---------------- CAREER RESULT ---------------- #

# ---------------- CAREER RESULT ---------------- #

@app.route("/result", methods=["POST"])
def result():

    degree = request.form["degree"]
    interest = request.form["interest"]
    skills = request.form["skills"]
    location = request.form["location"]

    prompt = f"""
You are Career Compass AI, an expert AI Career Counselor.

Analyze the student's profile and recommend the TOP 3 most suitable careers.

Student Profile
-----------------------
Degree: {degree}
Interest: {interest}
Skills: {skills}
Preferred Location: {location}

Generate a detailed professional report.

Return your answer exactly in this format.

# 🎯 AI Career Analysis Report

## 🥇 Recommendation 1

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

-------------------------------------------------

## 🥈 Recommendation 2

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

-------------------------------------------------

## 🥉 Recommendation 3

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

-------------------------------------------------

## 📅 6-Month Learning Roadmap

Month 1:
Month 2:
Month 3:
Month 4:
Month 5:
Month 6:

-------------------------------------------------

## 🎓 Recommended Certifications

- Certification 1
- Certification 2
- Certification 3

-------------------------------------------------

## 📈 Industry Outlook

Briefly explain the future demand for these careers over the next 5 years.

-------------------------------------------------

## 💡 Final Advice

Write 5–8 lines of personalized career advice based on the student's profile.
"""

    try:

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        ai_result = response.text

    except Exception as e:

        ai_result = f"""
Error generating AI recommendation.

{str(e)}
"""

    return render_template(
        "result.html",
        degree=degree,
        interest=interest,
        skills=skills,
        location=location,
        ai_result=ai_result
    )


# ---------------- SUMMARIZER PAGE ---------------- #

@app.route("/summarizer")
def summarizer():
    return render_template("summarizer.html")


# ---------------- PDF SUMMARIZER ---------------- #

@app.route("/summarize", methods=["POST"])
def summarize():

    try:

        if "pdf" not in request.files:
            return "No PDF uploaded."

        pdf = request.files["pdf"]

        if pdf.filename == "":
            return "Please select a PDF."

        filepath = os.path.join(app.config["UPLOAD_FOLDER"], pdf.filename)

        pdf.save(filepath)

        reader = PdfReader(filepath)

        text = ""

        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted

        if text.strip() == "":
            return "No readable text found in PDF."

        prompt = f"""
Summarize this report.

Provide:

• Main Topic

• Key Findings

• Important Points

• Conclusion

Report:

{text}
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        summary = response.text

        return render_template(
            "summary.html",
            summary=summary
        )

    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    app.run(debug=True)