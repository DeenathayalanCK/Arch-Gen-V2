import requests
from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL
import os
from pathlib import Path


OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://host.docker.internal:11434"  # Docker-safe default
)

MODEL_NAME = os.getenv("OLLAMA_MODEL", "mistral")


class LLMClient:
    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = OLLAMA_MODEL,
    ):
        self.base_url = base_url
        self.model = model

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "temperature": 0.0,
            "num_predict": 200,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "stream": False,
        }

        response = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=300,
        )

        response.raise_for_status()

        data = response.json()
        return data["message"]["content"]
    
def load_prompt(filename: str) -> str:
    """
    Load LLM prompt files safely in Docker and local environments.
    """
    prompt_dir = Path(__file__).resolve().parent / "prompts"
    return (prompt_dir / filename).read_text(encoding="utf-8")