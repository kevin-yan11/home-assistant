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
    ha_entity_id: str = None  # Home Assistant entity ID mapping


class StateManager:
    """Device state storage with Home Assistant sync support."""

    def __init__(self):
        self._states: Dict[str, DeviceState] = {}
        self._logs: list = []
        self._ha_entity_map: Dict[str, str] = {}  # local_id -> ha_entity_id
        self._init_mock_devices()

    def _init_mock_devices(self):
        """Initialize mock devices (used when HA is disabled)."""
        devices = [
            ("light_bedroom", "light", "bedroom", "off", {"brightness": 0}),
            ("light_living_room", "light", "living_room", "on", {"brightness": 80}),
            ("ac_bedroom", "ac", "bedroom", "off", {"temperature": 26, "mode": "cool"}),
            ("ac_living_room", "ac", "living_room", "on", {"temperature": 24, "mode": "cool"}),
            ("speaker_living_room", "speaker", "living_room", "off", {"volume": 50, "playing": None}),
        ]
        for did, dtype, room, status, props in devices:
            self._states[did] = DeviceState(did, dtype, room, status, props)

    def sync_from_ha(self, ha_client) -> int:
        """Sync device states from Home Assistant. Returns number of devices synced."""
        if not ha_client.enabled:
            return 0

        self._states.clear()
        self._ha_entity_map.clear()
        count = 0

        # Sync lights
        for entity in ha_client.get_entities_by_domain("light"):
            entity_id = entity["entity_id"]
            attrs = entity.get("attributes", {})
            friendly_name = attrs.get("friendly_name", entity_id)
            room = self._extract_room(entity_id, friendly_name)
            local_id = f"light_{room}"

            brightness = 0
            if entity["state"] == "on":
                brightness = int(attrs.get("brightness", 255) / 255 * 100)

            self._states[local_id] = DeviceState(
                device_id=local_id,
                device_type="light",
                room=room,
                status=entity["state"],
                properties={"brightness": brightness},
                ha_entity_id=entity_id,
            )
            self._ha_entity_map[local_id] = entity_id
            count += 1

        # Sync climate (AC)
        for entity in ha_client.get_entities_by_domain("climate"):
            entity_id = entity["entity_id"]
            attrs = entity.get("attributes", {})
            friendly_name = attrs.get("friendly_name", entity_id)
            room = self._extract_room(entity_id, friendly_name)
            local_id = f"ac_{room}"

            status = "on" if entity["state"] not in ("off", "unavailable") else "off"
            self._states[local_id] = DeviceState(
                device_id=local_id,
                device_type="ac",
                room=room,
                status=status,
                properties={
                    "temperature": attrs.get("temperature", 26),
                    "mode": entity["state"] if status == "on" else "off",
                },
                ha_entity_id=entity_id,
            )
            self._ha_entity_map[local_id] = entity_id
            count += 1

        # Sync media players (speakers)
        for entity in ha_client.get_entities_by_domain("media_player"):
            entity_id = entity["entity_id"]
            attrs = entity.get("attributes", {})
            friendly_name = attrs.get("friendly_name", entity_id)
            room = self._extract_room(entity_id, friendly_name)
            local_id = f"speaker_{room}"

            status = "on" if entity["state"] == "playing" else "off"
            self._states[local_id] = DeviceState(
                device_id=local_id,
                device_type="speaker",
                room=room,
                status=status,
                properties={
                    "volume": int(attrs.get("volume_level", 0.5) * 100),
                    "playing": attrs.get("media_title"),
                },
                ha_entity_id=entity_id,
            )
            self._ha_entity_map[local_id] = entity_id
            count += 1

        return count

    def _extract_room(self, entity_id: str, friendly_name: str) -> str:
        """Extract room name from entity_id or friendly_name."""
        name = entity_id.split(".")[-1].lower()

        # 常见房间名映射
        room_mapping = {
            "bed": "bedroom", "bedroom": "bedroom",
            "living": "living_room", "living_room": "living_room", "lounge": "living_room",
            "kitchen": "kitchen",
            "office": "office", "study": "study",
            "bathroom": "bathroom", "bath": "bathroom",
            "garage": "garage",
            "entrance": "entrance", "hallway": "hallway",
            "ceiling": "living_room",  # ceiling lights 通常在客厅
        }

        # 检查 entity_id 中是否包含房间关键词
        for keyword, room in room_mapping.items():
            if keyword in name:
                return room

        # Fallback: 使用实体名的第一个词
        parts = name.replace("_", " ").split()
        return parts[0] if parts else "unknown"

    def get_ha_entity_id(self, local_device_id: str) -> str | None:
        """Get Home Assistant entity_id for a local device."""
        state = self._states.get(local_device_id)
        return state.ha_entity_id if state else None

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
