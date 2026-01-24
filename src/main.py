import os
import sys
import logging
from pathlib import Path
from typing import List
import argparse
import shutil
from dotenv import load_dotenv

from src.orchestrator.workflow_orchestrator import WorkflowOrchestrator

# Load environment variables
load_dotenv()

# Ensure logs directory exists BEFORE setting up FileHandler
Path("logs").mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


def setup_directories():
    """Create necessary directories"""
    directories = [
        "data/input",
        "data/output/videos",
        "data/output/audio",
        "data/output/workflows",
        "data/cache",
        "logs",
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

    logger.info("Directories setup complete")


def validate_inputs(image_paths: List[str], script: str) -> bool:
    """Validate input files and data"""
    for img_path in image_paths:
        if not os.path.exists(img_path):
            logger.error(f"Image not found: {img_path}")
            return False

    if not script or len(script.strip()) < 10:
        logger.error("Script is too short or empty")
        return False

    return True


def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(description="Generate video advertisements using AI agents")
    parser.add_argument("--product", required=True, help="Product description")
    parser.add_argument("--script", required=True, help="Advertisement script")
    parser.add_argument("--images", nargs="+", required=True, help="Paths to product images")
    parser.add_argument("--audience", default="General consumers", help="Target audience")
    parser.add_argument("--duration", type=int, default=30, help="Video duration in seconds")
    parser.add_argument("--output", default="data/output/videos", help="Output directory")

    args = parser.parse_args()

    setup_directories()

    logger.info("=" * 80)
    logger.info("AGENTIC ADVERTISEMENT GENERATOR")
    logger.info("=" * 80)

    if not validate_inputs(args.images, args.script):
        logger.error("Input validation failed")
        return 1

    logger.info(f"Product: {args.product}")
    logger.info(f"Target Audience: {args.audience}")
    logger.info(f"Duration: {args.duration}s")
    logger.info(f"Images: {len(args.images)} provided")

    orchestrator = WorkflowOrchestrator()

    result = orchestrator.generate_advertisement(
        product_description=args.product,
        script=args.script,
        image_paths=args.images,
        target_audience=args.audience,
        target_duration=args.duration,
    )

    if result.get("success"):
        video_path = result.get("video_path")

        # Optionally copy final video to --output directory
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)

        final_path = video_path
        if video_path and os.path.exists(video_path):
            dst = output_dir / Path(video_path).name
            if str(dst) != str(video_path):
                shutil.copy2(video_path, dst)
                final_path = str(dst)

        logger.info("=" * 80)
        logger.info("GENERATION COMPLETED SUCCESSFULLY!")
        logger.info("=" * 80)
        logger.info(f"Video Path: {final_path}")
        logger.info(f"Duration: {result.get('duration')}s")
        logger.info(f"Quality Score: {result.get('quality_score')}/1.0")
        logger.info(f"Approved: {result.get('approved')}")
        logger.info(f"Processing Time: {result.get('processing_time_seconds'):.2f}s")

        return 0

    logger.error("=" * 80)
    logger.error("GENERATION FAILED")
    logger.error("=" * 80)
    logger.error(f"Error: {result.get('error')}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

