import os
from dotenv import load_dotenv
import agentscope

load_dotenv() 

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

# Switch to vLLM later:
# OPENAI_BASE_URL = "http://localhost:8000/v1"
# OPENAI_API_KEY = "not-needed"

MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

# Home Assistant Configuration
HA_URL = os.getenv("HA_URL", "http://localhost:8123")
HA_TOKEN = os.getenv("HA_TOKEN", "")
HA_ENABLED = os.getenv("HA_ENABLED", "false").lower() == "true"

# AgentScope Configuration
AGENTSCOPE_STUDIO_URL = os.getenv("AGENTSCOPE_STUDIO_URL", "")  # Optional: e.g., "http://localhost:3001"

# Initialize AgentScope
_init_kwargs = {
    "project": "home-assistant",
    "name": "butler-agent",
}
if AGENTSCOPE_STUDIO_URL:
    _init_kwargs["studio_url"] = AGENTSCOPE_STUDIO_URL

agentscope.init(**_init_kwargs)
