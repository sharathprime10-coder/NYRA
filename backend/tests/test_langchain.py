import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
os.environ["GOOGLE_API_KEY"] = api_key

try:
    llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0.2)
    res = llm.invoke("Hello")
    print("langchain gemini-3.6-flash success:", res)
except Exception as e:
    print("langchain gemini-3.6-flash failed:", e)

try:
    llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0.2)
    res = llm.invoke("Hello")
    print("langchain gemini-3.5-flash success:", res)
except Exception as e:
    print("langchain gemini-3.5-flash failed:", e)
