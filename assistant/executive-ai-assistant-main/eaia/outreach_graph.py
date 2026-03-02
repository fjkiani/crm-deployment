"""
Outreach Pipeline — LangGraph StateGraph
Orchestrates 5 specialized nodes into an autonomous pipeline:
  Research → Distill → Score → Write → Review (with loop-back on fail)

Usage:
    from eaia.outreach_graph import run_pipeline
    result = await run_pipeline("Peter McManus", "3EDGE Asset Management")
"""
import os
import re
import json
import asyncio
import logging
import requests
from typing import TypedDict, Optional, List, Dict, Any, AsyncGenerator
from langchain_core.runnables.config import RunnableConfig

logger = logging.getLogger(__name__)


# ── STATE SCHEMA ─────────────────────────────────────────────────────────────
class OutreachState(TypedDict, total=False):
    prospect_name: str
    company_name: str
    raw_research: str
    apollo_data: dict
    distilled_signals: dict
    score: int
    score_reasoning: str
    score_angle: str
    framework: str
    email_draft: dict
    ab_subjects: list
    review_result: str
    review_feedback: str
    attempt: int
    error: str
    crm_synced: bool
    crm_prospect_id: str
    email_sent: bool
    email_error: str


# ── SHARED LLM CALLER (Cohere → OpenAI fallback) ───────────────────────────
def _llm_json(prompt: str) -> Dict[str, Any]:
    """Call LLM with JSON response. Tries Cohere first, falls back to OpenAI."""
    # ── Primary: Cohere ───────────────────────────────────────────────
    cohere_key = os.getenv("COHERE_API_KEY")
    if cohere_key:
        try:
            r = requests.post(
                'https://api.cohere.com/v2/chat',
                headers={'Authorization': f'Bearer {cohere_key}'},
                json={
                    'model': 'command-r-plus-08-2024',
                    'messages': [{'role': 'user', 'content': prompt}],
                    'response_format': {'type': 'json_object'}
                },
                timeout=45
            )
            r.raise_for_status()
            return json.loads(r.json()['message']['content'][0]['text'])
        except Exception as e:
            logger.warning(f"Cohere failed ({e}), falling back to OpenAI...")

    # ── Fallback: OpenAI ──────────────────────────────────────────────
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            r = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {openai_key}'},
                json={
                    'model': 'gpt-4o-mini',
                    'messages': [
                        {'role': 'system', 'content': 'You are a JSON-only assistant. Return ONLY valid JSON, no markdown.'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'response_format': {'type': 'json_object'}
                },
                timeout=30
            )
            r.raise_for_status()
            return json.loads(r.json()['choices'][0]['message']['content'])
        except Exception as e:
            logger.error(f"OpenAI fallback also failed: {e}")

    raise RuntimeError("No LLM available (both COHERE_API_KEY and OPENAI_API_KEY failed)")


# Keep backward compat alias
_cohere_json = _llm_json


# ═══════════════════════════════════════════════════════════════════════════
# NODE 1: RESEARCH (Tavily + Apollo in parallel)
# ═══════════════════════════════════════════════════════════════════════════
def _tavily_search(query: str, max_results: int = 5) -> List[Dict]:
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        return [{"url": "#", "content": "TAVILY_API_KEY not set"}]
    try:
        r = requests.post("https://api.tavily.com/search", json={
            "api_key": key, "query": query,
            "search_depth": "advanced", "max_results": max_results,
            "include_answer": True
        }, timeout=15)
        r.raise_for_status()
        data = r.json()
        results = []
        if data.get("answer"):
            results.append({"url": "tavily_answer", "content": data["answer"]})
        for res in data.get("results", []):
            results.append({"url": res.get("url"), "content": res.get("content", "")})
        return results
    except Exception as e:
        return [{"url": "#", "content": f"Tavily error: {e}"}]


def _apollo_match(name: str, org: str) -> Optional[Dict]:
    key = os.getenv("APOLLO_API_KEY")
    if not key:
        return None
    try:
        r = requests.post(
            "https://api.apollo.io/v1/people/match",
            headers={"Content-Type": "application/json", "X-Api-Key": key},
            json={"name": name, "organization_name": org, "reveal_personal_emails": True},
            timeout=10
        )
        if r.status_code == 200:
            person = r.json().get("person")
            if person:
                return {
                    "email": person.get("email"),
                    "title": person.get("title"),
                    "linkedin_url": person.get("linkedin_url"),
                    "organization": person.get("organization", {}).get("name"),
                    "city": person.get("city"),
                    "headline": person.get("headline"),
                }
    except Exception as e:
        logger.warning(f"Apollo match failed: {e}")
    return None


def _brightdata_linkedin(name: str, company: str) -> str:
    """Pull LinkedIn signals via BrightData Web Unlocker API."""
    key = os.getenv("BRIGHTDATA_API_KEY")
    if not key:
        return ""
    try:
        r = requests.post(
            "https://api.brightdata.com/request",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "zone": "web_unlocker1",
                "url": f"https://www.linkedin.com/search/results/people/?keywords={name.replace(' ','+')}&company_ids=&origin=SWITCH_SEARCH_VERTICAL&sid=gBJ",
                "format": "raw"
            },
            timeout=15
        )
        if r.status_code == 200:
            import re
            text = r.text
            headlines = re.findall(r'"headline":"([^"]{5,150})"', text)
            titles = re.findall(r'"title":\{"text":"([^"]{5,100})"', text)
            if headlines or titles:
                return f"\n\n[BRIGHTDATA LINKEDIN]\nHeadlines: {headlines[:3]}\nTitles: {titles[:3]}"
    except Exception as e:
        logger.debug(f"BrightData LinkedIn: {e}")
    return ""


async def research_node(state: OutreachState, config: RunnableConfig) -> OutreachState:
    """Node 1: Research prospect via Tavily + Apollo + BrightData LinkedIn (parallel)."""
    cb = config.get("configurable", {}).get("callback")
    name = state["prospect_name"]
    company = state["company_name"]
    logger.info(f"🔍 RESEARCH: {name} @ {company}")

    if cb: await cb("research", "thought", {"message": f"Searching Tavily + Apollo + LinkedIn for {name} at {company}..."})

    # Run all 3 sources in parallel
    import concurrent.futures
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        t_fut = loop.run_in_executor(executor, _tavily_search, f"{company} {name} investment strategy AUM portfolio")
        a_fut = loop.run_in_executor(executor, _apollo_match, name, company)
        l_fut = loop.run_in_executor(executor, _brightdata_linkedin, name, company)
        tavily_results, apollo, linkedin_raw = await asyncio.gather(t_fut, a_fut, l_fut)

    raw = "\n\n".join([f"[{r['url']}]\n{r['content'][:600]}" for r in tavily_results])

    if apollo:
        raw += f"\n\n[APOLLO CONTACT DATA]\nEmail: {apollo.get('email')}\nTitle: {apollo.get('title')}\nLinkedIn: {apollo.get('linkedin_url')}\nHeadline: {apollo.get('headline')}"

    if linkedin_raw:
        raw += linkedin_raw

    state["raw_research"] = raw
    state["apollo_data"] = apollo or {}
    return state


# ═══════════════════════════════════════════════════════════════════════════
# NODE 2: DISTILL (Citation Combiner)
# ═══════════════════════════════════════════════════════════════════════════
DISTILL_PROMPT = """You are an intelligence analyst for Zeta, a genomic data platform selling to quantitative investment firms.

Raw research intel on a prospect is below. Extract EXACTLY 3 citable signals — only facts with numbers, names, or dates.

RAW INTEL:
{raw_intel}

Return ONLY valid JSON:
{{
    "specific_number": "One hard number — AUM, fund size, headcount, revenue, or return %.",
    "recent_event": "One event from the last 12 months — fund launch, hire, acquisition, regulatory filing.",
    "strategic_detail": "One specific strategic detail — investment thesis, strategy name, sector focus.",
    "blind_spot": "One structural gap Zeta's genomic data could address. Be specific about WHY they are vulnerable.",
    "recommended_framework": "One of: challenger, pas, aida"
}}

Rules:
- Never fabricate. If unknown, write "UNKNOWN".
- blind_spot must connect to biological drug response signals predicting clinical trials, stock moves, sector rotation."""


async def distill_node(state: OutreachState, config: RunnableConfig) -> OutreachState:
    """Node 2: Distill raw research into structured signals."""
    cb = config.get("configurable", {}).get("callback")
    logger.info("🔬 DISTILL: Extracting signals")
    if cb: await cb("distill", "thought", {"message": "Citation combiner extracting 5 structured signals..."})
    prompt = DISTILL_PROMPT.format(raw_intel=state["raw_research"][:4000])
    try:
        signals = _cohere_json(prompt)
        required = ["specific_number", "recent_event", "strategic_detail", "blind_spot", "recommended_framework"]
        for k in required:
            if k not in signals:
                signals[k] = "UNKNOWN"
        fw = signals.get("recommended_framework", "challenger").lower().strip()
        if fw not in ("challenger", "pas", "aida"):
            fw = "challenger"
        signals["recommended_framework"] = fw
        state["distilled_signals"] = signals
    except Exception as e:
        logger.error(f"Distill failed: {e}")
        state["distilled_signals"] = {
            "specific_number": "UNKNOWN", "recent_event": "UNKNOWN",
            "strategic_detail": "UNKNOWN",
            "blind_spot": "Systematic macro-only models miss biological mechanism data.",
            "recommended_framework": "challenger"
        }
    return state


# ═══════════════════════════════════════════════════════════════════════════
# NODE 3: SCORE (Kill Score + Framework Auto-Select)
# ═══════════════════════════════════════════════════════════════════════════
SCORE_PROMPT = """You are a B2B sales intelligence analyst for Zeta, a genomic data analytics platform.
WHAT ZETA SELLS: Proprietary genomic datasets that quantify biological drug response signals.

ICP: Quantitative/systematic investment firms, AUM > $500M, biotech/healthcare equities, decision-makers (PMs, CIOs, Research Directors).

Prospect: {name} at {company}
Research: {research}
Signals: {signals}

Score 0-100:
- 80-100 (HOT): Quant/systematic fund + biotech exposure + decision-maker
- 50-79 (WARM): Matches 2-3 ICP criteria
- 0-49 (COLD): No quant mandate, no biotech relevance

Return JSON: {{"score": int, "reasoning": "...", "angle": "..."}}"""


async def score_node(state: OutreachState, config: RunnableConfig) -> OutreachState:
    """Node 3: Score the lead and auto-select framework."""
    cb = config.get("configurable", {}).get("callback")
    logger.info("📊 SCORE: Kill scoring")
    if cb: await cb("score", "thought", {"message": "Calculating Kill Score 0-100 and determining framework..."})
    signals = state.get("distilled_signals", {})
    try:
        prompt = SCORE_PROMPT.format(
            name=state["prospect_name"],
            company=state["company_name"],
            research=state["raw_research"][:2000],
            signals=json.dumps(signals, indent=2)
        )
        result = _cohere_json(prompt)
        score = int(result.get("score", 50))
        state["score"] = score
        state["score_reasoning"] = result.get("reasoning", "")
        state["score_angle"] = result.get("angle", "")

        # Auto-select framework based on score
        if score >= 70:
            state["framework"] = "challenger"
        elif score >= 40:
            state["framework"] = "pas"
        else:
            state["framework"] = "aida"

        # Override with distiller recommendation if score is in ambiguous range
        rec = signals.get("recommended_framework", "")
        if 45 <= score <= 75 and rec in ("challenger", "pas", "aida"):
            state["framework"] = rec

    except Exception as e:
        logger.error(f"Score failed: {e}")
        state["score"] = 50
        state["score_reasoning"] = f"Scoring error: {e}"
        state["score_angle"] = "Generic pitch"
        state["framework"] = signals.get("recommended_framework", "challenger")
    return state


# ═══════════════════════════════════════════════════════════════════════════
# NODE 4: WRITE (Two-Pass Email Generation)
# ═══════════════════════════════════════════════════════════════════════════
from eaia.skills.challenger_email_writer import FRAMEWORKS, _two_pass_generate, _generate_ab_subjects


async def write_node(state: OutreachState, config: RunnableConfig) -> OutreachState:
    """Node 4: Two-pass email generation (Think → Write)."""
    cb = config.get("configurable", {}).get("callback")
    fw = state.get("framework", "challenger")
    logger.info(f"✍️ WRITE: {fw.upper()} framework, attempt {state.get('attempt', 1)}")
    if cb: await cb("write", "thought", {"message": f"Writing {fw.upper()} email (attempt {state.get('attempt',1)})... Pass 1: Think. Pass 2: Write."})

    cohere_key = os.getenv("COHERE_API_KEY")
    if not cohere_key:
        state["email_draft"] = {"error": "No COHERE_API_KEY"}
        return state

    signals = state.get("distilled_signals", {})
    name = state["prospect_name"]
    company = state["company_name"]
    prospect_info = f"{name}, {state.get('apollo_data', {}).get('title', 'Unknown Title')} at {company}"

    # Incorporate review feedback into signals if this is a retry
    if state.get("review_feedback") and state.get("attempt", 1) > 1:
        signals["_review_feedback"] = state["review_feedback"]

    try:
        result = _two_pass_generate(
            fw, signals, prospect_info, name, company, cohere_key
        )
        state["email_draft"] = result

        # A/B subjects
        body = result.get("email", {}).get("body", "")
        ab = _generate_ab_subjects(body, name, company, cohere_key)
        state["ab_subjects"] = ab

    except Exception as e:
        logger.error(f"Write failed: {e}")
        state["email_draft"] = {"error": str(e)}
        state["ab_subjects"] = []

    return state


# ═══════════════════════════════════════════════════════════════════════════
# NODE 5: REVIEW (Deterministic Quality Gate)
# ═══════════════════════════════════════════════════════════════════════════
WORD_LIMITS = {"challenger": 65, "pas": 70, "aida": 85}
BANNED_WORDS = [
    "dear", "cutting-edge", "innovative", "leverage", "synergy", "unlock",
    "revolutionize", "unique", "advanced", "comprehensive", "robust",
    "holistic", "transform", "enhance", "optimize", "excited", "thrilled",
    "delighted", "pleased", "fascinating"
]
BANNED_OPENERS = ["i hope this", "my name is", "i'm reaching out", "i wanted to"]


async def review_node(state: OutreachState, config: RunnableConfig) -> OutreachState:
    """Node 5: Deterministic quality gate — no LLM needed."""
    cb = config.get("configurable", {}).get("callback")
    logger.info("🔍 REVIEW: Quality gate check")
    if cb: await cb("review", "thought", {"message": "Quality gate checking word count, banned words, and CTA..."})
    email_data = state.get("email_draft", {})
    email = email_data.get("email", {})
    fw = state.get("framework", "challenger")
    body = email.get("body", "")
    failures = []

    # 1. Word count
    word_count = len(body.split())
    limit = WORD_LIMITS.get(fw, 75)
    if word_count > limit:
        failures.append(f"Word count {word_count} exceeds {fw} limit of {limit}")

    # 2. Banned words
    body_lower = body.lower()
    found_banned = [w for w in BANNED_WORDS if w in body_lower]
    if found_banned:
        failures.append(f"Banned words found: {', '.join(found_banned)}")

    # 3. Banned openers
    for opener in BANNED_OPENERS:
        if body_lower.strip().startswith(opener):
            failures.append(f"Banned opener: '{opener}'")

    # 4. "Dear" check
    if body_lower.strip().startswith("dear"):
        failures.append("Opens with 'Dear' — must use first name only")

    # 5. Subject length
    subject = email.get("subject", "")
    if len(subject) > 50:
        failures.append(f"Subject too long: {len(subject)} chars (max 40)")

    if failures:
        state["review_result"] = "fail"
        state["review_feedback"] = "; ".join(failures)
        logger.warning(f"❌ REVIEW FAILED: {state['review_feedback']}")
    else:
        state["review_result"] = "pass"
        state["review_feedback"] = f"✅ Passed: {word_count} words, no banned words, clean opener"
        logger.info(f"✅ REVIEW PASSED: {word_count}/{limit} words")

    return state


# ═══════════════════════════════════════════════════════════════════════════
# CONDITIONAL EDGE: Review → Write (loop) or END
# ═══════════════════════════════════════════════════════════════════════════
def should_retry(state: OutreachState) -> str:
    """If review failed and attempts < 2, loop back to write. Otherwise sync to CRM."""
    if state.get("review_result") == "pass":
        return "sync"
    attempt = state.get("attempt", 1)
    if attempt >= 2:
        logger.warning("⚠️ Max retries reached. Syncing best effort.")
        return "sync"
    state["attempt"] = attempt + 1
    return "retry"


# ═══════════════════════════════════════════════════════════════════════════
# NODE 6: SYNC TO CRM (Write-back via Frappe API)
# ═══════════════════════════════════════════════════════════════════════════
from eaia.agents.zo import CRMClient

async def sync_node(state: OutreachState, config: RunnableConfig) -> OutreachState:
    """Node 6: Sync pipeline results to CRM Lead Prospect."""
    cb = config.get("configurable", {}).get("callback")
    logger.info("💾 SYNC: Writing to CRM")
    if cb: await cb("sync", "thought", {"message": "Syncing prospect + score + email to CRM..."})

    try:
        client = CRMClient()
        apollo = state.get("apollo_data", {})
        signals = state.get("distilled_signals", {})
        email_draft = state.get("email_draft", {})
        email = email_draft.get("email", {})

        prospect_data = {
            "pi_name": state["prospect_name"],
            "pi_email": apollo.get("email") or "",
            "institution": state["company_name"],
            "source": "Nyx Pipeline",
            "cancer_type": "General",
            "lead_score": state.get("score", 0),
            "tier": "Tier 1" if state.get("score", 0) > 75 else "Tier 2" if state.get("score", 0) > 40 else "Tier 3",
            "notes": json.dumps({
                "framework": state.get("framework"),
                "score_reasoning": state.get("score_reasoning", "")[:500],
                "signals": signals,
                "email_subject": email.get("subject", ""),
                "email_body": email.get("body", ""),
                "apollo_title": apollo.get("title", ""),
                "apollo_linkedin": apollo.get("linkedin_url", ""),
                "review_result": state.get("review_result"),
                "ab_subjects": state.get("ab_subjects", []),
            }, indent=2)
        }

        prospect_id = client.upsert_prospect(prospect_data)
        state["crm_synced"] = bool(prospect_id)
        state["crm_prospect_id"] = prospect_id or ""
        logger.info(f"💾 SYNC: {'✅ Saved' if prospect_id else '❌ Failed'} — {prospect_id}")

        # ── Auto-enroll in outreach sequence (Day 1 = email already queued via send_email_node) ──
        if prospect_id:
            try:
                import requests as _req
                enroll_r = _req.post(
                    f"{client.base_url}/api/method/crm.api.sequence_manager.enroll_prospect",
                    headers=client.headers,
                    json={"prospect_id": prospect_id, "sequence_name": "Nyx Default"},
                    timeout=5
                )
                enroll_data = enroll_r.json().get("message", {})
                if enroll_data.get("success"):
                    logger.info(f"📅 SEQUENCE: Enrolled {prospect_id} — next step: {enroll_data.get('next_step')} on {enroll_data.get('next_step_date')}")
                else:
                    logger.debug(f"Sequence enroll skipped: {enroll_data.get('error', 'unknown')}")
            except Exception as seq_e:
                logger.debug(f"Sequence enroll failed (non-fatal): {seq_e}")

    except Exception as e:
        logger.error(f"💾 SYNC ERROR: {e}")
        state["crm_synced"] = False
        state["crm_prospect_id"] = ""
        state["error"] = str(e)

    return state



# ═══════════════════════════════════════════════════════════════════════════
# NODE 7: SEND EMAIL (Gmail API → SMTP fallback)
# ═══════════════════════════════════════════════════════════════════════════
async def send_email_node(state: OutreachState, config: RunnableConfig) -> OutreachState:
    """Node 7: Actually fire the email via Gmail API or SMTP."""
    cb = config.get("configurable", {}).get("callback")
    logger.info("📧 SEND: Firing email")
    if cb: await cb("send", "thought", {"message": "Sending email to prospect..."})

    apollo = state.get("apollo_data", {})
    to_email = apollo.get("email")
    email_draft = state.get("email_draft", {})
    email_data = email_draft.get("email", {})
    subject = email_data.get("subject", "")
    body = email_data.get("body", "")
    ps = email_data.get("ps", "")
    full_body = body + (f"\n\nPS: {ps}" if ps else "")

    if not to_email:
        logger.warning("📧 SEND: No prospect email — skipping")
        state["email_sent"] = False
        state["email_error"] = "No prospect email (Apollo returned no email)"
        return state

    # ── Try Gmail API ─────────────────────────────────────────────────────
    secrets_dir = os.path.join(os.path.dirname(__file__), ".secrets")
    token_path = os.path.join(secrets_dir, "token.json")
    gmail_user = os.getenv("GMAIL_USER", "")

    if os.path.exists(token_path) and gmail_user:
        try:
            from eaia.gmail import get_credentials
            from googleapiclient.discovery import build
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            import base64
            import email as emaillib
            creds = await get_credentials(gmail_user)
            service = build("gmail", "v1", credentials=creds)
            msg = MIMEMultipart()
            msg["To"] = to_email
            msg["From"] = gmail_user
            msg["Subject"] = subject
            msg["Message-ID"] = emaillib.utils.make_msgid()
            msg.attach(MIMEText(full_body, "plain"))
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
            state["email_sent"] = True
            state["email_error"] = ""
            logger.info(f"📧 SEND: ✅ Gmail API → {to_email} (id={result.get('id')})")
            if state.get("crm_prospect_id"):
                try:
                    import requests as _req
                    from eaia.agents.zo import CRMClient
                    _c = CRMClient()
                    _req.put(f"{_c.base_url}/api/resource/Lead Prospect/{state['crm_prospect_id']}",
                             headers=_c.headers, json={"outreach_status": "Email Sent"})
                except Exception:
                    pass
            return state
        except Exception as e:
            logger.warning(f"Gmail API failed: {e} → trying SMTP...")

    # ── SMTP fallback ─────────────────────────────────────────────────────
    smtp_user = os.getenv("GMAIL_USER", os.getenv("SMTP_USER", ""))
    smtp_pass = os.getenv("GMAIL_APP_PASSWORD", os.getenv("SMTP_PASS", ""))
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    if smtp_user and smtp_pass:
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            msg = MIMEMultipart()
            msg["From"] = smtp_user
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(full_body, "plain"))
            with smtplib.SMTP(smtp_host, smtp_port) as s:
                s.starttls()
                s.login(smtp_user, smtp_pass)
                s.sendmail(smtp_user, [to_email], msg.as_string())
            state["email_sent"] = True
            state["email_error"] = ""
            logger.info(f"📧 SEND: ✅ SMTP → {to_email}")
            if state.get("crm_prospect_id"):
                try:
                    import requests as _req
                    from eaia.agents.zo import CRMClient
                    _c = CRMClient()
                    _req.put(f"{_c.base_url}/api/resource/Lead Prospect/{state['crm_prospect_id']}",
                             headers=_c.headers, json={"outreach_status": "Email Sent"})
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"📧 SMTP FAILED: {e}")
            state["email_sent"] = False
            state["email_error"] = str(e)
    else:
        logger.warning("📧 SEND: No credentials. Set GMAIL_USER + GMAIL_APP_PASSWORD in .secrets/.env")
        state["email_sent"] = False
        state["email_error"] = "No send credentials configured"

    return state


# ═══════════════════════════════════════════════════════════════════════════
# GRAPH ASSEMBLY
# ═══════════════════════════════════════════════════════════════════════════
try:
    from langgraph.graph import StateGraph, END

    def build_graph():
        graph = StateGraph(OutreachState)

        graph.add_node("research", research_node)
        graph.add_node("distill", distill_node)
        graph.add_node("score", score_node)
        graph.add_node("write", write_node)
        graph.add_node("review", review_node)
        graph.add_node("sync", sync_node)
        graph.add_node("send", send_email_node)

        graph.set_entry_point("research")
        graph.add_edge("research", "distill")
        graph.add_edge("distill", "score")
        graph.add_edge("score", "write")
        graph.add_edge("write", "review")
        graph.add_edge("sync", "send")
        graph.add_edge("send", END)

        graph.add_conditional_edges(
            "review",
            should_retry,
            {"retry": "write", "sync": "sync"}
        )

        return graph.compile()

    PIPELINE = build_graph()
    logger.info("✅ Outreach pipeline graph compiled")

except ImportError:
    PIPELINE = None
    logger.warning("⚠️ langgraph not available — pipeline will run sequentially")


# ═══════════════════════════════════════════════════════════════════════════
# RUNNER (with SSE progress events)
# ═══════════════════════════════════════════════════════════════════════════
async def run_pipeline(
    prospect_name: str,
    company_name: str,
    callback=None
) -> Dict[str, Any]:
    """
    Run the full outreach pipeline.
    
    Args:
        prospect_name: Full name of the prospect
        company_name: Company name
        callback: Optional async function called with (node_name, status, data) for progress
    
    Returns:
        Final state dict with all pipeline outputs
    """
    initial_state: OutreachState = {
        "prospect_name": prospect_name,
        "company_name": company_name,
        "raw_research": "",
        "apollo_data": {},
        "distilled_signals": {},
        "score": 0,
        "score_reasoning": "",
        "score_angle": "",
        "framework": "",
        "email_draft": {},
        "ab_subjects": [],
        "review_result": "",
        "review_feedback": "",
        "attempt": 1,
        "error": "",
        "crm_synced": False,
        "crm_prospect_id": ""
    }

    if PIPELINE:
        # Use LangGraph compiled pipeline
        if callback:
            await callback("pipeline", "running", {"message": "Starting autonomous pipeline..."})

        # Run through graph — langgraph handles the edges
        final_state = None
        config = {"configurable": {"callback": callback}}
        async for event in PIPELINE.astream(initial_state, config):
            for node_name, node_state in event.items():
                if callback:
                    # Build progress payload
                    progress = {"node": node_name}
                    if node_name == "research":
                        progress["tavily_results"] = len(node_state.get("raw_research", "").split("["))
                        progress["apollo_found"] = bool(node_state.get("apollo_data"))
                    elif node_name == "distill":
                        progress["signals"] = node_state.get("distilled_signals", {})
                    elif node_name == "score":
                        progress["score"] = node_state.get("score", 0)
                        progress["framework"] = node_state.get("framework", "")
                        progress["reasoning"] = node_state.get("score_reasoning", "")
                    elif node_name == "write":
                        progress["email"] = node_state.get("email_draft", {}).get("email", {})
                        progress["ab_subjects"] = node_state.get("ab_subjects", [])
                    elif node_name == "review":
                        progress["result"] = node_state.get("review_result", "")
                        progress["feedback"] = node_state.get("review_feedback", "")

                    await callback(node_name, "done", progress)
                final_state = node_state

        return final_state or initial_state

    else:
        # Fallback: run nodes sequentially without langgraph
        nodes = [
            ("research", research_node),
            ("distill", distill_node),
            ("score", score_node),
            ("write", write_node),
            ("review", review_node),
            ("sync", sync_node),
        ]
        config = {"configurable": {"callback": callback}}
        state = initial_state
        for node_name, node_fn in nodes:
            if callback:
                await callback(node_name, "running", {})
            state = await node_fn(state, config)
            if callback:
                await callback(node_name, "done", {"state": "complete"})

            # Handle review retry
            if node_name == "review" and state.get("review_result") == "fail" and state.get("attempt", 1) < 2:
                state["attempt"] = state.get("attempt", 1) + 1
                if callback:
                    await callback("write", "running", {"retry": True})
                state = await write_node(state, config)
                if callback:
                    await callback("write", "done", {"retry": True})
                state = await review_node(state, config)
                if callback:
                    await callback("review", "done", {"retry": True})

        return state
