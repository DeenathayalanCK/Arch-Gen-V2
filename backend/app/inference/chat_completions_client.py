import requests
import re

class ChatCompletionsClient:
    def __init__(self, base_url: str, model: str, temperature: float = 0.2):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature

    def generate(self, messages):
        url = f"{self.base_url}/chat/completions"

        response = requests.post(
            url,
            json={
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
            },
            timeout=300,  
        )
        response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]

        #  STRIP MARKDOWN FENCES 
        content = re.sub(r"^```(?:json)?\s*", "", content.strip())
        content = re.sub(r"\s*```$", "", content.strip())

        return content