import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

# Switch to vLLM later:
# OPENAI_BASE_URL = "http://localhost:8000/v1"
# OPENAI_API_KEY = "not-needed"

MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
