import os
from flask import Flask, render_template  # type: ignore[import]

from config import Config
from database.db import init_db
from routes.documents import documents_bp
from routes.chat import chat_bp
from routes.history import history_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(Config.CHROMA_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(Config.SQLITE_DB), exist_ok=True)
    init_db()

    app.register_blueprint(documents_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(history_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/about")
    def about():
        return render_template("about.html")

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(debug=True, port=port)
