"""
Wraps the Ollama vision model (llama3.2-vision) to turn images/graphs/diagrams
found inside a PDF into plain-text descriptions. Those descriptions get embedded
and indexed exactly like any other chunk, which is what lets the RAG pipeline
"understand" a figure without needing a separate multimodal retrieval path.

Text-only Llama 3.2 (via Ollama) CANNOT see images - that's a different model
(llama3.2-vision) with its own weights. If it isn't installed, we fail soft:
log once, skip image understanding, and let text/table understanding continue.
"""

import base64
import ollama
from config import Config

_vision_available = None  # cached after first check, None = not checked yet
_vision_broken_at_runtime = False  # set True the first time an actual call fails


def _extract_model_names(list_response) -> list[str]:
    """
    ollama-python's Client.list() return shape has shifted across versions
    (dict-like vs. pydantic object). Handle both instead of assuming one.
    """
    models = getattr(list_response, "models", None)
    if models is None and hasattr(list_response, "get"):
        models = list_response.get("models", [])
    models = models or []

    names = []
    for m in models:
        name = getattr(m, "model", None) or getattr(m, "name", None)
        if name is None and hasattr(m, "get"):
            name = m.get("model") or m.get("name")
        if name:
            names.append(name)
    return names


def vision_model_ready():
    """Check once per process whether the vision model is actually pulled."""
    global _vision_available
    if _vision_available is not None:
        return _vision_available

    if not Config.ENABLE_VISION:
        _vision_available = False
        return False

    try:
        client = ollama.Client(host=Config.OLLAMA_HOST)
        names = _extract_model_names(client.list())
        _vision_available = any(Config.OLLAMA_VISION_MODEL in n for n in names)
    except Exception:
        _vision_available = False

    if not _vision_available:
        print(
            f"[vision_engine] '{Config.OLLAMA_VISION_MODEL}' not found in Ollama. "
            f"Run `ollama pull {Config.OLLAMA_VISION_MODEL}` to enable image/graph "
            f"understanding. Continuing with text + tables only."
        )
    return _vision_available


def describe_image(image_bytes: bytes, context_hint: str = "") -> str | None:
    """
    Send raw image bytes to the vision model and get back a plain-English
    description - specifically prompted to also read any equations, axis
    labels, or numbers so the description is retrievable by semantic search.
    Returns None if the vision model isn't available (caller should skip).
    """
    global _vision_broken_at_runtime

    if not vision_model_ready() or _vision_broken_at_runtime:
        return None

    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    prompt = (
        "Describe this figure from a research paper in 3-5 sentences. "
        "If it is a chart or graph, state what is on each axis and the overall "
        "trend or result shown. If it contains a mathematical formula or equation, "
        "transcribe it as plain text as accurately as you can. "
        + (f"Context: this appears near the text '{context_hint}'." if context_hint else "")
    )

    try:
        client = ollama.Client(host=Config.OLLAMA_HOST)
        response = client.chat(
            model=Config.OLLAMA_VISION_MODEL,
            messages=[{"role": "user", "content": prompt, "images": [b64_image]}],
        )
        return response["message"]["content"].strip()
    except Exception as e:
        # The model being *listed* doesn't guarantee it can actually run (e.g. the
        # Ollama runtime is too old for this model's architecture). Don't retry
        # this dozens of times across one document's images - fail once, log once,
        # and let every remaining image skip instantly for the rest of this run.
        _vision_broken_at_runtime = True
        print(
            f"[vision_engine] vision model call failed and will be disabled for the "
            f"rest of this run: {e}\n"
            f"[vision_engine] This usually means your Ollama installation is out of "
            f"date for '{Config.OLLAMA_VISION_MODEL}'. Update Ollama from "
            f"https://ollama.com/download and try again."
        )
        return None