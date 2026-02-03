from dotenv import load_dotenv
load_dotenv()

import os
from app.pipeline.reasoner import run_architecture_reasoner
from app.inference.chat_completions_client import ChatCompletionsClient


client = ChatCompletionsClient(
    base_url=os.environ["REASONER_BASE_URL"],
    model=os.environ["REASONER_MODEL"],
)

prompt = """
A platform where citizens can give consent to share their health data
with approved researchers for studies.
"""

ir = run_architecture_reasoner(prompt, client)
print("✅ Reasoner produced valid Architecture IR")
import json
print(json.dumps(enriched.dict(), indent=2))

