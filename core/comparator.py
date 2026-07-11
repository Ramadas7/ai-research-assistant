from core import vector_store, llm_engine
from database.models import get_document

SYSTEM_PROMPT = (
    "You are a research assistant comparing multiple documents. Structure your "
    "answer as: 1) what each document individually says on the topic, 2) where they "
    "agree, 3) where they differ or contradict each other. Only use the provided "
    "context - if a document doesn't cover the topic, say so."
)


def compare_documents(question: str, doc_ids: list[str]) -> dict:
    per_doc_hits = vector_store.query_per_document(question, doc_ids)

    context_blocks = []
    all_sources = []
    for doc_id, hits in per_doc_hits.items():
        doc = get_document(doc_id)
        filename = doc["filename"] if doc else doc_id
        if not hits:
            context_blocks.append(f"[{filename}]\n(No relevant content found)")
            continue
        joined = "\n".join(f"(page {h['page']}) {h['content']}" for h in hits)
        context_blocks.append(f"[{filename}]\n{joined}")
        for h in hits:
            all_sources.append({
                "doc": filename, "page": h["page"], "type": h["type"],
                "snippet": h["content"][:180],
            })

    context = "\n\n===\n\n".join(context_blocks)
    prompt = f"Documents:\n{context}\n\nCompare the documents on: {question}\n\nAnswer:"
    answer = llm_engine.generate(prompt, system=SYSTEM_PROMPT)

    return {"answer": answer, "sources": all_sources}
