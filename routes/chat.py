from flask import Blueprint, request, jsonify

from core.rag_pipeline import answer_question
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

    result = answer_question(question, doc_ids, session_id)
    # Auto-title new sessions from the first question
    session = get_session(session_id)
    if session and session["title"] == "New Chat":
        touch_session(session_id, title=question[:40])
    else:
        touch_session(session_id)

    result["session_id"] = session_id
    return jsonify(result)


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
