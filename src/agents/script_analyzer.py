from .base_agent import BaseAgent
from typing import Dict, Any
import json
import re


class ScriptAnalyzerAgent(BaseAgent):
    """Agent that analyzes scripts and breaks them into scenes"""

    def __init__(self):
        super().__init__(name="ScriptAnalyzer")

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes script and creates detailed scene breakdown

        Input:
            - script: str
            - creative_brief: dict (optional)
            - target_duration: int (seconds, optional)

        Output:
            - total_duration: int
            - scenes: list of scene objects
            - visual_requirements: list
            - voiceover_instructions: dict
            - call_to_action: dict
        """
        self.validate_input(input_data, ["script"])

        prompt = self._build_analysis_prompt(input_data)
        system_prompt = (
            "You are an expert script analyst for video production. "
            "Break down scripts into actionable scenes with precise timing and visual requirements. "
            "Return ONLY valid JSON matching the requested schema."
        )

        response = self.call_llm(prompt, system_prompt, temperature=0.3)

        analysis = self._parse_analysis_response(response)

        # Minimal schema safety (downstream protection)
        analysis.setdefault("scenes", [])
        analysis.setdefault("visual_requirements", [])
        analysis.setdefault("voiceover_instructions", {})
        analysis.setdefault("call_to_action", {})
        analysis.setdefault("total_duration", input_data.get("target_duration", 30))

        return analysis

    def _build_analysis_prompt(self, input_data: Dict[str, Any]) -> str:
        """Build prompt for script analysis"""

        script = input_data["script"]
        target_duration = int(input_data.get("target_duration", 30))

        prompt = f"""Analyze this script for a {target_duration}-second video advertisement.

SCRIPT:
{script}
"""

        if "creative_brief" in input_data and input_data["creative_brief"] is not None:
            prompt += "\n\nCREATIVE DIRECTION:\n" + json.dumps(
                input_data["creative_brief"], indent=2
            )

        prompt += f"""

Break this down into a detailed production plan in JSON format:

{{
  "total_duration": {target_duration},
  "scenes": [
    {{
      "scene_id": "scene_1",
      "start_time": 0,
      "end_time": 5,
      "duration": 5,
      "script_text": "Exact words spoken",
      "visual_description": "What should be shown on screen",
      "visual_type": "product_shot/lifestyle/text_overlay/b_roll",
      "transition_in": "fade/cut/slide/zoom",
      "transition_out": "fade/cut/slide/zoom",
      "pacing": "slow/medium/fast",
      "emphasis_words": ["important", "words"],
      "required_assets": ["asset1", "asset2"]
    }}
  ],
  "visual_requirements": [
    {{
      "type": "product_photo/lifestyle_image/graphic/text",
      "description": "Detailed description of needed visual",
      "scenes": ["scene_1", "scene_2"],
      "priority": "high/medium/low"
    }}
  ],
  "voiceover_instructions": {{
    "tone": "professional/friendly/exciting/calm",
    "pace": "fast/medium/slow",
    "emphasis_points": ["timestamp:word"],
    "pauses": [3.5, 7.2, 12.0]
  }},
  "call_to_action": {{
    "text": "CTA text",
    "start_time": {max(target_duration - 5, 0)},
    "duration": {min(5, target_duration)},
    "visual_style": "bold/simple/animated"
  }}
}}

Rules:
- Return ONLY valid JSON (no markdown, no extra commentary).
- Scene timings must be consistent: end_time = start_time + duration.
- Scenes must total exactly {target_duration} seconds.
- Use 4–8 scenes unless the script is extremely short/long.
- Keep visuals concrete and producible.

Be precise with timing - scenes must total exactly {target_duration} seconds.
"""
        return prompt

    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse analysis response"""
        cleaned = response.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        # 1) Try parse whole response
        try:
            analysis = json.loads(cleaned)
            self._validate_timing(analysis)
            return analysis
        except json.JSONDecodeError:
            pass

        # 2) Fallback: extract largest JSON object substring
        try:
            start_idx = cleaned.find("{")
            end_idx = cleaned.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = cleaned[start_idx:end_idx]
                analysis = json.loads(json_str)
                self._validate_timing(analysis)
                return analysis
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parse error: {e}")

        return {"raw_response": response}

    def _validate_timing(self, analysis: Dict[str, Any]) -> None:
        """Ensure scenes have valid timing and total duration matches target."""
        if "scenes" not in analysis or not isinstance(analysis["scenes"], list):
            return

        target = analysis.get("total_duration")
        if not isinstance(target, (int, float)):
            return

        # Sum durations
        total = 0.0
        for s in analysis["scenes"]:
            dur = s.get("duration")
            if isinstance(dur, (int, float)):
                total += float(dur)

        # Warn if off by >1 second
        if abs(total - float(target)) > 1.0:
            self.logger.warning(
                f"Scene durations ({total:.2f}s) don't match target ({target}s)"
            )

        # Optional: if off by <= 1 second, auto-adjust last scene to match exactly
        if analysis["scenes"] and abs(total - float(target)) <= 1.0:
            delta = float(target) - total
            last = analysis["scenes"][-1]
            if isinstance(last.get("duration"), (int, float)):
                last["duration"] = round(float(last["duration"]) + delta, 2)
                if isinstance(last.get("start_time"), (int, float)):
                    last["end_time"] = round(float(last["start_time"]) + float(last["duration"]), 2)

