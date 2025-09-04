#!/usr/bin/env python3
"""
Semantic Intelligence CLI
Wire Tavily client + optional Gemini synthesizer + optional decomposer
"""

import os
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any
import sys

# Ensure project root is on sys.path for package imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Load .env.local if present
try:
    from components.services.env_loader import load_env_file
    load_env_file(os.path.join(PROJECT_ROOT, ".env.local"))
except Exception:
    pass

from components.services.tavily_client import TavilyClient
from components.services.gemini_synthesizer import GeminiSynthesizer
from pipelines.semantic_intelligence_pipeline import SemanticIntelligencePipeline, PipelineConfig

try:
    # Optional import: existing decomposer component
    from components.llm_integration.question_decomposer import QuestionDecomposer
    from components.llm_integration.llm_client import UnifiedLLMClient, LLMConfig
except Exception:
    QuestionDecomposer = None  # type: ignore
    UnifiedLLMClient = None  # type: ignore
    LLMConfig = None  # type: ignore


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Semantic intelligence via Tavily")
    p.add_argument("--company", required=True, help="Target company name")
    p.add_argument("--domains", nargs="*", default=["general"], help="Focus domains (e.g., healthcare fintech)")
    p.add_argument("--question", action="append", help="Custom question (can repeat)")
    p.add_argument("--max-results", type=int, default=5, help="Max results per query")
    p.add_argument("--exclude-domain", action="append", help="Domain to exclude (can repeat)")
    p.add_argument("--domain", default=None, help="Explicit company domain (e.g., abbeycapital.com)")
    p.add_argument("--enable-linkedin", action="store_true", help="Enable LinkedIn enrichment")
    p.add_argument("--enable-diffbot", action="store_true", help="Enable Diffbot enrichment")
    p.add_argument("--enable-brightdata", action="store_true", help="Enable Bright Data recall")
    p.add_argument("--brightdata-url", default=None, help="Bright Data base URL")
    p.add_argument("--brightdata-token", default=None, help="Bright Data token (or set env)")
    p.add_argument("--no-synthesis", action="store_true", help="Skip Gemini synthesis")
    p.add_argument("--out", default=None, help="Output JSON file path")
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        raise SystemExit("TAVILY_API_KEY is required in environment")

    tavily = TavilyClient(api_key=tavily_api_key)

    # Optional decomposer
    decomposer_callable = None
    if QuestionDecomposer is not None and UnifiedLLMClient is not None and LLMConfig is not None and os.getenv("GEMINI_API_KEY"):
        # Use lightweight Gemini-backed decomposer if available
        llm = UnifiedLLMClient(LLMConfig(primary_provider="gemini", gemini_api_key=os.getenv("GEMINI_API_KEY")))
        qd = QuestionDecomposer(llm)
        decomposer_callable = lambda q: qd.decompose_question(q).get("sub_questions", [])  # type: ignore

    # Optional synthesis
    synthesizer_fn = None
    if not args.no_synthesis and os.getenv("GEMINI_API_KEY"):
        gem = GeminiSynthesizer(api_key=os.getenv("GEMINI_API_KEY"))
        synthesizer_fn = lambda prompt: gem.synthesize(prompt)

    # Optional providers
    diffbot = None
    if args.enable_diffbot and os.getenv("DIFFBOT_TOKEN"):
        from components.services.diffbot_client import DiffbotClient
        diffbot = DiffbotClient(token=os.getenv("DIFFBOT_TOKEN"))

    linkedin = None
    if args.enable_linkedin and os.getenv("LINKEDIN_RAPIDAPI_KEY"):
        from components.services.linkedin_client import LinkedInClient
        linkedin = LinkedInClient(api_key=os.getenv("LINKEDIN_RAPIDAPI_KEY"))

    # Optional Bright Data
    brightdata = None
    if args.enable_brightdata:
        from components.services.brightdata_client import BrightDataClient
        bd_url = args.brightdata_url or os.getenv("BRIGHTDATA_URL")
        bd_token = args.brightdata_token or os.getenv("BRIGHTDATA_TOKEN")
        if bd_url and bd_token:
            brightdata = BrightDataClient(base_url=bd_url, api_token=bd_token)

    pipeline = SemanticIntelligencePipeline(
        tavily=tavily,
        question_decomposer=decomposer_callable,
        synthesizer=synthesizer_fn,
        diffbot=diffbot,
        linkedin=linkedin,
        brightdata=brightdata,
    )

    cfg = PipelineConfig(
        company=args.company,
        focus_domains=args.domains,
        max_results_per_query=args.max_results,
        exclude_domains=args.exclude_domain,
        custom_questions=args.question or [],
        domain=args.domain,
    )

    result = pipeline.run(cfg)

    # Save
    out_path = args.out or f"{args.company.lower().replace(' ', '_')}_semantic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    # Print concise summary
    print(f"\n✅ Completed semantic intelligence for: {args.company}")
    print(f"   Domains: {', '.join(args.domains)} | Questions: {len(result['results'])} | Sources: {result['total_sources']}")
    if 'strategic_synthesis' in result:
        preview = result['strategic_synthesis'][:300].replace('\n', ' ')
        print(f"   Synthesis: {preview}...")
    print(f"   Output: {out_path}")


if __name__ == "__main__":
    main()


