from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import json
import os

# Import all agents
from src.agents.creative_director import CreativeDirectorAgent
from src.agents.script_analyzer import ScriptAnalyzerAgent
from src.agents.visual_designer import VisualDesignerAgent
from src.agents.audio_producer import AudioProducerAgent
from src.agents.video_editor import VideoEditorAgent
from src.agents.qa_agent import QAAgent


class WorkflowOrchestrator:
    """Orchestrates the entire multi-agent workflow"""

    def __init__(self):
        # Basic logging setup (only if not already configured elsewhere)
        if not logging.getLogger().handlers:
            logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

        self.logger = logging.getLogger("Orchestrator")

        # Initialize all agents
        self.creative_director = CreativeDirectorAgent()
        self.script_analyzer = ScriptAnalyzerAgent()
        self.visual_designer = VisualDesignerAgent()
        self.audio_producer = AudioProducerAgent()
        self.video_editor = VideoEditorAgent()
        self.qa_agent = QAAgent()

        # State management
        self.state = {
            "status": "initialized",
            "current_step": None,
            "outputs": {},
            "errors": []
        }

    def generate_advertisement(
        self,
        product_description: str,
        script: str,
        image_paths: List[str],
        target_audience: str = "General consumers",
        target_duration: int = 30,
        brand_guidelines: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main method to generate a complete video advertisement

        Returns:
            Dict containing video path and metadata
        """
        self.logger.info("Starting advertisement generation workflow")
        start_time = datetime.now()

        try:
            # Step 1: Creative Direction
            self.logger.info("Step 1: Creating creative brief")
            self.state["current_step"] = "creative_direction"

            creative_brief = self.creative_director.process({
                "product_description": product_description,
                "target_audience": target_audience,
                "brand_guidelines": brand_guidelines,
                "script": script
            })

            self.state["outputs"]["creative_brief"] = creative_brief
            self.logger.info("✓ Creative brief completed")

            # Step 2: Script Analysis
            self.logger.info("Step 2: Analyzing script")
            self.state["current_step"] = "script_analysis"

            script_analysis = self.script_analyzer.process({
                "script": script,
                "creative_brief": creative_brief,
                "target_duration": target_duration
            })

            self.state["outputs"]["script_analysis"] = script_analysis
            scenes = script_analysis.get("scenes", []) or []
            self.logger.info(f"✓ Script analyzed into {len(scenes)} scenes")

            # Step 3: Visual Design
            self.logger.info("Step 3: Processing visuals")
            self.state["current_step"] = "visual_design"

            # IMPORTANT: use scene-level requirements (scenes) for matching
            visual_design = self.visual_designer.process({
                "images": image_paths,
                "scene_requirements": scenes,  # <-- changed from visual_requirements
                "creative_brief": creative_brief
            })

            self.state["outputs"]["visual_design"] = visual_design
            self.logger.info("✓ Visual design completed")

            # Step 4: Audio Production
            self.logger.info("Step 4: Generating audio")
            self.state["current_step"] = "audio_production"

            audio_output = self.audio_producer.process({
                "script": script,
                "voiceover_instructions": script_analysis.get("voiceover_instructions", {}) or {},
                "music_style": creative_brief.get("music_style", "upbeat"),
                "scenes": scenes,
                "duration": target_duration
            })

            self.state["outputs"]["audio_output"] = audio_output
            self.logger.info("✓ Audio production completed")

            # Step 5: Video Editing
            self.logger.info("Step 5: Assembling video")
            self.state["current_step"] = "video_editing"

            # IMPORTANT: VideoEditorAgent expects scene_visuals + image_analysis separately
            video_output = self.video_editor.process({
                "scenes": scenes,
                "scene_visuals": visual_design.get("scene_visuals", {}),
                "image_analysis": visual_design.get("image_analysis", []),
                "voiceover_path": audio_output.get("voiceover_path"),
                "fps": 30
            })

            self.state["outputs"]["video_output"] = video_output
            video_path = video_output.get("video_path")
            self.logger.info(f"✓ Video assembled: {video_path}")

            # Step 6: Quality Assurance
            self.logger.info("Step 6: Quality review")
            self.state["current_step"] = "quality_assurance"

            qa_result = self.qa_agent.process({
                "video_path": video_path,
                "original_requirements": {
                    "product_description": product_description,
                    "target_audience": target_audience,
                    "duration": target_duration,
                    "resolution": "1920x1080",
                    "fps": 30
                },
                "creative_brief": creative_brief,
                "scenes": scenes
            })

            self.state["outputs"]["qa_result"] = qa_result

            if not qa_result.get("approved", False):
                self.logger.warning(f"QA failed. Score: {qa_result.get('quality_score', 0)}")
                self.logger.warning(f"Issues: {qa_result.get('issues', [])}")

            self.logger.info(f"✓ QA completed. Score: {qa_result.get('quality_score', 0)}")

            # Total time
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            result = {
                "success": True,
                "video_path": video_path,
                "duration": video_output.get("duration"),
                "quality_score": qa_result.get("quality_score"),
                "approved": qa_result.get("approved"),
                "processing_time_seconds": round(duration, 2),
                "metadata": {
                    "creative_brief": creative_brief,
                    "scenes": scenes,
                    "qa_report": qa_result
                }
            }

            self._save_workflow_state(result)

            self.logger.info(f"Advertisement generation completed in {duration:.2f} seconds")
            return result

        except Exception as e:
            self.logger.error(f"Error in workflow: {str(e)}", exc_info=True)
            self.state["errors"].append(str(e))

            return {
                "success": False,
                "error": str(e),
                "state": self.state
            }

    def _save_workflow_state(self, result: Dict[str, Any]) -> None:
        """Save the workflow state and results"""
        output_dir = "data/output/workflows"
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        state_file = os.path.join(output_dir, f"workflow_{timestamp}.json")

        with open(state_file, "w") as f:
            json.dump({"state": self.state, "result": result}, f, indent=2)

        self.logger.info(f"Workflow state saved: {state_file}")

    def get_status(self) -> Dict[str, Any]:
        """Get current workflow status"""
        return {
            "status": self.state["status"],
            "current_step": self.state["current_step"],
            "completed_steps": list(self.state["outputs"].keys()),
            "errors": self.state["errors"]
        }

