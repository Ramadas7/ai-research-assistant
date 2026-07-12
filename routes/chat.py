import json
from flask import Blueprint, request, jsonify, Response, stream_with_context

from core.rag_pipeline import (
    answer_question, answer_question_stream,
    answer_broad_question, answer_broad_question_stream, is_broad_question,
)
from core.comparator import compare_documents
from core.summarizer import summarize_document
from database.models import create_session, touch_session, get_session

chat_bp = Blueprint("chat", __name__, url_prefix="/api")


@chat_bp.route("/session/new", methods=["POST"])
def new_session():
    data = request.get_json(force=True)
    doc_ids = data.get("doc_ids", [])
    mode = data.get("mode", "chat")
    title = data.get("title", "New Chat")
    session_id = create_session(doc_ids, mode=mode, title=title)
    return jsonify({"session_id": session_id})


@chat_bp.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    question = data.get("question", "").strip()
    doc_ids = data.get("doc_ids", [])
    session_id = data.get("session_id")

    if not question:
        return jsonify({"error": "question is required"}), 400
    if not doc_ids:
        return jsonify({"error": "at least one doc_id is required"}), 400
    if not session_id:
        session_id = create_session(doc_ids, mode="chat", title=question[:40])

    result = (
        answer_broad_question(question, doc_ids, session_id)
        if is_broad_question(question)
        else answer_question(question, doc_ids, session_id)
    )
    session = get_session(session_id)
    if session and session["title"] == "New Chat":
        touch_session(session_id, title=question[:40])
    else:
        touch_session(session_id)

    result["session_id"] = session_id
    return jsonify(result)


@chat_bp.route("/chat/stream", methods=["POST"])
def chat_stream():
    """
    Same as /api/chat, but streams the answer as newline-delimited JSON events
    instead of waiting for the full response:
        {"type": "session", "session_id": "..."}
        {"type": "token", "content": "..."}   x many
        {"type": "done", "sources": [...]}
    """
    data = request.get_json(force=True)
    question = data.get("question", "").strip()
    doc_ids = data.get("doc_ids", [])
    session_id = data.get("session_id")

    if not question:
        return jsonify({"error": "question is required"}), 400
    if not doc_ids:
        return jsonify({"error": "at least one doc_id is required"}), 400
    if not session_id:
        session_id = create_session(doc_ids, mode="chat", title=question[:40])

    def generate():
        yield json.dumps({"type": "session", "session_id": session_id}) + "\n"
        stream_fn = answer_broad_question_stream if is_broad_question(question) else answer_question_stream
        for event in stream_fn(question, doc_ids, session_id):
            yield json.dumps(event) + "\n"

        session = get_session(session_id)
        if session and session["title"] == "New Chat":
            touch_session(session_id, title=question[:40])
        else:
            touch_session(session_id)

    return Response(stream_with_context(generate()), mimetype="application/x-ndjson")


@chat_bp.route("/compare", methods=["POST"])
def compare():
    data = request.get_json(force=True)
    question = data.get("question", "").strip()
    doc_ids = data.get("doc_ids", [])
    session_id = data.get("session_id")

    if len(doc_ids) < 2:
        return jsonify({"error": "Select at least 2 documents to compare"}), 400
    if not session_id:
        session_id = create_session(doc_ids, mode="compare", title=f"Compare: {question[:30]}")

    result = compare_documents(question, doc_ids)
    touch_session(session_id)
    result["session_id"] = session_id
    return jsonify(result)


@chat_bp.route("/summarize", methods=["POST"])
def summarize():
    data = request.get_json(force=True)
    doc_id = data.get("doc_id")
    if not doc_id:
        return jsonify({"error": "doc_id is required"}), 400
    result = summarize_document(doc_id)
    return jsonify(result)