#!/usr/bin/env python3
"""
Dynamic Semantic Intelligence (thin wrapper)
Use the CLI: bin/semantic_intel.py for full control.
"""

import os
import json
from datetime import datetime

from components.services.tavily_client import TavilyClient
from pipelines.semantic_intelligence_pipeline import SemanticIntelligencePipeline, PipelineConfig


def main():
    company = os.getenv("COMPANY", "Abbey Capital")
    tavily_key = os.getenv("TAVILY_API_KEY")
    if not tavily_key:
        raise SystemExit("TAVILY_API_KEY is required. Prefer using bin/semantic_intel.py")

    tavily = TavilyClient(api_key=tavily_key)
    pipeline = SemanticIntelligencePipeline(tavily=tavily)

    cfg = PipelineConfig(
        company=company,
        focus_domains=os.getenv("DOMAINS", "general").split(","),
        max_results_per_query=int(os.getenv("MAX_RESULTS", "5")),
        exclude_domains=os.getenv("EXCLUDE", "wikipedia.org,dictionary.com,thefreedictionary.com").split(","),
        custom_questions=[],
    )

    result = pipeline.run(cfg)
    out_path = f"{company.lower().replace(' ', '_')}_semantic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Output: {out_path}")


if __name__ == "__main__":
    main()
