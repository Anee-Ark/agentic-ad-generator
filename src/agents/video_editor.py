from .base_agent import BaseAgent
from typing import Dict, Any, List, Optional
import os
import time

from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    concatenate_videoclips,
)
from moviepy.video.fx.all import crop


class VideoEditorAgent(BaseAgent):
    """Agent that assembles the final video"""

    def __init__(self):
        super().__init__(name="VideoEditor")

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assemble final video from all components

        Input:
            - scenes: list (from Script Analyzer)
            - scene_visuals: dict (from Visual Designer: contains scene_matches)
            - image_analysis: list (from Visual Designer: contains image paths + metadata)
            - voiceover_path: str (optional)
            - fps: int (optional)

        Output:
            - video_path: str
            - duration: float
            - resolution: str
            - fps: int
        """
        self.validate_input(input_data, ["scenes", "scene_visuals", "image_analysis"])

        scenes: List[Dict[str, Any]] = input_data["scenes"]
        scene_visuals: Dict[str, Any] = input_data["scene_visuals"]
        image_analysis: List[Dict[str, Any]] = input_data["image_analysis"]

        fps = int(input_data.get("fps", 30))
        voiceover_path = input_data.get("voiceover_path")

        # Create video clips from scenes
        video_clips = self._create_video_clips(scenes, scene_visuals, image_analysis)

        # Assemble timeline (video + audio)
        final_video = self._assemble_timeline(video_clips, voiceover_path)

        # Export
        output_path = self._export_video(final_video, fps=fps)

        return {
            "video_path": output_path,
            "duration": float(final_video.duration),
            "resolution": "1920x1080",
            "fps": fps,
        }

    def _create_video_clips(
        self,
        scenes: List[Dict[str, Any]],
        scene_visuals: Dict[str, Any],
        image_analysis: List[Dict[str, Any]],
    ) -> List[ImageClip]:
        """Create a clip per scene using matched images."""
        clips: List[ImageClip] = []

        scene_matches = scene_visuals.get("scene_matches", []) or []

        for scene in scenes:
            scene_id = scene.get("scene_id")
            duration = float(scene.get("duration", 5))

            visual = next((v for v in scene_matches if v.get("scene_id") == scene_id), None)

            # If no visual match, skip (or later: generate placeholder)
            if not visual:
                self.logger.warning(f"No visual match for {scene_id}; skipping scene.")
                continue

            image_id = visual.get("image_id")
            image_path = self._get_image_path(image_id, image_analysis)

            if not image_path or not os.path.exists(image_path):
                self.logger.warning(f"Image not found for {scene_id} (image_id={image_id}): {image_path}")
                continue

            clip = ImageClip(image_path).set_duration(duration)

            # Fit to 1920x1080 with crop (no black bars)
            clip = self._fit_to_1080p(clip)

            # Simple transition in
            transition = (scene.get("transition_in") or "fade").lower()
            if transition == "fade":
                clip = clip.fadein(0.4)

            clips.append(clip)

        if not clips:
            raise ValueError("No video clips created (check image paths and scene_matches).")

        return clips

    def _get_image_path(self, image_id: Optional[int], image_analysis: List[Dict[str, Any]]) -> Optional[str]:
        """Resolve image_id -> actual path using VisualDesigner image_analysis."""
        if image_id is None:
            return None
        try:
            idx = int(image_id)
            if 0 <= idx < len(image_analysis):
                return image_analysis[idx].get("path")
        except Exception:
            return None
        return None

    def _fit_to_1080p(self, clip: ImageClip) -> ImageClip:
        """
        Resize and crop to exact 1920x1080.
        Strategy: scale up until it covers 1920x1080, then center-crop.
        """
        target_w, target_h = 1920, 1080
        w, h = clip.size

        # scale factor to cover target
        scale = max(target_w / w, target_h / h)
        clip = clip.resize(scale)

        # center crop
        clip = crop(clip, width=target_w, height=target_h, x_center=clip.w / 2, y_center=clip.h / 2)
        return clip

    def _assemble_timeline(
        self,
        video_clips: List[ImageClip],
        voiceover_path: Optional[str] = None,
    ):
        """Concatenate clips and attach voiceover audio if available."""
        final_video = concatenate_videoclips(video_clips, method="compose")

        if voiceover_path and os.path.exists(voiceover_path):
            audio = AudioFileClip(voiceover_path)
            # If audio is longer than video, trim it; if shorter, keep as-is
            if audio.duration > final_video.duration:
                audio = audio.subclip(0, final_video.duration)
            final_video = final_video.set_audio(audio)
        else:
            self.logger.info("No voiceover audio attached.")

        return final_video

    def _export_video(self, video, fps: int = 30) -> str:
        """Export final video."""
        output_dir = "data/output/videos"
        os.makedirs(output_dir, exist_ok=True)

        ts = int(time.time())
        output_path = os.path.join(output_dir, f"final_ad_{ts}.mp4")

        video.write_videofile(
            output_path,
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
            threads=4,
        )

        self.logger.info(f"Video exported: {output_path}")
        return output_path

