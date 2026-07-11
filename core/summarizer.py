from core import vector_store, llm_engine
from database.models import get_document

MAP_PROMPT_SYSTEM = "Summarize the following excerpt from a research document in 2-3 sentences, keeping key facts, numbers, and findings."
REDUCE_PROMPT_SYSTEM = (
    "You are combining partial summaries of a research document into one cohesive "
    "summary. Structure it with these headings: Overview, Key Findings, Methodology "
    "(if applicable), Notable Data/Tables/Figures. Be concise."
)

# How many chunks to bundle into one map-step call, to keep prompts from getting huge.
BATCH_SIZE = 6


def _batch(iterable, size):
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]


def summarize_document(doc_id: str) -> dict:
    doc = get_document(doc_id)
    if not doc:
        return {"summary": "Document not found.", "sources": []}

    all_chunks = vector_store.get_all_chunks(doc_id)
    if not all_chunks:
        return {"summary": "No content was indexed for this document.", "sources": []}

    # Map step: summarize each batch of chunks independently
    partial_summaries = []
    for batch in _batch(all_chunks, BATCH_SIZE):
        excerpt = "\n\n".join(batch)
        partial = llm_engine.generate(excerpt, system=MAP_PROMPT_SYSTEM)
        partial_summaries.append(partial)

    # Reduce step: combine partial summaries into one structured summary
    combined = "\n\n".join(partial_summaries)
    final_summary = llm_engine.generate(combined, system=REDUCE_PROMPT_SYSTEM)

    return {
        "summary": final_summary,
        "doc": doc["filename"],
        "num_sections_summarized": len(partial_summaries),
    }
