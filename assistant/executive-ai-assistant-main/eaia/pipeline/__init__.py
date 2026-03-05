"""
Nyx Outreach Pipeline — Modular Package
========================================
Architecture:
  pipeline/
    state.py        — OutreachState TypedDict (single source of truth)
    llm.py          — LLM caller: Cohere → OpenAI fallback
    enrichment/     — One file per data source
      apollo.py       — Apollo.io people/match
      tavily.py       — Tavily web search
      brightdata.py   — BrightData LinkedIn/SEC/strategy/competitors
    nodes/          — One file per pipeline node
      research.py     — Node 1: parallel enrichment
      distill.py      — Node 2: signal extraction + UNKNOWN gate
      score.py        — Node 3: informed scoring rubric
      write.py        — Node 4: two-pass email writer
      review.py       — Node 5: deterministic quality gate
      sync.py         — Node 6: CRM write-back
    graph.py        — LangGraph assembly + run_pipeline()
    sequence.py     — 21-day siege engine (/fire-sequence logic)
"""
