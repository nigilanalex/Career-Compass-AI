from google import genai
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Explain Artificial Intelligence in 3 simple sentences for a first-year engineering student."
)

print(response.text)