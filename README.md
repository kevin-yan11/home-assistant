# Home Assistant Demo

A demo project showcasing AI agent architecture for smart home control using AgentScope framework.

## Project Structure

```
home-assistant/
├── backend/
│   ├── agents/          # Agent definitions
│   ├── core/            # State management
│   ├── tools/           # Device control tools
│   └── main.py          # FastAPI server
└── frontend/            # Next.js UI
```

## Quick Start

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set API key
export OPENAI_API_KEY="your-key-here"

# Run server
python main.py
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

Open http://localhost:3000 in your browser.

## Architecture

```
User Input
    │
    ▼
┌───────────────────┐
│   ReActAgent      │  ← AgentScope framework
│   (Supervisor)    │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│   Tool Functions  │  ← control_light, control_ac, etc.
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│   StateManager    │  ← In-memory device state
└───────────────────┘
```

## Switching to vLLM

When vLLM is deployed locally, update `backend/config.py`:

```python
OPENAI_BASE_URL = "http://localhost:8000/v1"
OPENAI_API_KEY = "not-needed"
MODEL_NAME = "qwen2.5-72b"
```

## Example Commands

- "Turn on the bedroom light"
- "Set AC to 24 degrees"
- "Dim the lights to 30%"
- "Play some jazz music"
- "Turn off all lights"
