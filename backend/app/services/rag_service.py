import logging
import os
import shutil
import time

from google import genai
from langchain_classic.retrievers import (
    ContextualCompressionRetriever,
    EnsembleRetriever,
)
from langchain_community.document_compressors import FlashrankRerank
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document as LangchainDocument
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Initialize FlashRank reranker globally
try:
    from flashrank import Ranker

    FlashrankRerank.model_rebuild()
    flashrank_compressor = FlashrankRerank(top_n=4)
except Exception as e:
    print(f"Warning: Failed to initialize FlashRank: {e}")
    flashrank_compressor = None


from app.core.config import settings

# Initialize Gemini Embeddings
os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY

embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")
llm = ChatGoogleGenerativeAI(model="gemini-3.7-flash", temperature=0.2)

# Initialize Qdrant Client locally
qdrant_client = QdrantClient(path="./qdrant_db")

# Ensure collections exist
collection_params = models.VectorParams(size=3072, distance=models.Distance.COSINE)
if not qdrant_client.collection_exists("nyra_knowledge_base"):
    qdrant_client.create_collection(
        "nyra_knowledge_base", vectors_config=collection_params
    )
if not qdrant_client.collection_exists("nyra_shared_faq"):
    qdrant_client.create_collection("nyra_shared_faq", vectors_config=collection_params)

vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name="nyra_knowledge_base",
    embedding=embeddings,
)

shared_vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name="nyra_shared_faq",
    embedding=embeddings,
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
            model="gemini-3.7-flash",
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


def process_and_store_document(file_path: str, document_id: str, user_id: int | str):
    """Loads a file, chunks it, and stores embeddings in Qdrant."""
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
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            chunks = text_splitter.split_documents(docs)
        except Exception as e:
            print(f"Native PDF extraction skipped/failed for {file_path}: {e}")

    has_text = any(chunk.page_content.strip() for chunk in chunks) if chunks else False

    if not has_text and ext not in [".mp3", ".wav", ".m4a"]:
        try:
            print(
                f"No text extracted natively for doc {document_id}. Attempting Gemini OCR..."
            )
            extracted_text = _extract_text_with_gemini(file_path)
            if extracted_text:
                doc = LangchainDocument(
                    page_content=extracted_text, metadata={"source": file_path}
                )
                chunks = text_splitter.split_documents([doc])
        except Exception as e:
            print(f"Gemini OCR fallback failed: {e}")

    valid_chunks = []
    for i, chunk in enumerate(chunks):
        if chunk.page_content.strip():
            chunk.metadata["document_id"] = str(document_id)
            chunk.metadata["user_id"] = str(user_id)
            chunk.metadata["chunk_index"] = i
            valid_chunks.append(chunk)

    if valid_chunks:
        vector_store.add_documents(valid_chunks)
        sample_meta = valid_chunks[0].metadata
        logging.info(
            "chunks_written",
            extra={
                "event": "chunks_written",
                "document_id": sample_meta["document_id"],
                "document_id_type": type(sample_meta["document_id"]).__name__,
                "user_id": sample_meta["user_id"],
                "user_id_type": type(sample_meta["user_id"]).__name__,
                "chunk_count": len(valid_chunks),
            },
        )
    return len(valid_chunks)


def query_knowledge_base(query: str, filters: dict = None):
    """Retrieves relevant chunks from Qdrant using Hybrid Search (Dense + BM25) and FlashRank reranking."""
    start_time = time.time()
    top_score = 0.0
    final_docs = []
    is_shared = False

    try:
        # Convert dict filters to Qdrant models.Filter
        qdrant_filter = None
        if filters:
            must_conditions = []
            for k, v in filters.items():
                must_conditions.append(
                    models.FieldCondition(
                        key=f"metadata.{k}", match=models.MatchValue(value=v)
                    )
                )
            qdrant_filter = models.Filter(must=must_conditions)

        dense_retriever = vector_store.as_retriever(
            search_type="similarity", search_kwargs={"k": 10, "filter": qdrant_filter}
        )

        # 2. Fetch BM25 Keyword docs
        bm25_retriever = None
        if filters:
            scroll_res, _ = qdrant_client.scroll(
                collection_name="nyra_knowledge_base",
                scroll_filter=qdrant_filter,
                limit=1000,
                with_payload=True,
            )
            bm25_docs = [
                LangchainDocument(
                    page_content=r.payload.get("page_content", ""),
                    metadata=r.payload.get("metadata", {}),
                )
                for r in scroll_res
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
            if final_docs:
                top_score = final_docs[0].metadata.get("relevance_score", 0.0)
        else:
            final_docs = ensemble_retriever.invoke(query)[:4]
            top_score = 1.0  # fallback score

    except Exception as e:
        print(f"Hybrid retrieval failed: {e}. Falling back to basic dense.")
        dense_results = vector_store.similarity_search_with_score(
            query, k=4, filter=qdrant_filter
        )
        final_docs = [doc for doc, score in dense_results]
        top_score = 1.0 if not dense_results else (1.0 - dense_results[0][1])

    if not final_docs or top_score < 0.3:
        confidence = "Low"
    elif top_score < 0.7:
        confidence = "Medium"
    else:
        confidence = "High"

    if not final_docs or confidence == "Low":
        try:
            shared_results = shared_vector_store.similarity_search_with_score(
                query, k=2
            )
            if shared_results:
                shared_min_dist = min([score for doc, score in shared_results])
                if shared_min_dist < 0.6:
                    final_docs = [doc for doc, score in shared_results]
                    confidence = "Medium"
                    is_shared = True
        except Exception as e:
            print(f"Shared FAQ retrieval failed: {e}")

    duration = (time.time() - start_time) * 1000
    logging.info(
        "retrieval_completed",
        extra={
            "event": "retrieval_completed",
            "duration_ms": round(duration, 1),
            "chunks_returned": len(final_docs),
        },
    )

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
        "min_distance": 1.0 - top_score,
    }


def delete_document_from_index(document_id: str):
    """Deletes all chunks associated with a document_id from Qdrant."""
    try:
        qdrant_client.delete(
            collection_name="nyra_knowledge_base",
            points_selector=models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.document_id",
                        match=models.MatchValue(value=str(document_id)),
                    )
                ]
            ),
        )
    except Exception as e:
        print(f"Error deleting from qdrant: {e}")
