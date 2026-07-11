import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")

    # Storage locations
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    CHROMA_DIR = os.path.join(BASE_DIR, "data", "chroma_db")
    SQLITE_DB = os.path.join(BASE_DIR, "data", "chat_history.db")

    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB per upload
    ALLOWED_EXTENSIONS = {"pdf"}

    # Chunking
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 150

    # A page with less than this many extracted characters is treated as a
    # scanned/image page and routed through OCR instead of plain text extraction.
    OCR_TEXT_THRESHOLD = 30

    # Embeddings (downloaded once from HuggingFace on first run, cached after that)
    EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

    # Ollama models - both must be pulled locally first:
    #   ollama pull llama3.2
    #   ollama pull llama3.2-vision
    OLLAMA_TEXT_MODEL = os.getenv("OLLAMA_TEXT_MODEL", "llama3.2")
    OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llama3.2-vision")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    # If the vision model isn't installed, the app degrades gracefully instead
    # of crashing: images/graphs are skipped and a warning is shown once.
    ENABLE_VISION = os.getenv("ENABLE_VISION", "true").lower() == "true"

    # Retrieval
    TOP_K = 5

    # Conversation memory: how many previous turns get fed back into the prompt
    MAX_HISTORY_TURNS = 6
