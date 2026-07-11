"""
One Chroma collection holds chunks from every uploaded document, each tagged
with a doc_id in its metadata. This (rather than one collection per document)
is what makes multi-document search and comparison possible: a single query
can filter to any subset of doc_ids via Chroma's `where` clause.
"""

import uuid
import chromadb
from sentence_transformers import SentenceTransformer

from config import Config

_client = chromadb.PersistentClient(path=Config.CHROMA_DIR)
_collection = _client.get_or_create_collection(name="documents")

_embedder = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        # Downloaded once from HuggingFace and cached locally after that.
        _embedder = SentenceTransformer(Config.EMBEDDING_MODEL)
    return _embedder


def embed_texts(texts: list[str]):
    return _get_embedder().encode(texts, show_progress_bar=False).tolist()


def add_chunks(doc_id: str, filename: str, chunks: list[dict]):
    """chunks: [{content, page, type}, ...] from core.chunker.chunk_document"""
    if not chunks:
        return
    texts = [c["content"] for c in chunks]
    embeddings = embed_texts(texts)
    ids = [f"{doc_id}_{i}_{uuid.uuid4().hex[:8]}" for i in range(len(chunks))]
    metadatas = [
        {"doc_id": doc_id, "filename": filename, "page": c["page"], "type": c["type"]}
        for c in chunks
    ]
    _collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)


def query(question: str, doc_ids: list[str], top_k: int = None):
    """
    Semantic search restricted to the given doc_ids.
    Returns a flat list of {content, filename, page, type, distance}.
    """
    top_k = top_k or Config.TOP_K
    if not doc_ids:
        return []

    where_filter = {"doc_id": {"$in": doc_ids}} if len(doc_ids) > 1 else {"doc_id": doc_ids[0]}
    query_embedding = embed_texts([question])[0]

    results = _collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter,
    )

    hits = []
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]
    for content, meta, dist in zip(docs, metas, dists):
        hits.append({
            "content": content,
            "filename": meta.get("filename"),
            "page": meta.get("page"),
            "type": meta.get("type"),
            "distance": dist,
        })
    return hits


def query_per_document(question: str, doc_ids: list[str], top_k: int = None):
    """Same as query(), but keeps results grouped per doc_id - used for comparisons."""
    return {doc_id: query(question, [doc_id], top_k) for doc_id in doc_ids}


def get_all_chunks(doc_id: str) -> list[str]:
    """Used by the summarizer, which needs every chunk of one document, not just top-k."""
    results = _collection.get(where={"doc_id": doc_id})
    return results.get("documents", [])


def delete_document_vectors(doc_id: str):
    _collection.delete(where={"doc_id": doc_id})
