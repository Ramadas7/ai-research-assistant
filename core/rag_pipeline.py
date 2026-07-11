from core import vector_store, llm_engine, memory_manager

SYSTEM_PROMPT = (
    "You are a research assistant. Answer ONLY using the provided context. "
    "If the context doesn't contain the answer, say so honestly instead of guessing. "
    "When the context includes table data or figure descriptions, you may reference them. "
    "Keep answers clear and directly grounded in the context."
)


def _build_context(hits: list[dict]) -> str:
    if not hits:
        return "No relevant context was found in the document(s)."
    blocks = []
    for h in hits:
        tag = f"[{h['filename']} - page {h['page']} - {h['type']}]"
        blocks.append(f"{tag}\n{h['content']}")
    return "\n\n---\n\n".join(blocks)


def _build_sources(hits: list[dict]) -> list[dict]:
    sources = []
    for h in hits:
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
