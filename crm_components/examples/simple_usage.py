"""
Simple Component Usage Example
"""

from pipelines.intelligence_pipeline import IntelligencePipeline
from pipelines.outreach_pipeline import OutreachPipeline
import json

def main():
    # Load configuration
    with open('config/main_config.json', 'r') as f:
        config = json.load(f)

    # Initialize pipelines
    intel_pipeline = IntelligencePipeline(config['components'])
    outreach_pipeline = OutreachPipeline(config['components'])

    # Define targets
    targets = [
        {"company": "3EDGE Asset Management"},
        {"company": "Sequoia Capital"}
    ]

    print("🎯 Gathering Intelligence...")
    intel_results = []
    for target in targets:
        result = intel_pipeline.execute(target)
        intel_results.append(result)
        print(f"✓ Processed {target['company']}")

    print("\n📧 Generating Outreach...")
    outreach_input = {
        "targets": intel_results,
        "campaign_config": {"id": "demo_campaign"}
    }

    outreach_results = outreach_pipeline.execute(outreach_input)
    print(f"✓ Generated {outreach_results['total_targets']} outreach campaigns")

    print("\n✅ Demo Complete!")

if __name__ == "__main__":
    main()