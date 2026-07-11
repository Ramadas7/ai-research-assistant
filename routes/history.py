from flask import Blueprint, jsonify
from database.models import list_sessions, get_messages, delete_session, get_session

history_bp = Blueprint("history", __name__, url_prefix="/api/sessions")


@history_bp.route("", methods=["GET"])
def get_sessions():
    return jsonify(list_sessions())


@history_bp.route("/<session_id>", methods=["GET"])
def get_session_detail(session_id):
    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    session["messages"] = get_messages(session_id)
    return jsonify(session)


@history_bp.route("/<session_id>", methods=["DELETE"])
def remove_session(session_id):
    delete_session(session_id)
    return jsonify({"status": "deleted"})
