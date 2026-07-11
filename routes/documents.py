import os
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from core.ingest import ingest_pdf
from core.vector_store import delete_document_vectors
from database.models import list_documents, delete_document, get_document

documents_bp = Blueprint("documents", __name__, url_prefix="/api/documents")


def _allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]


@documents_bp.route("", methods=["GET"])
def get_documents():
    return jsonify(list_documents())


@documents_bp.route("/upload", methods=["POST"])
def upload_document():
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    if not _allowed(file.filename):
        return jsonify({"error": "Only PDF files are supported"}), 400

    filename = secure_filename(file.filename)
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)

    # Avoid clobbering an existing file with the same name
    base, ext = os.path.splitext(filepath)
    counter = 1
    while os.path.exists(filepath):
        filepath = f"{base}_{counter}{ext}"
        counter += 1
    filename = os.path.basename(filepath)

    file.save(filepath)

    try:
        doc = ingest_pdf(filepath, filename)
    except Exception as e:
        os.remove(filepath)
        return jsonify({"error": f"Failed to process PDF: {e}"}), 500

    return jsonify(doc), 201


@documents_bp.route("/<doc_id>", methods=["DELETE"])
def remove_document(doc_id):
    doc = get_document(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404

    delete_document_vectors(doc_id)
    delete_document(doc_id)
    if os.path.exists(doc["filepath"]):
        os.remove(doc["filepath"])

    return jsonify({"status": "deleted"})
