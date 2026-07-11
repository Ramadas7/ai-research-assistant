from config import Config
from database.models import get_messages, add_message


def get_recent_history(session_id: str) -> str:
    """
    Formats the last N turns of a session as plain text so it can be dropped
    straight into the prompt. This is what lets a follow-up question like
    "what did I just ask you?" work, without re-sending the whole PDF each time.
    """
    messages = get_messages(session_id)
    recent = messages[-(Config.MAX_HISTORY_TURNS * 2):]  # user+assistant pairs
    if not recent:
        return ""

    lines = []
    for m in recent:
        speaker = "User" if m["role"] == "user" else "Assistant"
        lines.append(f"{speaker}: {m['content']}")
    return "\n".join(lines)


def save_turn(session_id: str, question: str, answer: str, sources: list):
    add_message(session_id, "user", question)
    add_message(session_id, "assistant", answer, sources)
