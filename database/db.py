import sqlite3
import os
from config import Config

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    size_mb REAL,
    num_pages INTEGER,
    num_chunks INTEGER,
    has_tables INTEGER DEFAULT 0,
    has_images INTEGER DEFAULT 0,
    uploaded_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT DEFAULT 'New Chat',
    doc_ids TEXT NOT NULL,          -- JSON list of document ids in scope for this session
    mode TEXT DEFAULT 'chat',       -- 'chat' | 'compare' | 'summarize'
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,             -- 'user' | 'assistant'
    content TEXT NOT NULL,
    sources TEXT,                   -- JSON list of {doc, page, type, snippet}
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sessions (id)
);
"""


def get_connection():
    os.makedirs(os.path.dirname(Config.SQLITE_DB), exist_ok=True)
    conn = sqlite3.connect(Config.SQLITE_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
