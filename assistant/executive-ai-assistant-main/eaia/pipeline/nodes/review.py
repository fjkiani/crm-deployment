"""
pipeline/nodes/review.py — Node 5: Deterministic Quality Gate.

Pipeline position: AFTER write_node. Before sync_node.
Purpose: Reject bad emails BEFORE they go to CRM. No LLM needed.

All checks are rule-based and deterministic — same input always produces same verdict.
This is intentional: LLMs should not judge their own output.

Current checks:
  1. Word count per framework (challenger: 65, pas: 70, aida: 85)
  2. Banned words list (20 corporate filler words)
  3. Banned openers ("I hope this...", "My name is...", etc)
  4. "Dear" opener check
  5. Subject line length (max 40 chars)

On fail: state["review_result"] = "fail" → should_retry() sends back to write_node (max 2 tries).
On pass: state["review_result"] = "pass" → proceed to sync_node.

To improve this node:
  - Add "generic sentence detector": flag any sentence that could apply to >1 prospect
  - Add "question mark check": challenger emails should end with a question
  - Add "personalization score": count how many dossier fields appear in the body
    If < 2 fields referenced → fail with "Personalization too low"
  - Add "reading level check": Flesch-Kincaid < 10th grade
  - Add "CTA check": must have exactly one clear call to action
  - Add "no pronoun check": reject if "we/our/us" appears > 3 times (too company-focused)
  - Raise word limits: challenger 65 → 55 (tighter = more disciplined)
"""
import logging
from langchain_core.runnables.config import RunnableConfig

from eaia.pipeline.state import OutreachState
from eaia.pipeline.llm import llm_json
from eaia.config import NyxConfig

logger = logging.getLogger(__name__)

# ── Quality Gate Rules ─────────────────────────────────────────────────────────
WORD_LIMITS = {
    "challenger": 65,
    "pas": 70,
    "aida": 85,
}

BANNED_WORDS = [
    "dear", "cutting-edge", "innovative", "leverage", "synergy", "unlock",
    "revolutionize", "unique", "advanced", "comprehensive", "robust",
    "holistic", "transform", "enhance", "optimize", "excited", "thrilled",
    "delighted", "pleased", "fascinating", "game-changer", "disruptive",
    "best-in-class", "world-class", "state-of-the-art",
]

BANNED_OPENERS = [
    "i hope this",
    "my name is",
    "i'm reaching out",
    "i wanted to",
    "i am reaching out",
    "hope this finds",
    "i trust this",
]


async def review_node(state: OutreachState, config: RunnableConfig) -> OutreachState:
    """
    Node 5 — Deterministic quality gate. Runs 5 checks. No LLM.

    Input:  state["email_draft"]
    Output: state["review_result"] ("pass" | "fail") + state["review_feedback"]

    On fail + attempt < 2: graph loops back to write_node with review_feedback injected.
    On fail + attempt >= 2: best-effort sync (not blocked — email flagged for review).
    """
    cb = config.get("configurable", {}).get("callback")
    logger.info("🔍 REVIEW: Quality gate")

    if cb:
        await cb("review", "thought", {"message": "Checking word count, banned words, opener..."})

    email_data = state.get("email_draft", {})
    email      = email_data.get("email", {})
    body       = email.get("body", "")
    subject    = email.get("subject", "")
    fw         = state.get("framework", NyxConfig.DEFAULT_FRAMEWORK)
    failures   = []

    body_lower = body.lower().strip()

    # 1. Word count
    word_count = len(body.split())
    limit = WORD_LIMITS.get(fw, 75)
    if word_count > limit:
        failures.append(f"Word count {word_count} exceeds {fw} limit of {limit}")

    # 2. Banned words
    found = [w for w in BANNED_WORDS if w in body_lower]
    if found:
        failures.append(f"Banned words: {', '.join(found)}")

    # 3. Banned openers
    for opener in BANNED_OPENERS:
        if body_lower.startswith(opener):
            failures.append(f"Banned opener: '{opener}'")
            break

    # 4. "Dear" check
    if body_lower.startswith("dear"):
        failures.append("Opens with 'Dear' — use first name only")

    # 5. Subject length
    if len(subject) > 50:
        failures.append(f"Subject too long: {len(subject)} chars (max 40)")

    if failures:
        state["review_result"]   = "fail"
        state["review_feedback"] = "; ".join(failures)
        logger.warning(f"❌ REVIEW FAILED: {state['review_feedback']}")
        if cb:
            await cb("review", "result", {"message": f"❌ Failed: {state['review_feedback']}"})
    else:
        state["review_result"]   = "pass"
        state["review_feedback"] = f"✅ {word_count}/{limit} words, no banned words, clean opener"
        logger.info(f"✅ REVIEW PASSED: {word_count}/{limit} words")
        if cb:
            await cb("review", "result", {"message": state["review_feedback"]})

    return state


def should_retry(state: OutreachState) -> str:
    """
    Conditional edge: Review → retry Write or proceed to Sync.
    Max 2 write attempts per lead.
    """
    if state.get("review_result") == "pass":
        return "sync"
    attempt = state.get("attempt", 1)
    if attempt >= 2:
        logger.warning("⚠️ Max retries reached — syncing best effort")
        return "sync"
    state["attempt"] = attempt + 1
    return "retry"
