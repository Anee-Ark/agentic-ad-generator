from .base_agent import BaseAgent
from typing import Dict, Any
import json
import re


class CreativeDirectorAgent(BaseAgent):
    """Agent responsible for high-level creative decisions"""

    def __init__(self):
        super().__init__(name="CreativeDirector")

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes product and creates creative strategy

        Input:
            - product_description: str
            - target_audience: str
            - brand_guidelines: dict (optional)
            - script: str (optional)

        Output:
            - creative_concept: str
            - visual_style: str
            - mood: str
            - color_palette: list
            - key_messages: list
            - target_emotion: str
            - storyboard_outline: list
            - music_style: str
            - pacing: str
        """
        self.validate_input(input_data, ["product_description", "target_audience"])

        prompt = self._build_creative_prompt(input_data)
        system_prompt = (
            "You are an expert Creative Director specializing in video advertisements. "
            "Your role is to create compelling creative concepts that sell products effectively. "
            "Always think about emotional resonance, visual impact, and clear messaging. "
            "Return ONLY valid JSON matching the requested schema."
        )

        response = self.call_llm(prompt, system_prompt, temperature=0.7)

        creative_brief = self._parse_creative_response(response)

        # Minimal schema check (keeps downstream agents safe)
        required_keys = [
            "creative_concept",
            "visual_style",
            "mood",
            "color_palette",
            "key_messages",
            "target_emotion",
            "storyboard_outline",
            "music_style",
            "pacing",
        ]
        missing = [k for k in required_keys if k not in creative_brief]
        if missing:
            self.logger.warning(f"Creative brief missing keys: {missing}")
            creative_brief["_missing_keys"] = missing

        return creative_brief

    def _build_creative_prompt(self, input_data: Dict[str, Any]) -> str:
        """Build the prompt for creative direction"""

        prompt = f"""Create a comprehensive creative brief for a video advertisement.

Product Description: {input_data['product_description']}
Target Audience: {input_data['target_audience']}
"""

        if "brand_guidelines" in input_data and input_data["brand_guidelines"] is not None:
            prompt += f"\nBrand Guidelines: {input_data['brand_guidelines']}"

        if "script" in input_data and input_data["script"] is not None:
            prompt += f"\nProvided Script: {input_data['script']}"

        prompt += """

Provide your creative direction in the following JSON format:
{
  "creative_concept": "Main creative idea and theme",
  "visual_style": "Detailed description of visual aesthetic",
  "mood": "Overall emotional tone",
  "color_palette": ["color1", "color2", "color3"],
  "key_messages": ["message1", "message2", "message3"],
  "target_emotion": "Primary emotion to evoke",
  "storyboard_outline": [
    {
      "scene_number": 1,
      "description": "What happens in this scene",
      "duration_seconds": 5,
      "key_visual": "What the viewer sees",
      "message": "What this scene communicates"
    }
  ],
  "music_style": "Type of background music recommended",
  "pacing": "fast/medium/slow"
}

Rules:
- Return ONLY valid JSON (no markdown, no extra commentary).
- Ensure storyboard_outline has 4-8 scenes and total duration ~30 seconds unless the product needs less/more.
- Keep messaging punchy, specific, and benefit-driven.

Make it compelling, memorable, and effective at selling the product!
"""
        return prompt

    def _parse_creative_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured creative brief"""
        # 1) Strip common markdown fences if present
        cleaned = response.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        # 2) Try full JSON parse first
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 3) Fallback: extract the largest JSON object substring
        try:
            start_idx = cleaned.find("{")
            end_idx = cleaned.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = cleaned[start_idx:end_idx]
                return json.loads(json_str)
        except json.JSONDecodeError:
            self.logger.warning("Could not parse JSON from creative response")

        # 4) Final fallback: return raw response
        return {"raw_response": response}

