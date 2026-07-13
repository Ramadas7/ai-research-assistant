from core import vector_store, llm_engine, memory_manager
from database.models import get_document
from config import Config

SYSTEM_PROMPT = (
    "You are a research assistant. Answer using ONLY the information in the provided "
    "context - if the answer isn't there, say so honestly instead of guessing.\n\n"
    "Formatting rules:\n"
    "- Write in clean Markdown: use **bold** for key terms, bullet or numbered lists "
    "where they aid clarity, and fenced code blocks for any pseudocode, formulas, or code.\n"
    "- Synthesize the answer in your own words rather than quoting the context verbatim.\n"
    "- Do not include bracketed citations like '[filename.pdf]' in your answer - the "
    "sources are already shown separately in the interface.\n"
    "- Be concise and avoid repeating yourself."
)

BROAD_QUESTION_KEYWORDS = [
    "what is this", "what's this", "summarize", "summary", "overview",
    "key points", "list all", "list of all", "all the lessons", "all the chapters",
    "explain this pdf", "explain this document", "main idea", "in brief",
    "briefly explain", "characters in this book", "characters in the book",
]

BROAD_MAP_SYSTEM = (
    "You are scanning one excerpt of a larger document to help answer a specific "
    "question about the document as a whole. If this excerpt contains anything "
    "relevant to the question, summarize it in 1-2 sentences. If it contains "
    "nothing relevant, respond with exactly: NOT RELEVANT"
)

BROAD_REDUCE_SYSTEM = (
    "You are answering a question about a document using notes gathered from "
    "across the ENTIRE document, not just one passage. Write in clean Markdown: "
    "use **bold** for key terms and bullet points where they help. Synthesize a "
    "complete answer in your own words rather than just restating the notes."
)


def is_broad_question(question: str) -> bool:
    q = question.lower()
    return any(kw in q for kw in BROAD_QUESTION_KEYWORDS)


def _batch(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _gather_relevant_notes(question: str, doc_ids: list[str]):
    """
    Generator: yields {"type": "progress", "message": ...} while scanning, then
    a final {"type": "result", "notes": [...], "doc_names": [...]}.

    Caps the total number of chunks scanned at Config.BROAD_QUESTION_MAX_CHUNKS
    regardless of document size - a 564-chunk book and a 40-chunk paper take
    roughly the same time. When a document exceeds the cap, it samples evenly
    across the whole thing (every Nth chunk) rather than just the first N, so
    coverage stays spread across the beginning, middle, and end.
    """
    doc_names = []
    all_batches = []

    for doc_id in doc_ids:
        doc = get_document(doc_id)
        filename = doc["filename"] if doc else doc_id
        doc_names.append(filename)

        chunks = vector_store.get_all_chunks(doc_id)
        if len(chunks) > Config.BROAD_QUESTION_MAX_CHUNKS:
            step = len(chunks) / Config.BROAD_QUESTION_MAX_CHUNKS
            chunks = [chunks[int(i * step)] for i in range(Config.BROAD_QUESTION_MAX_CHUNKS)]

        all_batches.extend(_batch(chunks, Config.BROAD_QUESTION_BATCH_SIZE))

    relevant_notes = []
    total = len(all_batches)
    for i, batch in enumerate(all_batches, start=1):
        yield {"type": "progress", "message": f"Reading document... ({i}/{total})"}
        excerpt = "\n\n".join(batch)
        note = llm_engine.generate(f"Question: {question}\n\nExcerpt:\n{excerpt}", system=BROAD_MAP_SYSTEM)
        if "NOT RELEVANT" not in note.upper():
            relevant_notes.append(note)

    yield {"type": "result", "notes": relevant_notes, "doc_names": doc_names}


def _build_context(hits: list[dict]) -> str:
    if not hits:
        return "No relevant context was found in the document(s)."
    blocks = []
    for h in hits:
        tag = f"[{h['filename']} - page {h['page']} - {h['type']}]"
        blocks.append(f"{tag}\n{h['content']}")
    return "\n\n---\n\n".join(blocks)


def _build_sources(hits: list[dict]) -> list[dict]:
    seen = set()
    sources = []
    for h in hits:
        key = (h["filename"], h["page"], h["type"])
        if key in seen:
            continue
        seen.add(key)
        sources.append({
            "doc": h["filename"],
            "page": h["page"],
            "type": h["type"],
            "snippet": h["content"][:180] + ("..." if len(h["content"]) > 180 else ""),
        })
    return sources


def answer_question(question: str, doc_ids: list[str], session_id: str) -> dict:
    hits = vector_store.query(question, doc_ids)
    context = _build_context(hits)
    history = memory_manager.get_recent_history(session_id)

    prompt = (
        f"Conversation so far:\n{history}\n\n" if history else ""
    ) + f"Context from document(s):\n{context}\n\nQuestion: {question}\n\nAnswer:"

    answer = llm_engine.generate(prompt, system=SYSTEM_PROMPT)
    sources = _build_sources(hits)

    memory_manager.save_turn(session_id, question, answer, sources)

    return {"answer": answer, "sources": sources}


def answer_question_stream(question: str, doc_ids: list[str], session_id: str):
    hits = vector_store.query(question, doc_ids)
    context = _build_context(hits)
    history = memory_manager.get_recent_history(session_id)

    prompt = (
        f"Conversation so far:\n{history}\n\n" if history else ""
    ) + f"Context from document(s):\n{context}\n\nQuestion: {question}\n\nAnswer:"

    full_answer = []
    for piece in llm_engine.generate_stream(prompt, system=SYSTEM_PROMPT):
        full_answer.append(piece)
        yield {"type": "token", "content": piece}

    answer = "".join(full_answer)
    sources = _build_sources(hits)
    memory_manager.save_turn(session_id, question, answer, sources)

    yield {"type": "done", "sources": sources}


def answer_broad_question(question: str, doc_ids: list[str], session_id: str) -> dict:
    relevant_notes, doc_names = [], []
    for event in _gather_relevant_notes(question, doc_ids):
        if event["type"] == "result":
            relevant_notes, doc_names = event["notes"], event["doc_names"]

    combined_notes = "\n".join(f"- {n}" for n in relevant_notes) or "No relevant information found."
    prompt = f"Question: {question}\n\nNotes gathered from across the document(s):\n{combined_notes}\n\nAnswer:"

    answer = llm_engine.generate(prompt, system=BROAD_REDUCE_SYSTEM)
    sources = [{"doc": name, "page": "whole document", "type": "summary", "snippet": ""} for name in doc_names]
    memory_manager.save_turn(session_id, question, answer, sources)

    return {"answer": answer, "sources": sources}


def answer_broad_question_stream(question: str, doc_ids: list[str], session_id: str):
    relevant_notes, doc_names = [], []
    for event in _gather_relevant_notes(question, doc_ids):
        if event["type"] == "progress":
            yield event
        else:
            relevant_notes, doc_names = event["notes"], event["doc_names"]

    combined_notes = "\n".join(f"- {n}" for n in relevant_notes) or "No relevant information found."
    prompt = f"Question: {question}\n\nNotes gathered from across the document(s):\n{combined_notes}\n\nAnswer:"

    full_answer = []
    for piece in llm_engine.generate_stream(prompt, system=BROAD_REDUCE_SYSTEM):
        full_answer.append(piece)
        yield {"type": "token", "content": piece}

    answer = "".join(full_answer)
    sources = [{"doc": name, "page": "whole document", "type": "summary", "snippet": ""} for name in doc_names]
    memory_manager.save_turn(session_id, question, answer, sources)

    yield {"type": "done", "sources": sources}