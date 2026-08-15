import os
import sys

from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.rag_service import query_knowledge_base

try:
    response = query_knowledge_base("Who is the PM of India?")
    print("Success:", response)
except Exception as e:
    print("Failed:", e)
