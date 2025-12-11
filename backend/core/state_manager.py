from dataclasses import dataclass, field
from typing import Dict, Any
from datetime import datetime


@dataclass
class DeviceState:
    device_id: str
    device_type: str
    room: str
    status: str
    properties: Dict[str, Any] = field(default_factory=dict)


class StateManager:
    """In-memory device state storage for demo purposes."""

    def __init__(self):
        self._states: Dict[str, DeviceState] = {}
        self._logs: list = []
        self._init_mock_devices()

    def _init_mock_devices(self):
        devices = [
            ("light_bedroom", "light", "bedroom", "off", {"brightness": 0}),
            ("light_living_room", "light", "living_room", "on", {"brightness": 80}),
            ("ac_bedroom", "ac", "bedroom", "off", {"temperature": 26, "mode": "cool"}),
            ("ac_living_room", "ac", "living_room", "on", {"temperature": 24, "mode": "cool"}),
            ("speaker_living_room", "speaker", "living_room", "off", {"volume": 50, "playing": None}),
        ]
        for did, dtype, room, status, props in devices:
            self._states[did] = DeviceState(did, dtype, room, status, props)

    def get(self, device_id: str) -> DeviceState | None:
        return self._states.get(device_id)

    def update(self, device_id: str, **kwargs) -> bool:
        if device_id not in self._states:
            return False
        state = self._states[device_id]
        for k, v in kwargs.items():
            if k == "properties":
                state.properties.update(v)
            elif hasattr(state, k):
                setattr(state, k, v)
        self._logs.append({
            "time": datetime.now().isoformat(),
            "device": device_id,
            "changes": kwargs
        })
        return True

    def get_context(self) -> str:
        """Generate context string for agent prompt injection."""
        lines = ["[Current Device Status]"]
        room_map = {"bedroom": "Bedroom", "living_room": "Living Room", "kitchen": "Kitchen"}
        for s in self._states.values():
            room_name = room_map.get(s.room, s.room)
            icon = "ON" if s.status == "on" else "OFF"
            props = ", ".join(f"{k}={v}" for k, v in s.properties.items() if v is not None)
            lines.append(f"- {room_name} {s.device_type}: {icon}" + (f" ({props})" if props else ""))
        return "\n".join(lines)

    def get_all(self) -> Dict[str, dict]:
        return {
            did: {
                "room": s.room,
                "type": s.device_type,
                "status": s.status,
                "properties": s.properties
            }
            for did, s in self._states.items()
        }

    def get_logs(self, limit: int = 10) -> list:
        return self._logs[-limit:]


state_manager = StateManager()
