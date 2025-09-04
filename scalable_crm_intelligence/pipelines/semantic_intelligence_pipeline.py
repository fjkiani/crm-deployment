"""
Semantic Intelligence Pipeline
Composable pipeline that uses injected TavilyClient, optional decomposer, optional synthesizer
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

from components.services.tavily_client import TavilyClient
from components.services.diffbot_client import DiffbotClient
from components.services.linkedin_client import LinkedInClient
from components.services.brightdata_client import BrightDataClient


@dataclass
class PipelineConfig:
    company: str
    focus_domains: List[str]
    max_results_per_query: int = 5
    exclude_domains: Optional[List[str]] = None
    custom_questions: Optional[List[str]] = None
    domain: Optional[str] = None


class SemanticIntelligencePipeline:
    """Composable pipeline for semantic intelligence using Tavily."""

    def __init__(
        self,
        tavily: TavilyClient,
        question_decomposer: Optional[Callable[[str], List[Dict[str, str]]]] = None,
        synthesizer: Optional[Callable[[str], str]] = None,
        diffbot: Optional[DiffbotClient] = None,
        linkedin: Optional[LinkedInClient] = None,
        brightdata: Optional[BrightDataClient] = None,
    ):
        self.tavily = tavily
        self.question_decomposer = question_decomposer
        self.synthesizer = synthesizer
        self.diffbot = diffbot
        self.linkedin = linkedin
        self.brightdata = brightdata

    def _default_questions(self, company: str, domain: str) -> List[Dict[str, str]]:
        prefix = f"in {domain} " if domain and domain != "general" else ""
        return [
            {"focus": "decision_makers", "question": f"Who are the key decision makers at {company} {prefix}?".strip()},
            {"focus": "investments", "question": f"What has {company} invested in recently {prefix}?".strip()},
            {"focus": "gaps", "question": f"What are {company}'s strategic gaps {prefix}?".strip()},
        ]

    def _build_questions(self, cfg: PipelineConfig) -> List[Dict[str, str]]:
        questions: List[Dict[str, str]] = []
        for domain in cfg.focus_domains:
            if self.question_decomposer is not None:
                base_q = (
                    f"Analyze {cfg.company} in {domain}: decision makers, recent investments, and strategic gaps"
                    if domain != "general"
                    else f"Analyze {cfg.company}: decision makers, recent investments, and strategic gaps"
                )
                try:
                    subs = self.question_decomposer(base_q) or []
                    for sub in subs:
                        questions.append(
                            {
                                "focus": sub.get("focus", "general"),
                                "question": sub.get("question", base_q),
                            }
                        )
                except Exception:
                    questions.extend(self._default_questions(cfg.company, domain))
            else:
                questions.extend(self._default_questions(cfg.company, domain))
        if cfg.custom_questions:
            for q in cfg.custom_questions:
                questions.append({"focus": "custom", "question": q})
        return questions

    def run(self, cfg: PipelineConfig) -> Dict[str, Any]:
        questions = self._build_questions(cfg)
        results: List[Dict[str, Any]] = []
        total_sources = 0

        for q in questions:
            res = self.tavily.search(
                q["question"],
                max_results=cfg.max_results_per_query,
                include_answer=True,
                include_raw_content=False,
                exclude_domains=cfg.exclude_domains,
            )
            answer = res.get("answer", "")
            sources = res.get("results", [])
            total_sources += len(sources)
            enriched: Dict[str, Any] = {
                "focus": q["focus"],
                "question": q["question"],
                "answer": answer,
                "sources": sources,
                "source_count": len(sources),
            }

            # Answer-quality guardrail: detect generic, definition-like answers without proper nouns
            is_generic = not any(token in (answer or "") for token in [
                cfg.company, "CEO", "Director", "Partner", "Investment", "Committee"
            ]) or (len((answer or "").split()) < 12)

            # If Diffbot is configured and answer looks generic, escalate: analyze top sources for people
            if self.diffbot and self.diffbot.is_configured() and sources:
                top_urls = [s.get("url") for s in sources[:3] if s.get("url")]
                extracted_people: List[Dict[str, Any]] = []
                for u in top_urls:
                    dj = self.diffbot.analyze_url(u)
                    ppl = self.diffbot.extract_people(dj)
                    if ppl:
                        extracted_people.extend(
                            {**p, "source_url": u} for p in ppl
                        )
                if extracted_people:
                    enriched["extracted_people"] = extracted_people
                    # If focus is decision makers and we found people, regenerate an answer summary from entities
                    if q["focus"] == "decision_makers" and is_generic:
                        names = ", ".join({p.get("name", "") for p in extracted_people if p.get("name")})
                        enriched["answer"] = f"Identified decision-makers: {names}. See sources for titles and details."
                    # Debug: always add Diffbot info to show it's working
                    enriched["diffbot_debug"] = f"Analyzed {len(top_urls)} URLs, found {len(extracted_people)} people"

            # LinkedIn enrichment for decision-makers when available
            if q["focus"] == "decision_makers" and self.linkedin and self.linkedin.is_configured():
                # Prefer explicit domain from config; else heuristic guess from sources
                domain_guess = cfg.domain
                if not domain_guess:
                    for s in sources:
                        url = s.get("url", "")
                        if url and "." in url:
                            try:
                                domain_guess = url.split("//", 1)[-1].split("/", 1)[0]
                            except Exception:
                                domain_guess = None
                            if domain_guess:
                                break
                li_company = self.linkedin.get_company_by_domain(domain_guess or "") if domain_guess else {}
                # Safely extract company id from various possible shapes
                li_data = (li_company.get("data") if isinstance(li_company, dict) else None) or {}
                li_company_obj = (li_company.get("company") if isinstance(li_company, dict) else None) or {}
                company_id = None
                if isinstance(li_company, dict):
                    company_id = li_company.get("companyId") or li_company.get("id")
                if not company_id and isinstance(li_data, dict):
                    company_id = li_data.get("companyId") or li_data.get("id")
                if not company_id and isinstance(li_company_obj, dict):
                    company_id = li_company_obj.get("id") or li_company_obj.get("companyId")
                linkedin_people: List[Dict[str, Any]] = []
                if company_id:
                    for page in range(1, 4):  # paginate first 3 pages
                        employees = self.linkedin.get_company_employees(company_id, page=page)
                        items = employees.get("employees") or employees.get("data") or []
                        for itm in items:
                            title = (itm.get("title") or itm.get("position") or "").lower()
                            name = itm.get("fullName") or itm.get("name") or ""
                            if not name or not title:
                                continue
                            senior = any(k in title for k in [
                                "managing partner","partner","founder","ceo","cio","md","managing director","director","head","vp","investment","portfolio","healthcare"
                            ])
                            if senior:
                                linkedin_people.append({
                                    "name": name,
                                    "title": itm.get("title") or itm.get("position"),
                                    "linkedin_url": itm.get("profileUrl") or itm.get("url"),
                                    "source_url": "linkedin_api",
                                    "confidence": 0.9
                                })
                                            if linkedin_people:
                            # Merge with Diffbot extractions if present
                            existing = enriched.get("extracted_people", [])
                            all_people = existing + linkedin_people
                            # Deduplicate
                            seen = set()
                            dedup: List[Dict[str, Any]] = []
                            for p in all_people:
                                key = (str(p.get("name", "")).lower(), str(p.get("title", "")).lower())
                                if key not in seen:
                                    seen.add(key)
                                    dedup.append(p)
                            enriched["extracted_people"] = dedup
                            if is_generic:
                                names = ", ".join({p.get("name", "") for p in dedup if p.get("name")})
                                enriched["answer"] = f"Identified decision-makers: {names}. See sources for titles and details."
                            # Debug: always add LinkedIn info to show it's working
                            enriched["linkedin_debug"] = f"Found {len(linkedin_people)} LinkedIn employees"

            # Bright Data recall for investments/gaps when available
            if self.brightdata and self.brightdata.is_configured() and q["focus"] in ("investments", "gaps"):
                bd_query = f"{cfg.company} {q['focus']}"
                bd = self.brightdata.search_news(bd_query, limit=5)
                bd_results = bd.get("results", [])
                if bd_results:
                    # Merge BD sources
                    for r in bd_results:
                        if r.get("url"):
                            enriched.setdefault("sources", []).append({
                                "title": r.get("title", ""),
                                "url": r.get("url", ""),
                                "content": r.get("content", ""),
                            })
                            total_sources += 1

            results.append(enriched)

        output: Dict[str, Any] = {
            "company": cfg.company,
            "focus_domains": cfg.focus_domains,
            "analysis_timestamp": datetime.now().isoformat(),
            "questions_analyzed": len(questions),
            "total_sources": total_sources,
            "results": results,
            "configuration": {
                "max_results_per_query": cfg.max_results_per_query,
                "exclude_domains": cfg.exclude_domains or [],
                "custom_questions_count": len(cfg.custom_questions or []),
            },
            "method": "semantic_pipeline_tavily_llm",
        }

        # Simple scoring (meeting-readiness): fit/access/need/timing
        score = 0
        # Fit: presence of focus domains
        score += min(len([d for d in cfg.focus_domains if d and d != "general"]) * 10, 30)
        # Access: decision-makers extracted
        dm_count = 0
        for r in results:
            if r.get("focus") == "decision_makers":
                dm_count += len(r.get("extracted_people", []))
        score += min(dm_count * 8, 25)
        # Need: gaps detected
        gap_count = 0
        for r in results:
            if r.get("focus") == "gaps":
                gap_count += max(1, r.get("source_count", 0)) if r.get("answer") else 0
        score += min(gap_count * 6, 30)
        # Timing: total sources as a weak proxy
        score += min(int(total_sources / 5) * 3, 15)
        output["meeting_readiness_score"] = min(score, 100)

        # Optional synthesis
        if self.synthesizer is not None:
            summary_items = [
                {
                    "focus": r["focus"],
                    "question": r["question"],
                    "answer": (r["answer"][:300] + "...") if len(r["answer"]) > 300 else r["answer"],
                    "sources": r["source_count"],
                }
                for r in results
            ]
            prompt = (
                f"Provide an executive synthesis for {cfg.company} covering decision makers, recent investments, and gaps.\n\n"
                f"INPUT:\n{summary_items}\n\nReturn actionable findings, next steps, and confidence."
            )
            try:
                synthesis_text = self.synthesizer(prompt)
            except Exception as e:
                synthesis_text = f"Synthesis failed: {e}"
            output["strategic_synthesis"] = synthesis_text

        return output


