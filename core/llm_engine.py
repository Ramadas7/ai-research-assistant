import ollama
from config import Config


def generate(prompt: str, system: str = None) -> str:
    """Single call to the local Llama 3.2 model through Ollama. Returns the full answer at once."""
    client = ollama.Client(host=Config.OLLAMA_HOST)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat(
            model=Config.OLLAMA_TEXT_MODEL,
            messages=messages,
            options={"num_ctx": Config.OLLAMA_NUM_CTX},
        )
        return response["message"]["content"].strip()
    except Exception as e:
        return (
            "⚠️ Couldn't reach Ollama. Make sure it's running (`ollama serve`) "
            f"and that the model is pulled (`ollama pull {Config.OLLAMA_TEXT_MODEL}`).\n\n"
            f"Details: {e}"
        )


def generate_stream(prompt: str, system: str = None):
    """
    Same call, but yields the answer piece by piece as it's generated instead of
    waiting for the whole thing.
    """
    client = ollama.Client(host=Config.OLLAMA_HOST)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        stream = client.chat(
            model=Config.OLLAMA_TEXT_MODEL,
            messages=messages,
            stream=True,
            options={"num_ctx": Config.OLLAMA_NUM_CTX},
        )
        for chunk in stream:
            piece = chunk["message"]["content"]
            if piece:
                yield piece
    except Exception as e:
        yield (
            "⚠️ Couldn't reach Ollama. Make sure it's running (`ollama serve`) "
            f"and that the model is pulled (`ollama pull {Config.OLLAMA_TEXT_MODEL}`).\n\n"
            f"Details: {e}"
        )