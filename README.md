# AI Research Assistant

A local-first RAG (Retrieval-Augmented Generation) system for reasoning over research
PDFs — multi-document Q&A, document comparison, research summarization, and
understanding of scanned pages, tables, and figures. Everything runs on your own
machine through [Ollama](https://ollama.com); no document ever leaves your device.

## Features

- **Multi-PDF support** — upload several documents and query across all of them, or scope a question to just one
- **Semantic search (RAG)** — ChromaDB + sentence-transformer embeddings retrieve the most relevant passages before the LLM answers
- **Table-aware** — tables are extracted with `pdfplumber` and kept as structured markdown, not flattened into prose
- **Scanned page support** — pages with little/no extractable text are automatically OCR'd with Tesseract
- **Figure & graph understanding** — embedded images are described by a vision model (`llama3.2-vision`) so charts and diagrams become searchable text
- **Document comparison** — ask a question across 2+ documents and get a structured "what each says / where they agree / where they differ" answer
- **Research summarization** — map-reduce summarization over an entire document, not just the first few pages
- **Conversation memory** — each chat is a persisted session; follow-up questions have context, and past conversations can be reopened from the History tab
- **Page-level citations** — every answer lists which document, page, and content type (text/table/figure) it drew from

## Architecture

```
PDF ─┬─► pypdf (text per page) ──────────────┐
     ├─► PyMuPDF render + Tesseract OCR ─────┤  (only for pages with ~no extractable text)
     ├─► pdfplumber (tables → markdown) ─────┼──► chunker ──► sentence-transformers ──► ChromaDB
     └─► PyMuPDF (embedded images) ──────────┘         (embed)                (store, per-doc metadata)
                  │
                  ▼
        llama3.2-vision (describe figure)

User question ──► ChromaDB semantic search (filtered by selected doc_ids)
              ──► prompt = retrieved chunks + conversation history + question
              ──► Ollama / Llama 3.2 ──► answer + citations ──► SQLite (session memory)
```

**Why one Chroma collection instead of one-per-document?** Every chunk is tagged
with a `doc_id` in its metadata. A single collection with a `where` filter lets one
query span any subset of documents — which is what makes both multi-document Q&A
and the comparison feature possible without duplicating the retrieval logic.

**Why a separate vision model instead of asking Llama 3.2 to "look" at images?**
Text-only Llama 3.2 has no vision capability at all — it's a different model
(`llama3.2-vision`) with separate weights. This project describes each figure once
at ingestion time and embeds that description like any other chunk, rather than
re-sending images on every question. If the vision model isn't installed, the app
detects that at startup and degrades gracefully — text and tables still work, image
understanding is skipped with a clear log message instead of a crash.

## Project structure

```
ai-research-assistant/
├── app.py                  # Flask app factory + entry point
├── config.py                # All settings in one place
├── core/
│   ├── document_loader.py   # PDF → text/table/image chunk extraction
│   ├── ocr_engine.py         # Tesseract wrapper for scanned pages
│   ├── vision_engine.py       # llama3.2-vision wrapper for figures/graphs
│   ├── chunker.py              # Text splitting
│   ├── vector_store.py          # ChromaDB + embeddings
│   ├── llm_engine.py             # Ollama text generation
│   ├── memory_manager.py          # Conversation history formatting
│   ├── rag_pipeline.py             # Single-document / multi-document Q&A
│   ├── comparator.py                # Document comparison logic
│   ├── summarizer.py                 # Map-reduce summarization
│   └── ingest.py                      # Orchestrates the full upload pipeline
├── database/
│   ├── db.py                # SQLite schema + connection
│   └── models.py             # CRUD helpers
├── routes/
│   ├── documents.py          # upload / list / delete
│   ├── chat.py                # chat / compare / summarize
│   └── history.py              # sessions
├── templates/                 # Jinja HTML (single-page app shell)
├── static/css, static/js       # Styling + frontend logic
└── requirements.txt
```

## Setup

**1. Prerequisites**

- Python 3.10+
- [Ollama](https://ollama.com) installed and running
- Tesseract OCR (`sudo apt-get install tesseract-ocr` on Ubuntu, `brew install tesseract` on Mac)

**2. Pull the models**

```bash
ollama pull llama3.2
ollama pull llama3.2-vision   # optional — enables figure/graph understanding
```

**3. Install and run**

```bash
git clone <your-repo-url>
cd ai-research-assistant
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Open `http://localhost:5000`. The first PDF you upload will trigger a one-time
download of the embedding model (~90MB) from HuggingFace.

> **On macOS:** port 5000 is often taken by AirPlay Receiver. If the app won't
> start, either disable AirPlay Receiver in System Settings, or run
> `PORT=5001 python app.py` and open `localhost:5001` instead.

> Don't want to install the ~8GB vision model? Set `ENABLE_VISION=false` in `.env` —
> everything else (text, tables, OCR, chat, comparison, summarization, memory) still
> works fully.

## Roadmap

This project grew through deliberate versions rather than being built all at once:

- **V1** — single-PDF upload + basic RAG chat
- **V2** — chat history sidebar + persisted sessions
- **V3** — multi-PDF support
- **V4** — table extraction + document comparison
- **V5** — conversation memory across turns
- **V6 (this version)** — OCR for scanned pages, figure/graph understanding via a
  vision model, and map-reduce research summarization

Ideas for what's next:
- Streaming responses (token-by-token) instead of waiting for the full answer
- Re-ranking retrieved chunks with a cross-encoder before generation, for better precision on longer documents
- Exporting a session as a shareable Markdown/PDF research brief with citations
- Swapping ChromaDB for a hosted vector DB (e.g. Pinecone/Qdrant Cloud) as a scaling exercise

## Tech stack

Python · Flask · ChromaDB · sentence-transformers · pdfplumber · PyMuPDF · pypdf ·
Tesseract OCR · Ollama (Llama 3.2 + Llama 3.2 Vision) · SQLite · vanilla JS
