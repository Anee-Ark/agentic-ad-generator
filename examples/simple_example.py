"""
Simple example of generating an advertisement
"""
import sys
import os

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.orchestrator.workflow_orchestrator import WorkflowOrchestrator


def run_example():
    """Run a simple example"""

    # Example inputs
    product_description = """
    EcoBottle: A revolutionary sustainable water bottle made from 100% recycled ocean plastic.
    Features: Temperature control (keeps cold 24h, hot 12h), leak-proof, dishwasher safe,
    comes in 5 colors, with every purchase we remove 1lb of plastic from the ocean.
    """

    script = """
    Tired of single-use plastic? Meet EcoBottle.
    Made from 100% recycled ocean plastic, it keeps your drinks cold for 24 hours.
    Every bottle sold removes a pound of plastic from our oceans.
    Stay hydrated. Stay sustainable. Get your EcoBottle today.
    """

    # Image paths (must exist)
    image_paths = [
        "data/input/product_shot.jpg",
        "data/input/lifestyle_beach.jpg",
        "data/input/closeup_bottle.jpg",
    ]

    # Validate image paths early (better DX)
    missing = [p for p in image_paths if not os.path.exists(p)]
    if missing:
        print("❌ Missing image files:")
        for p in missing:
            print(f"  - {p}")
        print("\nAdd placeholder images before running this example.")
        return

    # Initialize orchestrator
    orchestrator = WorkflowOrchestrator()

    print("Starting advertisement generation...")
    print("-" * 80)

    result = orchestrator.generate_advertisement(
        product_description=product_description,
        script=script,
        image_paths=image_paths,
        target_audience="Environmentally conscious millennials and Gen Z",
        target_duration=30,
    )

    print("\n" + "=" * 80)
    if result.get("success"):
        print("✅ SUCCESS!")
        print(f"Video created: {result['video_path']}")
        print(f"Quality score: {result['quality_score']}")
        print(f"Approved: {result['approved']}")
    else:
        print("❌ FAILED!")
        print(f"Error: {result.get('error')}")
    print("=" * 80)


if __name__ == "__main__":
    run_example()

