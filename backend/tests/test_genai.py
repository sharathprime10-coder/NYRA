import os

from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

try:
    response = client.models.generate_content(
        model="gemini-3.6-flash", contents="Hello"
    )
    print("3.6 Flash success:", response.text)
except Exception as e:
    print("3.6 Flash failed:", e)

try:
    response = client.models.generate_content(
        model="gemini-3.5-flash", contents="Hello"
    )
    print("3.5 Flash success:", response.text)
except Exception as e:
    print("3.5 Flash failed:", e)
