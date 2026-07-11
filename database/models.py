import json
import uuid
from database.db import get_connection


# ---------- Documents ----------

def create_document(filename, filepath, size_mb, num_pages, num_chunks,
                     has_tables=False, has_images=False):
    doc_id = str(uuid.uuid4())
    conn = get_connection()
    conn.execute(
        """INSERT INTO documents
           (id, filename, filepath, size_mb, num_pages, num_chunks, has_tables, has_images)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (doc_id, filename, filepath, size_mb, num_pages, num_chunks,
         int(has_tables), int(has_images)),
    )
    conn.commit()
    conn.close()
    return doc_id


def list_documents():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM documents ORDER BY uploaded_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_document(doc_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_document(doc_id):
    conn = get_connection()
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()


# ---------- Sessions ----------

def create_session(doc_ids, mode="chat", title="New Chat"):
    session_id = str(uuid.uuid4())
    conn = get_connection()
    conn.execute(
        "INSERT INTO sessions (id, title, doc_ids, mode) VALUES (?, ?, ?, ?)",
        (session_id, title, json.dumps(doc_ids), mode),
    )
    conn.commit()
    conn.close()
    return session_id


def list_sessions():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM sessions ORDER BY updated_at DESC").fetchall()
    conn.close()
    sessions = []
    for r in rows:
        d = dict(r)
        d["doc_ids"] = json.loads(d["doc_ids"])
        sessions.append(d)
    return sessions


def get_session(session_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["doc_ids"] = json.loads(d["doc_ids"])
    return d


def touch_session(session_id, title=None):
    conn = get_connection()
    if title:
        conn.execute(
            "UPDATE sessions SET updated_at = datetime('now'), title = ? WHERE id = ?",
            (title, session_id),
        )
    else:
        conn.execute(
            "UPDATE sessions SET updated_at = datetime('now') WHERE id = ?",
            (session_id,),
        )
    conn.commit()
    conn.close()


def delete_session(session_id):
    conn = get_connection()
    conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()


# ---------- Messages ----------

def add_message(session_id, role, content, sources=None):
    conn = get_connection()
    conn.execute(
        "INSERT INTO messages (session_id, role, content, sources) VALUES (?, ?, ?, ?)",
        (session_id, role, content, json.dumps(sources or [])),
    )
    conn.commit()
    conn.close()


def get_messages(session_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,)
    ).fetchall()
    conn.close()
    messages = []
    for r in rows:
        d = dict(r)
        d["sources"] = json.loads(d["sources"]) if d["sources"] else []
        messages.append(d)
    return messages
