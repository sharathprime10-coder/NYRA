import os

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
os.environ["GOOGLE_API_KEY"] = api_key

try:
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")
    res = embeddings.embed_query("Hello")
    print("models/gemini-embedding-2 success! length:", len(res))
except Exception as e:
    print("models/gemini-embedding-2 failed:", e)

try:
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    res = embeddings.embed_query("Hello")
    print("models/text-embedding-004 success! length:", len(res))
except Exception as e:
    print("models/text-embedding-004 failed:", e)
