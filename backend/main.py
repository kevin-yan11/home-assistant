from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager

from agents import ButlerAgent
from core import state_manager, schedule_manager, ha_client


butler: ButlerAgent | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global butler
    # Sync devices from Home Assistant if enabled
    if ha_client.enabled:
        count = state_manager.sync_from_ha(ha_client)
        print(f"[HA] Synced {count} devices from Home Assistant")
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


@app.get("/schedules")
async def get_schedules():
    """Get all scheduled tasks."""
    tasks = schedule_manager.get_all_tasks()
    return [
        {
            "id": t.id,
            "type": t.task_type.value,
            "trigger_time": t.trigger_time.isoformat(),
            "repeat": t.repeat.value,
            "description": t.description,
            "message": t.message,
            "status": t.status.value,
        }
        for t in sorted(tasks, key=lambda x: x.trigger_time)
    ]


@app.delete("/schedules/{task_id}")
async def delete_schedule(task_id: str):
    """Delete a scheduled task."""
    if schedule_manager.delete_task(task_id):
        return {"status": "ok", "message": f"Task {task_id} deleted"}
    raise HTTPException(404, f"Task {task_id} not found")


@app.post("/reset")
async def reset():
    global butler
    butler = ButlerAgent()
    if ha_client.enabled:
        state_manager.sync_from_ha(ha_client)
    else:
        state_manager._init_mock_devices()
    return {"status": "ok"}


@app.get("/ha/status")
async def ha_status():
    """Check Home Assistant connection status."""
    if not ha_client.enabled:
        return {"enabled": False, "message": "Home Assistant integration is disabled"}
    result = ha_client.check_connection()
    return {"enabled": True, **result}


@app.post("/ha/sync")
async def ha_sync():
    """Manually sync devices from Home Assistant."""
    if not ha_client.enabled:
        raise HTTPException(400, "Home Assistant integration is disabled")
    count = state_manager.sync_from_ha(ha_client)
    return {"status": "ok", "devices_synced": count}


@app.get("/ha/entities")
async def ha_entities(domain: str = None):
    """List entities from Home Assistant."""
    if not ha_client.enabled:
        raise HTTPException(400, "Home Assistant integration is disabled")
    if domain:
        return ha_client.get_entities_by_domain(domain)
    return ha_client.get_states()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
