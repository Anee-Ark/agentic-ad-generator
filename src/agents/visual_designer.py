from .base_agent import BaseAgent
from typing import Dict, Any, List
from PIL import Image
import os
import json
import re


class VisualDesignerAgent(BaseAgent):
    """Agent that handles all visual elements"""

    def __init__(self):
        super().__init__(name="VisualDesigner")

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes images and creates visual specifications

        Input:
            - images: list of image paths
            - scene_requirements: list (typically derived from Script Analyzer scenes/visual_requirements)
            - creative_brief: dict (optional)

        Output:
            - image_analysis: list of analyzed images
            - scene_visuals: scene matches + missing visuals
            - processing_instructions: instructions for video editor
        """
        self.validate_input(input_data, ["images", "scene_requirements"])

        image_paths: List[str] = input_data["images"]
        scene_requirements: List[Dict[str, Any]] = input_data["scene_requirements"]
        creative_brief: Dict[str, Any] = input_data.get("creative_brief", {}) or {}

        # Analyze provided images
        image_analysis = self._analyze_images(image_paths)

        # Match images to scenes (LLM reasoning step)
        scene_visuals = self._match_images_to_scenes(
            image_analysis=image_analysis,
            scene_requirements=scene_requirements,
            creative_brief=creative_brief,
        )

        # Create concrete processing instructions for editor
        processing_instructions = self._create_processing_instructions(scene_visuals)

        return {
            "image_analysis": image_analysis,
            "scene_visuals": scene_visuals,
            "processing_instructions": processing_instructions,
        }

    def _analyze_images(self, image_paths: List[str]) -> List[Dict[str, Any]]:
        """Analyze each provided image (basic metadata + placeholder description)."""
        analyses: List[Dict[str, Any]] = []

        for img_path in image_paths:
            try:
                if not os.path.exists(img_path):
                    self.logger.warning(f"Image path not found: {img_path}")
                    continue

                with Image.open(img_path) as img:
                    width, height = img.size
                    aspect_ratio = round(width / height, 4) if height else None

                    description = self._describe_image(img_path, width, height)

                    analyses.append(
                        {
                            "path": img_path,
                            "filename": os.path.basename(img_path),
                            "width": width,
                            "height": height,
                            "aspect_ratio": aspect_ratio,
                            "description": description,
                            "format": img.format,
                        }
                    )

            except Exception as e:
                self.logger.error(f"Error analyzing {img_path}: {e}")

        return analyses

    def _describe_image(self, image_path: str, width: int, height: int) -> str:
        """
        Placeholder for Claude vision.

        For now, return a lightweight description so matching still works.
        Later you can upgrade this to Claude vision / OpenAI vision by sending image bytes.
        """
        filename = os.path.basename(image_path)
        return f"{filename} ({width}x{height})"

    def _match_images_to_scenes(
        self,
        image_analysis: List[Dict[str, Any]],
        scene_requirements: List[Dict[str, Any]],
        creative_brief: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Match available images to required scenes using LLM."""

        available_images_payload = [
            {
                "id": i,
                "filename": img.get("filename"),
                "description": img.get("description"),
                "aspect_ratio": img.get("aspect_ratio"),
                "width": img.get("width"),
                "height": img.get("height"),
            }
            for i, img in enumerate(image_analysis)
        ]

        prompt = f"""Match these available images to the required scenes.

AVAILABLE IMAGES:
{json.dumps(available_images_payload, indent=2)}

SCENE REQUIREMENTS:
{json.dumps(scene_requirements, indent=2)}

CREATIVE DIRECTION:
{json.dumps(creative_brief, indent=2)}

Return ONLY valid JSON in this schema:
{{
  "scene_matches": [
    {{
      "scene_id": "scene_1",
      "image_id": 0,
      "rationale": "Why this image works for this scene",
      "composition": {{
        "crop": "center/top/bottom/left/right",
        "zoom": 1.0,
        "pan": "none/left/right/up/down",
        "effects": ["effect1", "effect2"]
      }}
    }}
  ],
  "missing_visuals": [
    {{
      "scene_id": "scene_x",
      "description": "What visual is needed",
      "generation_prompt": "Prompt for AI image generation"
    }}
  ]
}}

Rules:
- Use image_id = null if no suitable image exists for a scene.
- Keep effects simple and video-editable (e.g., "blur_background", "vignette", "warm_grade", "ken_burns").
- Prefer matching aspect ratio close to 16:9 for 1920x1080 output.
"""

        response = self.call_llm(prompt, temperature=0.5)
        return self._parse_json_response(
            response, fallback={"scene_matches": [], "missing_visuals": []}
        )

    def _create_processing_instructions(self, scene_visuals: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create detailed processing instructions for video editor."""
        instructions: List[Dict[str, Any]] = []

        for match in scene_visuals.get("scene_matches", []):
            instructions.append(
                {
                    "scene_id": match.get("scene_id"),
                    "image_id": match.get("image_id"),
                    "processing": match.get("composition", {}),
                    "priority": "high",
                }
            )

        return instructions

    def _parse_json_response(self, response: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
        """Robust JSON parse: strips ```json fences and extracts object if needed."""
        cleaned = response.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        # 1) Try parse whole response
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 2) Fallback: extract largest JSON object substring
        try:
            start_idx = cleaned.find("{")
            end_idx = cleaned.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                return json.loads(cleaned[start_idx:end_idx])
        except Exception:
            pass

        self.logger.warning("Could not parse JSON from VisualDesigner response")
        return fallback

