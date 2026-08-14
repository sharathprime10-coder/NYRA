import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document as LangchainDocument
import time
from google import genai

from app.core.config import settings

# Initialize Gemini Embeddings
# It uses GEMINI_API_KEY from environment or settings
os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY

embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")
llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0.2)

# Initialize Chroma Vector Store locally
vector_store = Chroma(
    collection_name="nyra_knowledge_base",
    embedding_function=embeddings,
    persist_directory="./chroma_db"
)

def _extract_text_with_gemini(file_path: str) -> str:
    """Uses Gemini to extract text from an image-based PDF."""
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    # Upload the file
    uploaded_file = client.files.upload(file=file_path)
    
    try:
        # Wait for file to be processed
        while True:
            f = client.files.get(name=uploaded_file.name)
            if f.state.name == 'ACTIVE':
                break
            elif f.state.name == 'FAILED':
                raise Exception("Gemini file processing failed")
            time.sleep(2)
            
        # Extract text
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=[f, "Extract all text from this document accurately. Preserve structure."]
        )
        return response.text
    finally:
        # Always clean up the file from Google's servers
        try:
            client.files.delete(name=uploaded_file.name)
        except Exception as e:
            print(f"Failed to delete Gemini file {uploaded_file.name}: {e}")

def process_and_store_document(file_path: str, document_id: str, user_id: int):
    """Loads a file, chunks it, and stores embeddings in ChromaDB."""
    chunks = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )
    
    try:
        # We try PyPDFLoader first. If it's an image or other format, this will throw an exception.
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        chunks = text_splitter.split_documents(docs)
    except Exception as e:
        print(f"Native PDF extraction skipped/failed for {file_path}: {e}")

    
    # Fallback to Gemini OCR if PyPDFLoader yields no text
    if not chunks:
        try:
            print(f"No text extracted natively for doc {document_id}. Attempting Gemini OCR...")
            extracted_text = _extract_text_with_gemini(file_path)
            if extracted_text:
                # Wrap text in Langchain Document and split
                doc = LangchainDocument(page_content=extracted_text, metadata={"source": file_path})
                chunks = text_splitter.split_documents([doc])
        except Exception as e:
            print(f"Gemini OCR fallback failed: {e}")
            
    # Add metadata and filter empty chunks
    valid_chunks = []
    for i, chunk in enumerate(chunks):
        if chunk.page_content.strip():
            chunk.metadata["document_id"] = document_id
            chunk.metadata["user_id"] = user_id
            chunk.metadata["chunk_index"] = i
            valid_chunks.append(chunk)
        
    if valid_chunks:
        vector_store.add_documents(valid_chunks)
    return len(valid_chunks)

def query_knowledge_base(query: str, filters: dict = None):
    """Retrieves relevant chunks from ChromaDB.
    Optimized to skip LLM generation since LangGraph handles answering."""
    
    search_kwargs = {"k": 4}
    if filters:
        search_kwargs["filter"] = filters

    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs=search_kwargs
    )
    
    # Just get retrieved documents
    retrieved_docs = retriever.invoke(query)
    
    # Calculate a mock confidence score based on the number of retrieved docs
    confidence = "High" if len(retrieved_docs) >= 3 else "Medium" if len(retrieved_docs) > 0 else "Low"
    
    # Skip LLM formulation since the LangGraph agent will formulate the final answer using this context
    return {
        "answer": "",
        "sources": [
            {
                "document_id": doc.metadata.get("document_id"),
                "source": doc.metadata.get("source"),
                "page": doc.metadata.get("page"),
                "content": doc.page_content
            } for doc in retrieved_docs
        ],
        "confidence": confidence
    }

def delete_document_from_index(document_id: str):
    """Deletes all chunks associated with a document_id from Chroma."""
    try:
        vector_store._collection.delete(where={"document_id": document_id})
    except Exception as e:
        print(f"Error deleting from chroma: {e}")
