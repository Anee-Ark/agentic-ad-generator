from .base_agent import BaseAgent
from typing import Dict, Any, List, Optional
from gtts import gTTS
import os
import time

try:
    from elevenlabs.client import ElevenLabs
except Exception:
    ElevenLabs = None  # optional dependency import guard


class AudioProducerAgent(BaseAgent):
    """Agent that handles voiceover and music"""

    def __init__(self):
        super().__init__(name="AudioProducer")

        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        self.voice_provider = os.getenv("VOICE_PROVIDER", "gtts")  # gtts or elevenlabs

        # Initialize ElevenLabs client if available + key exists
        self.eleven_client = None
        if self.voice_provider.lower() == "elevenlabs":
            if not self.elevenlabs_api_key:
                self.logger.warning("VOICE_PROVIDER=elevenlabs but ELEVENLABS_API_KEY is not set. Falling back to gtts.")
                self.voice_provider = "gtts"
            elif ElevenLabs is None:
                self.logger.warning("elevenlabs package not importable. Falling back to gtts.")
                self.voice_provider = "gtts"
            else:
                self.eleven_client = ElevenLabs(api_key=self.elevenlabs_api_key)

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate audio elements

        Input:
            - script: str
            - voiceover_instructions: dict (optional)
            - music_style: str (optional)
            - scenes: list (optional)
            - duration: int (optional)

        Output:
            - voiceover_path: str
            - music_recommendation: dict
            - audio_timeline: dict
        """
        self.validate_input(input_data, ["script"])

        script: str = input_data["script"]
        instructions: Dict[str, Any] = input_data.get("voiceover_instructions", {}) or {}
        duration: int = int(input_data.get("duration", 30))
        scenes: List[Dict[str, Any]] = input_data.get("scenes", []) or []

        # Generate voiceover
        voiceover_path = self._generate_voiceover(script, instructions)

        # Select music (placeholder for now)
        music_selection = self._select_music(
            input_data.get("music_style", "upbeat"),
            duration
        )

        return {
            "voiceover_path": voiceover_path,
            "music_recommendation": music_selection,
            "audio_timeline": self._create_audio_timeline(scenes, duration),
        }

    def _generate_voiceover(self, script: str, instructions: Dict[str, Any]) -> str:
        """Generate voiceover from script."""
        output_dir = "data/output/audio"
        os.makedirs(output_dir, exist_ok=True)

        ts = int(time.time())
        ext = "mp3"
        output_path = os.path.join(output_dir, f"voiceover_{ts}.{ext}")

        provider = self.voice_provider.lo_

