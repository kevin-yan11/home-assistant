"""
Rule Engine - Fast path for simple commands.
Pattern matching to bypass LLM for common operations.
"""
import re
from dataclasses import dataclass
from typing import Callable, Optional
from core.state_manager import state_manager
from core.ha_client import ha_client


@dataclass
class RuleResult:
    matched: bool
    response: str = ""
    action_taken: bool = False


class RuleEngine:
    """
    Fast path rule engine for simple commands.
    Covers common patterns like "turn on/off X" without LLM overhead.
    """

    def __init__(self):
        self.rules: list[tuple[re.Pattern, Callable]] = []
        self._register_rules()

    def _register_rules(self):
        """Register pattern matching rules."""
        # Light control patterns
        self.rules.append((
            re.compile(r"^(turn on|open)\s*(.*?)\s*(light|lights?)$", re.I),
            self._handle_light_on
        ))
        self.rules.append((
            re.compile(r"^(turn off|close)\s*(.*?)\s*(light|lights?)$", re.I),
            self._handle_light_off
        ))
        # AC control patterns
        self.rules.append((
            re.compile(r"^(turn on)\s*(.*?)\s*(ac|air\s*con)$", re.I),
            self._handle_ac_on
        ))
        self.rules.append((
            re.compile(r"^(turn off)\s*(.*?)\s*(ac|air\s*con)$", re.I),
            self._handle_ac_off
        ))
        # Speaker control patterns
        self.rules.append((
            re.compile(r"^(pause|stop)\s*(music)?$", re.I),
            self._handle_speaker_pause
        ))
        self.rules.append((
            re.compile(r"^(play)\s*(music)?$", re.I),
            self._handle_speaker_play
        ))

    def process(self, user_input: str) -> RuleResult:
        """
        Try to match input against rules.
        Returns RuleResult with matched=True if handled, False otherwise.
        """
        user_input = user_input.strip()

        for pattern, handler in self.rules:
            match = pattern.match(user_input)
            if match:
                return handler(match)

        return RuleResult(matched=False)

    def _parse_room(self, room_str: str) -> str:
        """Parse room name from input."""
        room_str = room_str.strip().lower()
        room_map = {
            "bedroom": "bedroom",
            "living room": "living_room", "living_room": "living_room",
            "kitchen": "kitchen",
            "office": "office",
            "bathroom": "bathroom",
            "": "living_room",  # Default to living room
        }
        return room_map.get(room_str, room_str.replace(" ", "_"))

    def _handle_light_on(self, match: re.Match) -> RuleResult:
        room_str = match.group(2)
        room = self._parse_room(room_str)
        device_id = f"light_{room}"

        # Update local state
        if state_manager.update(device_id, status="on", properties={"brightness": 100}):
            # Sync to Home Assistant if enabled
            if ha_client.enabled:
                entity_id = state_manager.get_ha_entity_id(device_id)
                if entity_id:
                    ha_client.call_service("light", "turn_on", entity_id, brightness=255)

            room_name = room.replace("_", " ").title()
            return RuleResult(
                matched=True,
                response=f"Turned on {room_name} light.",
                action_taken=True
            )

        return RuleResult(matched=True, response="Device not found.", action_taken=False)

    def _handle_light_off(self, match: re.Match) -> RuleResult:
        room_str = match.group(2)
        room = self._parse_room(room_str)
        device_id = f"light_{room}"

        if state_manager.update(device_id, status="off", properties={"brightness": 0}):
            if ha_client.enabled:
                entity_id = state_manager.get_ha_entity_id(device_id)
                if entity_id:
                    ha_client.call_service("light", "turn_off", entity_id)

            room_name = room.replace("_", " ").title()
            return RuleResult(
                matched=True,
                response=f"Turned off {room_name} light.",
                action_taken=True
            )

        return RuleResult(matched=True, response="Device not found.", action_taken=False)

    def _handle_ac_on(self, match: re.Match) -> RuleResult:
        room_str = match.group(2)
        room = self._parse_room(room_str)
        device_id = f"ac_{room}"

        if state_manager.update(device_id, status="on"):
            if ha_client.enabled:
                entity_id = state_manager.get_ha_entity_id(device_id)
                if entity_id:
                    ha_client.call_service("climate", "turn_on", entity_id)

            room_name = room.replace("_", " ").title()
            return RuleResult(
                matched=True,
                response=f"Turned on {room_name} AC.",
                action_taken=True
            )

        return RuleResult(matched=True, response="Device not found.", action_taken=False)

    def _handle_ac_off(self, match: re.Match) -> RuleResult:
        room_str = match.group(2)
        room = self._parse_room(room_str)
        device_id = f"ac_{room}"

        if state_manager.update(device_id, status="off"):
            if ha_client.enabled:
                entity_id = state_manager.get_ha_entity_id(device_id)
                if entity_id:
                    ha_client.call_service("climate", "turn_off", entity_id)

            room_name = room.replace("_", " ").title()
            return RuleResult(
                matched=True,
                response=f"Turned off {room_name} AC.",
                action_taken=True
            )

        return RuleResult(matched=True, response="Device not found.", action_taken=False)

    def _handle_speaker_pause(self, _match: re.Match) -> RuleResult:
        # Pause all speakers or find the playing one
        for device_id, state in state_manager.get_all().items():
            if state["type"] == "speaker" and state["status"] == "on":
                state_manager.update(device_id, status="off")
                if ha_client.enabled:
                    entity_id = state_manager.get_ha_entity_id(device_id)
                    if entity_id:
                        ha_client.call_service("media_player", "media_pause", entity_id)

        return RuleResult(
            matched=True,
            response="Paused.",
            action_taken=True
        )

    def _handle_speaker_play(self, _match: re.Match) -> RuleResult:
        # Resume the first speaker found
        for device_id, state in state_manager.get_all().items():
            if state["type"] == "speaker":
                state_manager.update(device_id, status="on")
                if ha_client.enabled:
                    entity_id = state_manager.get_ha_entity_id(device_id)
                    if entity_id:
                        ha_client.call_service("media_player", "media_play", entity_id)
                break

        return RuleResult(
            matched=True,
            response="Playing.",
            action_taken=True
        )


# Singleton instance
rule_engine = RuleEngine()
