import asyncio
from typing import AsyncIterator, List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.constants import get_model_string
from backend.db.chat import save_turn_to_db
from backend.llm.base import BaseLLM, EveryLLM
from backend.prompts import CHAT_PROMPT, HISTORY_QUERY_REPHRASE
from backend.related_queries import generate_related_queries
from backend.schemas import (
    BeginStream,
    ChatRequest,
    ChatResponseEvent,
    FinalResponseStream,
    Message,
    RelatedQueriesStream,
    SearchResult,
    SearchResultStream,
    StreamEndStream,
    StreamEvent,
    TextChunkStream,
)
from backend.search.search_service import perform_search
from backend.utils import is_local_model
from backend.intel.services import build_intel_service_from_env


def rephrase_query_with_history(
    question: str, history: List[Message], llm: BaseLLM
) -> str:
    if not history:
        return question

    try:
        history_str = "\n".join(f"{msg.role}: {msg.content}" for msg in history)
        formatted_query = HISTORY_QUERY_REPHRASE.format(
            chat_history=history_str, question=question
        )
        question = llm.complete(formatted_query).text.replace('"', "")
        return question
    except Exception:
        raise HTTPException(
            status_code=500, detail="Model is at capacity. Please try again later."
        )


def format_context(search_results: List[SearchResult]) -> str:
    return "\n\n".join(
        [f"Citation {i+1}. {str(result)}" for i, result in enumerate(search_results)]
    )


async def stream_qa_objects(
    request: ChatRequest, session: Session
) -> AsyncIterator[ChatResponseEvent]:
    try:
        model_name = get_model_string(request.model)
        llm = EveryLLM(model=model_name)

        yield ChatResponseEvent(
            event=StreamEvent.BEGIN_STREAM,
            data=BeginStream(query=request.query),
        )

        query = rephrase_query_with_history(request.query, request.history, llm)

        # --- Minimal intent routing for intel enrichment ---
        INTEL_KEYWORDS = [
            "decision makers",
            "decision-makers",
            "executives",
            "ceo",
            "cio",
            "managing director",
            "investments",
            "portfolio",
            "holdings",
            "gaps",
            "opportunities",
            "partnerships",
        ]

        def should_route_to_intel(q: str) -> bool:
            lower_q = q.lower()
            return any(k in lower_q for k in INTEL_KEYWORDS)

        def extract_company_from_query(q: str) -> str | None:
            # Heuristic: look for " at <Company>" or title-cased token sequence at end
            lower = q.lower()
            if " at " in lower:
                try:
                    tail = q.split(" at ", 1)[1].strip()
                    # Strip trailing punctuation
                    tail = tail.strip(".,!? ")
                    # Take up to first 6 words as company candidate
                    parts = tail.split()
                    candidate = " ".join(parts[:6])
                    return candidate
                except Exception:
                    return None
            # Fallback: if the query starts with a company name then a comma
            if "," in q:
                head = q.split(",", 1)[0].strip()
                if any(ch.isupper() for ch in head):
                    return head
            return None

        if should_route_to_intel(query):
            company = extract_company_from_query(query)
            if company:
                service = build_intel_service_from_env()
                intel_result = service.analyze(company=company, questions=[query], domain=None, max_results=5)

                # Map first result's sources to SearchResult for UI parity
                combined_sources: list[SearchResult] = []
                full_response = ""
                for r in intel_result.get("results", []):
                    srcs = r.get("sources", []) or []
                    mapped = []
                    for s in srcs:
                        title = s.get("title") or "Source"
                        url = s.get("url") or ""
                        content = s.get("content") or s.get("raw_content") or ""
                        mapped.append(SearchResult(title=title, url=url, content=content))
                    if mapped:
                        yield ChatResponseEvent(
                            event=StreamEvent.SEARCH_RESULTS,
                            data=SearchResultStream(results=mapped, images=[]),
                        )
                        combined_sources.extend(mapped)
                    # Stream the answer as text chunks (single chunk for now)
                    ans = r.get("answer") or ""
                    if ans:
                        full_response += ans + "\n\n"
                        yield ChatResponseEvent(
                            event=StreamEvent.TEXT_CHUNK,
                            data=TextChunkStream(text=ans),
                        )

                # Persist turn
                thread_id = save_turn_to_db(
                    session=session,
                    thread_id=request.thread_id,
                    user_message=request.query,
                    assistant_message=full_response.strip() or "",
                    model=request.model,
                    search_results=combined_sources,
                    image_results=[],
                    related_queries=[],
                )

                yield ChatResponseEvent(
                    event=StreamEvent.FINAL_RESPONSE,
                    data=FinalResponseStream(message=(full_response.strip() or "")),
                )
                yield ChatResponseEvent(
                    event=StreamEvent.STREAM_END,
                    data=StreamEndStream(thread_id=thread_id),
                )
                return

        # --- Default path: existing search + LLM answer ---
        search_response = await perform_search(query)

        search_results = search_response.results
        images = search_response.images

        # Only create the task first if the model is not local
        related_queries_task = None
        if not is_local_model(request.model):
            related_queries_task = asyncio.create_task(
                generate_related_queries(query, search_results, llm)
            )

        yield ChatResponseEvent(
            event=StreamEvent.SEARCH_RESULTS,
            data=SearchResultStream(
                results=search_results,
                images=images,
            ),
        )

        fmt_qa_prompt = CHAT_PROMPT.format(
            my_context=format_context(search_results),
            my_query=query,
        )

        full_response = ""
        response_gen = await llm.astream(fmt_qa_prompt)
        async for completion in response_gen:
            full_response += completion.delta or ""
            yield ChatResponseEvent(
                event=StreamEvent.TEXT_CHUNK,
                data=TextChunkStream(text=completion.delta or ""),
            )

        related_queries = await (
            related_queries_task
            if related_queries_task
            else generate_related_queries(query, search_results, llm)
        )

        yield ChatResponseEvent(
            event=StreamEvent.RELATED_QUERIES,
            data=RelatedQueriesStream(related_queries=related_queries),
        )

        thread_id = save_turn_to_db(
            session=session,
            thread_id=request.thread_id,
            user_message=request.query,
            assistant_message=full_response,
            model=request.model,
            search_results=search_results,
            image_results=images,
            related_queries=related_queries,
        )

        yield ChatResponseEvent(
            event=StreamEvent.FINAL_RESPONSE,
            data=FinalResponseStream(message=full_response),
        )

        yield ChatResponseEvent(
            event=StreamEvent.STREAM_END,
            data=StreamEndStream(thread_id=thread_id),
        )

    except Exception as e:
        detail = str(e)
        raise HTTPException(status_code=500, detail=detail)
