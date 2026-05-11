import json
import os
import shutil
import subprocess
from typing import AsyncGenerator, Optional

try:
    import httpx
except ImportError:  # pragma: no cover - optional dependency fallback
    httpx = None

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
PREFERRED_MODELS = ["gpt-oss:latest", "gemma4:latest", "qwen3.6:latest"]
EMBEDDING_MODEL = "embeddinggemma:latest"


def _locate_ollama() -> Optional[str]:
    if found := shutil.which("ollama"):
        return found

    candidates = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe"),
        r"C:\Program Files\Ollama\ollama.exe",
        "/usr/local/bin/ollama",
        os.path.expanduser("~/.local/bin/ollama"),
        "/opt/homebrew/bin/ollama",
    ]
    return next((path for path in candidates if path and os.path.exists(path)), None)


def get_installed_models(timeout: float = 3.0) -> list[str]:
    ollama = _locate_ollama()
    if not ollama:
        return []
    try:
        result = subprocess.run([ollama, "list"], capture_output=True, text=True, timeout=timeout, check=True)
    except (OSError, subprocess.SubprocessError):
        return []

    models: list[str] = []
    for line in result.stdout.splitlines()[1:]:
        parts = line.split()
        if parts:
            models.append(parts[0])
    return models


def choose_best_model(preferred: list[str] | None = None) -> Optional[str]:
    installed = get_installed_models()
    if not installed:
        return None
    for model in preferred or PREFERRED_MODELS:
        if model in installed:
            return model
    return installed[0]


def choose_best_embedding_model() -> Optional[str]:
    installed = get_installed_models()
    return EMBEDDING_MODEL if EMBEDDING_MODEL in installed else None


async def generate_response(prompt: str, system: str) -> tuple[str, Optional[str]]:
    model = choose_best_model()
    if not model or httpx is None:
        return (
            "Local AI is currently unavailable. The system is running in deterministic fallback mode.",
            None,
        )

    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "options": {
            "temperature": 0.2,
            "num_predict": 2048,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=160.0) as client:
            response = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"], model
    except (httpx.HTTPError, KeyError, json.JSONDecodeError):
        return (
            "Ollama could not be reached. Returning deterministic results only.",
            None,
        )


async def generate_response_stream(prompt: str, system: str) -> AsyncGenerator[str, None]:
    model = choose_best_model()
    if not model or httpx is None:
        yield "Local AI is currently unavailable. No Ollama model detected."
        return

    payload = {
        "model": model,
        "stream": True,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "options": {
            "temperature": 0.2,
            "num_predict": 2048,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=160.0) as client:
            async with client.stream("POST", f"{OLLAMA_BASE_URL}/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if data.get("done"):
                        break
                    content = data.get("message", {}).get("content")
                    if content:
                        yield content
    except (httpx.HTTPError, KeyError, json.JSONDecodeError):
        yield "Ollama stream failed. Falling back to deterministic summary."
