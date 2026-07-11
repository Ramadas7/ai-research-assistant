import ollama
from config import Config


def generate(prompt: str, system: str = None) -> str:
    """Single call to the local Llama 3.2 model through Ollama."""
    client = ollama.Client(host=Config.OLLAMA_HOST)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat(model=Config.OLLAMA_TEXT_MODEL, messages=messages)
        return response["message"]["content"].strip()
    except Exception as e:
        return (
            "⚠️ Couldn't reach Ollama. Make sure it's running (`ollama serve`) "
            f"and that the model is pulled (`ollama pull {Config.OLLAMA_TEXT_MODEL}`).\n\n"
            f"Details: {e}"
        )
