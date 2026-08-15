import os
import time

from google import genai
from langchain_chroma import Chroma
from langchain_classic.retrievers import (
    ContextualCompressionRetriever,
    EnsembleRetriever,
)
from langchain_community.document_compressors import FlashrankRerank
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document as LangchainDocument
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Initialize FlashRank reranker globally
try:
    flashrank_compressor = FlashrankRerank(top_n=4)
except Exception as e:
    print(f"Warning: Failed to initialize FlashRank: {e}")
    flashrank_compressor = None


from app.core.config import settings

# Initialize Gemini Embeddings
# It uses GEMINI_API_KEY from environment or settings
os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY

embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.2)

# Initialize Chroma Vector Store locally
vector_store = Chroma(
    collection_name="nyra_knowledge_base",
    embedding_function=embeddings,
    persist_directory="./chroma_db",
)

shared_vector_store = Chroma(
    collection_name="nyra_shared_faq",
    embedding_function=embeddings,
    persist_directory="./chroma_db",
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
            if f.state.name == "ACTIVE":
                break
            elif f.state.name == "FAILED":
                raise Exception("Gemini file processing failed")
            time.sleep(2)

        # Extract text
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[
                f,
                "Extract all text from this document accurately. Preserve structure.",
            ],
        )
        return response.text
    finally:
        # Always clean up the file from Google's servers
        try:
            client.files.delete(name=uploaded_file.name)
        except Exception as e:
            print(f"Failed to delete Gemini file {uploaded_file.name}: {e}")


from groq import Groq


def _transcribe_audio_with_groq(file_path: str) -> str:
    """Uses Groq Whisper to transcribe an audio file."""
    client = Groq(api_key=settings.GROQ_API_KEY)

    with open(file_path, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file=(os.path.basename(file_path), file.read()),
            model="whisper-large-v3-turbo",
        )
    return transcription.text


def process_and_store_document(file_path: str, document_id: str, user_id: int):
    """Loads a file, chunks it, and stores embeddings in ChromaDB."""
    chunks = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )

    ext = os.path.splitext(file_path)[1].lower()

    if ext in [".mp3", ".wav", ".m4a"]:
        try:
            print(f"Transcribing audio {file_path} with Groq...")
            transcript = _transcribe_audio_with_groq(file_path)
            doc = LangchainDocument(
                page_content=transcript, metadata={"source": file_path}
            )
            chunks = text_splitter.split_documents([doc])
        except Exception as e:
            print(f"Audio transcription failed: {e}")
    else:
        try:
            # We try PyPDFLoader first. If it's an image or other format, this will throw an exception.
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            chunks = text_splitter.split_documents(docs)
        except Exception as e:
            print(f"Native PDF extraction skipped/failed for {file_path}: {e}")

    has_text = any(chunk.page_content.strip() for chunk in chunks) if chunks else False

    # Fallback to Gemini OCR if PyPDFLoader yields no text (or only empty pages)
    if not has_text and ext not in [".mp3", ".wav", ".m4a"]:
        try:
            print(
                f"No text extracted natively for doc {document_id}. Attempting Gemini OCR..."
            )
            extracted_text = _extract_text_with_gemini(file_path)
            if extracted_text:
                # Wrap text in Langchain Document and split
                doc = LangchainDocument(
                    page_content=extracted_text, metadata={"source": file_path}
                )
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
    """Retrieves relevant chunks from ChromaDB using Hybrid Search (Dense + BM25) and FlashRank reranking."""

    # We'll use this to keep track of the final distance/score for confidence
    top_score = 0.0
    final_docs = []
    is_shared = False

    try:
        # 1. Fetch dense results (wider net: k=10)
        dense_retriever = vector_store.as_retriever(
            search_type="similarity", search_kwargs={"k": 10, "filter": filters}
        )

        # 2. Fetch BM25 Keyword docs
        all_docs_data = vector_store.get(where=filters)

        bm25_retriever = None
        if all_docs_data and all_docs_data.get("documents"):
            bm25_docs = [
                LangchainDocument(page_content=doc, metadata=meta)
                for doc, meta in zip(
                    all_docs_data["documents"], all_docs_data["metadatas"]
                )
            ]
            if bm25_docs:
                bm25_retriever = BM25Retriever.from_documents(bm25_docs)
                bm25_retriever.k = 10

        # 3. Combine Retrievers
        retrievers = [dense_retriever]
        weights = [1.0]
        if bm25_retriever:
            retrievers.append(bm25_retriever)
            weights = [0.5, 0.5]

        ensemble_retriever = EnsembleRetriever(retrievers=retrievers, weights=weights)

        # 4. Rerank with FlashRank if available
        if flashrank_compressor:
            compression_retriever = ContextualCompressionRetriever(
                base_compressor=flashrank_compressor, base_retriever=ensemble_retriever
            )
            final_docs = compression_retriever.invoke(query)
            # FlashRank provides 'relevance_score' in metadata
            if final_docs:
                top_score = final_docs[0].metadata.get("relevance_score", 0.0)
        else:
            final_docs = ensemble_retriever.invoke(query)[:4]
            top_score = 1.0  # fallback score

    except Exception as e:
        print(f"Hybrid retrieval failed: {e}. Falling back to basic dense.")
        # Fallback completely
        dense_results = vector_store.similarity_search_with_score(
            query, k=4, filter=filters
        )
        final_docs = [doc for doc, score in dense_results]
        top_score = (
            1.0 if not dense_results else (1.0 - dense_results[0][1])
        )  # invert distance

    # Confidence scoring based on FlashRank score (usually 0 to 1)
    # If using distance fallback, logic might differ slightly, but we map it roughly:
    if not final_docs or top_score < 0.3:
        confidence = "Low"
    elif top_score < 0.7:
        confidence = "Medium"
    else:
        confidence = "High"

    # Shared FAQ Fallback if low confidence
    if not final_docs or confidence == "Low":
        try:
            shared_results = shared_vector_store.similarity_search_with_score(
                query, k=2
            )
            if shared_results:
                shared_min_dist = min([score for doc, score in shared_results])
                if (
                    shared_min_dist < 0.6
                ):  # Only fallback if shared FAQ has a good match
                    final_docs = [doc for doc, score in shared_results]
                    confidence = "Medium"
                    is_shared = True
        except Exception as e:
            print(f"Shared FAQ retrieval failed: {e}")

    return {
        "answer": "",
        "sources": [
            {
                "document_id": (
                    doc.metadata.get("document_id") if not is_shared else "shared_faq"
                ),
                "source": (
                    doc.metadata.get("source")
                    if not is_shared
                    else "Shared NYRA Knowledge Base"
                ),
                "page": doc.metadata.get("page"),
                "content": doc.page_content,
            }
            for doc in final_docs
        ],
        "confidence": confidence,
        "min_distance": 1.0
        - top_score,  # Mock min_distance so the frontend doesn't break
    }


def delete_document_from_index(document_id: str):
    """Deletes all chunks associated with a document_id from Chroma."""
    try:
        vector_store._collection.delete(where={"document_id": document_id})
    except Exception as e:
        print(f"Error deleting from chroma: {e}")
