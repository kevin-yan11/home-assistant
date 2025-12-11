from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager

from agents import ButlerAgent
from core import state_manager


butler: ButlerAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global butler
    butler = ButlerAgent()
    yield
    butler = None


app = FastAPI(title="Home Assistant API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    devices: dict


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(400, "Empty message")
    try:
        response = await butler.chat(req.message)
        return ChatResponse(
            response=response,
            devices=state_manager.get_all()
        )
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/devices")
async def get_devices():
    return state_manager.get_all()


@app.post("/reset")
async def reset():
    global butler
    butler = ButlerAgent()
    state_manager._init_mock_devices()
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
