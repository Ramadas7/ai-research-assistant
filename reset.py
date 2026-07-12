"""
Wipes all local app data back to a clean slate: vector store, chat history,
and uploaded PDFs. Run this with the Flask app stopped - Windows locks files
that are still open, so deleting while it's running can fail partway through.

Usage:
    python reset_data.py
"""
import os
import shutil

from config import Config


def _clear_dir(path):
    if not os.path.isdir(path):
        return
    for name in os.listdir(path):
        if name == ".gitkeep":
            continue
        full = os.path.join(path, name)
        if os.path.isdir(full):
            shutil.rmtree(full)
        else:
            os.remove(full)


def main():
    _clear_dir(Config.CHROMA_DIR)
    _clear_dir(Config.UPLOAD_FOLDER)
    if os.path.exists(Config.SQLITE_DB):
        os.remove(Config.SQLITE_DB)
    print("Cleared: vector store, uploaded files, and chat history.")
    print("Restart the app - it recreates everything fresh.")


if __name__ == "__main__":
    main()