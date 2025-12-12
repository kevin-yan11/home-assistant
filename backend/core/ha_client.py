"""Home Assistant API Client."""
import requests
from typing import Any
from config import HA_URL, HA_TOKEN, HA_ENABLED


class HomeAssistantClient:
    """Client for interacting with Home Assistant REST API."""

    def __init__(self):
        self.base_url = HA_URL.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {HA_TOKEN}",
            "Content-Type": "application/json",
        }

    @property
    def enabled(self) -> bool:
        return HA_ENABLED and bool(HA_TOKEN)

    def _request(self, method: str, endpoint: str, data: dict = None) -> dict | list | None:
        """Make HTTP request to Home Assistant API."""
        url = f"{self.base_url}{endpoint}"
        try:
            resp = requests.request(method, url, headers=self.headers, json=data, timeout=10)
            resp.raise_for_status()
            return resp.json() if resp.content else None
        except requests.RequestException as e:
            print(f"[HA Client] Error: {e}")
            return None

    def check_connection(self) -> dict:
        """Check if Home Assistant is reachable."""
        result = self._request("GET", "/api/")
        if result:
            return {"connected": True, "message": result.get("message", "Connected")}
        return {"connected": False, "message": "Cannot connect to Home Assistant"}

    def get_states(self) -> list[dict]:
        """Get all entity states from Home Assistant."""
        return self._request("GET", "/api/states") or []

    def get_state(self, entity_id: str) -> dict | None:
        """Get state of a specific entity."""
        return self._request("GET", f"/api/states/{entity_id}")

    def call_service(self, domain: str, service: str, entity_id: str = None, **data) -> bool:
        """Call a Home Assistant service."""
        payload = dict(data)
        if entity_id:
            payload["entity_id"] = entity_id

        result = self._request("POST", f"/api/services/{domain}/{service}", payload)
        return result is not None

    # Convenience methods for common device types
    def turn_on_light(self, entity_id: str, brightness_pct: int = None) -> bool:
        """Turn on a light."""
        data = {}
        if brightness_pct is not None:
            data["brightness_pct"] = brightness_pct
        return self.call_service("light", "turn_on", entity_id, **data)

    def turn_off_light(self, entity_id: str) -> bool:
        """Turn off a light."""
        return self.call_service("light", "turn_off", entity_id)

    def set_climate(self, entity_id: str, temperature: int = None, hvac_mode: str = None) -> bool:
        """Control climate/AC device."""
        if hvac_mode:
            self.call_service("climate", "set_hvac_mode", entity_id, hvac_mode=hvac_mode)
        if temperature:
            return self.call_service("climate", "set_temperature", entity_id, temperature=temperature)
        return True

    def turn_off_climate(self, entity_id: str) -> bool:
        """Turn off climate device."""
        return self.call_service("climate", "turn_off", entity_id)

    def media_play(self, entity_id: str) -> bool:
        """Play media."""
        return self.call_service("media_player", "media_play", entity_id)

    def media_pause(self, entity_id: str) -> bool:
        """Pause media."""
        return self.call_service("media_player", "media_pause", entity_id)

    def media_stop(self, entity_id: str) -> bool:
        """Stop media."""
        return self.call_service("media_player", "media_stop", entity_id)

    def set_volume(self, entity_id: str, volume_level: float) -> bool:
        """Set volume (0.0 to 1.0)."""
        return self.call_service("media_player", "volume_set", entity_id, volume_level=volume_level)

    def get_entities_by_domain(self, domain: str) -> list[dict]:
        """Get all entities for a specific domain (light, climate, media_player, etc.)."""
        states = self.get_states()
        return [s for s in states if s.get("entity_id", "").startswith(f"{domain}.")]


# Global client instance
ha_client = HomeAssistantClient()
