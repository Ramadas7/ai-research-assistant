from core import vector_store, llm_engine
from database.models import get_document

SYSTEM_PROMPT = (
    "You are a research assistant comparing multiple documents. Answer using ONLY "
    "the provided context.\n\n"
    "Structure your answer in Markdown with these headings:\n"
    "## What each document says\n"
    "## Where they agree\n"
    "## Where they differ\n\n"
    "Use **bold** for key terms and bullet points where helpful. Synthesize in your "
    "own words rather than quoting verbatim, and don't include bracketed filename "
    "citations - sources are shown separately in the interface. If a document doesn't "
    "cover the topic, say so under its section."
)


def compare_documents(question: str, doc_ids: list[str]) -> dict:
    per_doc_hits = vector_store.query_per_document(question, doc_ids)

    context_blocks = []
    seen_sources = set()
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
            key = (filename, h["page"], h["type"])
            if key in seen_sources:
                continue
            seen_sources.add(key)
            all_sources.append({
                "doc": filename, "page": h["page"], "type": h["type"],
                "snippet": h["content"][:180],
            })

    context = "\n\n===\n\n".join(context_blocks)
    prompt = f"Documents:\n{context}\n\nCompare the documents on: {question}\n\nAnswer:"
    answer = llm_engine.generate(prompt, system=SYSTEM_PROMPT)

    return {"answer": answer, "sources": all_sources}