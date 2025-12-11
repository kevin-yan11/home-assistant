from agentscope.tool import ToolResponse
from core.state_manager import state_manager

ROOM_ALIAS = {
    "卧室": "bedroom", "bedroom": "bedroom",
    "客厅": "living_room", "living_room": "living_room", "livingroom": "living_room",
    "厨房": "kitchen", "kitchen": "kitchen",
    "书房": "study", "study": "study",
}


def control_light(room: str, action: str, brightness: int = None) -> ToolResponse:
    """
    Control light device.

    Args:
        room: Room name (bedroom, living_room, etc.)
        action: turn_on, turn_off, or dim
        brightness: 0-100, required for dim action
    """
    room_key = ROOM_ALIAS.get(room.lower(), room.lower())
    device_id = f"light_{room_key}"

    if action == "turn_on":
        br = brightness if brightness else 100
        state_manager.update(device_id, status="on", properties={"brightness": br})
        return ToolResponse(content=f"Light in {room} turned on, brightness {br}%")

    elif action == "turn_off":
        state_manager.update(device_id, status="off", properties={"brightness": 0})
        return ToolResponse(content=f"Light in {room} turned off")

    elif action == "dim":
        br = brightness if brightness else 50
        state_manager.update(device_id, status="on", properties={"brightness": br})
        return ToolResponse(content=f"Light in {room} dimmed to {br}%")

    return ToolResponse(content=f"Unknown action: {action}")


def control_ac(room: str, action: str, temperature: int = None, mode: str = None) -> ToolResponse:
    """
    Control air conditioner.

    Args:
        room: Room name
        action: turn_on, turn_off, or set_temp
        temperature: 16-30
        mode: cool, heat, or auto
    """
    room_key = ROOM_ALIAS.get(room.lower(), room.lower())
    device_id = f"ac_{room_key}"

    if action == "turn_on":
        props = {"temperature": temperature or 26, "mode": mode or "cool"}
        state_manager.update(device_id, status="on", properties=props)
        return ToolResponse(content=f"AC in {room} turned on, {props['temperature']}°C, mode: {props['mode']}")

    elif action == "turn_off":
        state_manager.update(device_id, status="off")
        return ToolResponse(content=f"AC in {room} turned off")

    elif action == "set_temp":
        state_manager.update(device_id, properties={"temperature": temperature})
        return ToolResponse(content=f"AC in {room} set to {temperature}°C")

    return ToolResponse(content=f"Unknown action: {action}")


def control_speaker(room: str, action: str, song: str = None, volume: int = None) -> ToolResponse:
    """
    Control speaker/music player.

    Args:
        room: Room name
        action: play, pause, stop, or set_volume
        song: Song or playlist name
        volume: 0-100
    """
    room_key = ROOM_ALIAS.get(room.lower(), room.lower())
    device_id = f"speaker_{room_key}"

    if action == "play":
        track = song or "ambient music"
        state_manager.update(device_id, status="on", properties={"playing": track, "volume": volume or 50})
        return ToolResponse(content=f"Now playing: {track}")

    elif action in ("pause", "stop"):
        state_manager.update(device_id, status="off", properties={"playing": None})
        return ToolResponse(content="Playback stopped")

    elif action == "set_volume":
        state_manager.update(device_id, properties={"volume": volume})
        return ToolResponse(content=f"Volume set to {volume}%")

    return ToolResponse(content=f"Unknown action: {action}")


def get_device_status(room: str = None) -> ToolResponse:
    """
    Query current device status.

    Args:
        room: Optional room filter
    """
    return ToolResponse(content=state_manager.get_context())
