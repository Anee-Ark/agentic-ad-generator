from .base_agent import BaseAgent
from typing import Dict, Any, List
import os
import json
import re

from moviepy.editor import VideoFileClip


class QAAgent(BaseAgent):
    """Agent that reviews final output quality"""

    def __init__(self):
        super().__init__(name="QAAgent")

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Review video quality and requirements

        Input:
            - video_path: str
            - original_requirements: dict (optional)
            - creative_brief: dict (optional)
            - scenes: list (optional)

        Output:
            - approved: bool
            - quality_score: float
            - issues: list
            - recommendations: list
        """
        self.validate_input(input_data, ["video_path"])

        video_path = input_data["video_path"]
        if not os.path.exists(video_path):
            return {
                "approved": False,
                "quality_score": 0.0,
                "issues": ["Video file not found"],
                "recommendations": ["Regenerate video"],
                "technical_check": {"score": 0.0, "issues": ["Missing file"]},
                "content_check": {"score": 0.0, "issues": ["No file to review"]},
            }

        technical_check = self._check_technical_quality(
            video_path=video_path,
            requirements=input_data.get("original_requirements", {}) or {},
        )

        content_check = self._check_content_quality(
            requirements=input_data.get("original_requirements", {}) or {},
            creative_brief=input_data.get("creative_brief", {}) or {},
            scenes=input_data.get("scenes", []) or [],
        )

        quality_score = self._calculate_quality_score(technical_check, content_check)
        approved = quality_score >= 0.8

        issues = (technical_check.get("issues", []) or []) + (content_check.get("issues", []) or [])
        recommendations = self._generate_recommendations(technical_check, content_check)

        return {
            "approved": approved,
            "quality_score": quality_score,
            "technical_check": technical_check,
            "content_check": content_check,
            "issues": issues,
            "recommendations": recommendations,
        }

    def _check_technical_quality(self, video_path: str, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Check technical aspects: file size, duration, resolution, fps, audio presence."""
        issues: List[str] = []

        checks: Dict[str, Any] = {
            "file_exists": True,
            "file_size_mb": round(os.path.getsize(video_path) / (1024 * 1024), 3),
        }

        # Basic file size sanity
        if checks["file_size_mb"] < 0.1:
            issues.append("Video file is too small - may be corrupted")
        elif checks["file_size_mb"] > 200:
            issues.append("Video file is very large - consider compression")

        # Read metadata via MoviePy (already in your deps)
        try:
            with VideoFileClip(video_path) as clip:
                checks["duration_seconds"] = round(float(clip.duration), 2)
                checks["fps"] = float(getattr(clip, "fps", 0) or 0)
                checks["resolution"] = f"{clip.w}x{clip.h}"
                checks["has_audio"] = clip.audio is not None

                # Optional requirements checks (if provided)
                target_duration = requirements.get("duration") or requirements.get("target_duration")
                if target_duration is not None:
                    try:
                        td = float(target_duration)
                        if abs(checks["duration_seconds"] - td) > 1.0:
                            issues.append(f"Duration mismatch: {checks['duration_seconds']}s vs target {td}s")
                    except Exception:
                        pass

                target_resolution = requirements.get("resolution")
                if target_resolution and isinstance(target_resolution, str):
                    if target_resolution != checks["resolution"]:
                        issues.append(f"Resolution mismatch: {checks['resolution']} vs target {target_resolution}")

                target_fps = requirements.get("fps")
                if target_fps is not None:
                    try:
                        tfps = float(target_fps)
                        if checks["fps"] and abs(checks["fps"] - tfps) > 1.0:
                            issues.append(f"FPS mismatch: {checks['fps']} vs target {tfps}")
                    except Exception:
                        pass

                if not checks["has_audio"]:
                    issues.append("No audio track detected (missing voiceover/music)")

        except Exception as e:
            issues.append(f"Could not read video metadata: {e}")

        # Score heuristic
        score = 1.0
        if issues:
            score = 0.75 if len(issues) <= 2 else 0.6

        return {"score": score, "checks": checks, "issues": issues}

    def _check_content_quality(
        self,
        requirements: Dict[str, Any],
        creative_brief: Dict[str, Any],
        scenes: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """LLM-based check: messaging, pacing, CTA, audience fit, alignment."""
        prompt = f"""Review this video advertisement project for quality and effectiveness.

ORIGINAL REQUIREMENTS:
{json.dumps(requirements, indent=2)}

CREATIVE BRIEF:
{json.dumps(creative_brief, indent=2)}

IMPLEMENTED SCENES:
{json.dumps(scenes, indent=2)}

Evaluate the following aspects and provide scores (0-10) for each:
1. Message Clarity
2. Visual Appeal
3. Brand Alignment
4. Pacing
5. Call to Action
6. Target Audience Fit
7. Overall Effectiveness

Return ONLY valid JSON in this format:
{{
  "scores": {{
    "message_clarity": 8,
    "visual_appeal": 7,
    "brand_alignment": 9,
    "pacing": 8,
    "call_to_action": 7,
    "target_audience_fit": 8,
    "overall_effectiveness": 8
  }},
  "strengths": ["strength1", "strength2"],
  "weaknesses": ["weakness1", "weakness2"],
  "issues": ["critical issue 1"],
  "suggestions": ["improvement 1", "improvement 2"]
}}
"""
        system_prompt = (
            "You are an expert video advertisement reviewer with years of experience in marketing, "
            "creative direction, and video production. Be honest but constructive."
        )

        response = self.call_llm(prompt, system_prompt, temperature=0.3)

        assessment = self._parse_json_response(
            response,
            fallback={
                "score": 0.5,
                "issues": ["Could not parse quality assessment"],
                "raw_response": response,
                "scores": {},
                "suggestions": [],
            },
        )

        # Normalize score 0-1
        scores = assessment.get("scores", {}) or {}
        if scores:
            try:
                avg_score = sum(float(v) for v in scores.values()) / len(scores)
                assessment["score"] = round(avg_score / 10.0, 2)
            except Exception:
                assessment["score"] = assessment.get("score", 0.5)
        else:
            assessment.setdefault("score", 0.5)

        return assessment

    def _calculate_quality_score(self, technical_check: Dict[str, Any], content_check: Dict[str, Any]) -> float:
        """Overall score: 30% technical, 70% content."""
        technical_score = float(technical_check.get("score", 0.5))
        content_score = float(content_check.get("score", 0.5))
        overall = (technical_score * 0.3) + (content_score * 0.7)
        return round(overall, 2)

    def _generate_recommendations(self, technical_check: Dict[str, Any], content_check: Dict[str, Any]) -> List[str]:
        recommendations: List[str] = []

        if float(technical_check.get("score", 1.0)) < 0.8:
            recommendations.extend(
                [
                    "Review technical video specs (duration, resolution, fps).",
                    "Check audio levels and ensure voiceover is present.",
                    "Compress or re-export with optimized bitrate if file is too large.",
                ]
            )

        # Add model suggestions
        suggestions = content_check.get("suggestions", []) or []
        recommendations.extend(suggestions)

        # Add aspect-based recs
        scores = content_check.get("scores", {}) or {}
        for aspect, score in scores.items():
            try:
                if float(score) < 7:
                    recommendations.append(f"Improve {aspect.replace('_', ' ')}.")
            except Exception:
                pass

        # Keep top 5, de-dup
        deduped = []
        for r in recommendations:
            if r not in deduped:
                deduped.append(r)
        return deduped[:5]

    def _parse_json_response(self, response: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
        """Robust JSON parsing, handles ```json fences and extra text."""
        cleaned = response.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        try:
            start_idx = cleaned.find("{")
            end_idx = cleaned.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                return json.loads(cleaned[start_idx:end_idx])
        except Exception:
            pass

        self.logger.warning("Could not parse JSON from QA response")
        return fallback

