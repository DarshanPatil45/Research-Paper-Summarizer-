"""
Ollama API client – thin wrapper around the REST API.

Provides generate() for single-turn completions and a health check.
"""

import json
import requests
from config import OLLAMA_BASE_URL, OLLAMA_MODEL


class OllamaError(Exception):
    """Raised when Ollama is unreachable or returns an error."""


def _check_connectivity():
    """Raise OllamaError with a helpful message if Ollama is not running."""
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        resp.raise_for_status()
    except requests.ConnectionError:
        raise OllamaError(
            "Cannot connect to Ollama. Make sure it is running:\n"
            "  ollama serve\n"
            f"Expected URL: {OLLAMA_BASE_URL}"
        )
    except requests.Timeout:
        raise OllamaError(
            "Ollama did not respond in time. Is it running?"
        )


def _check_model(model: str):
    """Raise OllamaError if the requested model is not available locally."""
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        available = [m["name"] for m in resp.json().get("models", [])]
        # Ollama tags can be "llama3.2:3b" or "llama3.2:3b-instruct-...",
        # so we check if any available name starts with the requested model.
        match = any(
            name == model or name.startswith(model + "-") or name.startswith(model + ":")
            for name in available
        )
        # Also check the base name without tag
        if not match:
            match = any(model.split(":")[0] in name for name in available)
        if not match:
            names_str = "\n  ".join(available) if available else "(none)"
            raise OllamaError(
                f"Model '{model}' not found. Available models:\n  {names_str}\n\n"
                f"Pull it with:  ollama pull {model}"
            )
    except OllamaError:
        raise
    except Exception as e:
        raise OllamaError(f"Error checking model availability: {e}")


def health_check(model: str = OLLAMA_MODEL):
    """Verify Ollama is running and the model is available."""
    _check_connectivity()
    _check_model(model)


def generate(prompt: str, *, model: str = OLLAMA_MODEL,
             system: str = "", temperature: float = 0.3,
             max_tokens: int = 2048) -> str:
    """
    Send a single-turn prompt to Ollama and return the full response text.

    Uses the /api/generate endpoint with streaming disabled for simplicity.
    """
    _check_connectivity()

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    if system:
        payload["system"] = system

    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=300,  # large models can be slow
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "").strip()
    except requests.ConnectionError:
        raise OllamaError("Lost connection to Ollama during generation.")
    except requests.Timeout:
        raise OllamaError("Ollama generation timed out (300 s). Try a shorter input.")
    except json.JSONDecodeError:
        raise OllamaError("Ollama returned invalid JSON.")
    except requests.HTTPError as e:
        raise OllamaError(f"Ollama HTTP error: {e}")
