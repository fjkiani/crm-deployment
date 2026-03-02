
import os
import sys
import json
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# Ensure we can import from eaia
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")

from dotenv import load_dotenv
# Load secrets immediately
load_dotenv(os.path.join(os.path.dirname(__file__), ".secrets/.env"))

from eaia.main.draft_response import graph

import logging
logger = logging.getLogger(__name__)

app = FastAPI(title="EAIA Agent Service (Farfalle Compatible)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://localhost:3001", "http://localhost:3002",
        "http://127.0.0.1:3000", "http://127.0.0.1:3001",
        "http://crm.localhost:8000", "http://localhost:8000",
        "http://127.0.0.1:8000", "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Outreach Pipeline ────────────────────────────────────────────────────────
from eaia.outreach_graph import run_pipeline

class PipelineRequest(BaseModel):
    prospect_name: str
    company_name: str

@app.post("/pipeline")
async def pipeline_endpoint(request: PipelineRequest):
    """Autonomous outreach pipeline — streams node progress via SSE."""
    events_queue = asyncio.Queue()

    async def collect_progress(node: str, status: str, data: dict):
        await events_queue.put({"node": node, "status": status, **data})

    async def event_generator():
        yield f"data: {json.dumps({'event': 'pipeline-start', 'prospect': request.prospect_name, 'company': request.company_name})}\n\n"

        # Start the pipeline in the background
        pipeline_task = asyncio.create_task(run_pipeline(
            request.prospect_name,
            request.company_name,
            callback=collect_progress
        ))

        # Stream each node event as it arrives
        while not pipeline_task.done() or not events_queue.empty():
            try:
                evt = await asyncio.wait_for(events_queue.get(), timeout=0.1)
                evt_type = "node-thought" if evt.get("status") == "thought" else "node-complete"
                yield f"data: {json.dumps({'event': evt_type, 'data': evt})}\n\n"
            except asyncio.TimeoutError:
                continue

        # Final result
        result = pipeline_task.result()
        final = {
            "prospect_name": result.get("prospect_name"),
            "company_name": result.get("company_name"),
            "score": result.get("score"),
            "framework": result.get("framework"),
            "score_reasoning": result.get("score_reasoning"),
            "distilled_signals": result.get("distilled_signals"),
            "email_draft": result.get("email_draft"),
            "ab_subjects": result.get("ab_subjects"),
            "review_result": result.get("review_result"),
            "review_feedback": result.get("review_feedback"),
            "apollo_data": result.get("apollo_data"),
            "attempt": result.get("attempt"),
            "crm_synced": result.get("crm_synced", False),
            "crm_prospect_id": result.get("crm_prospect_id", ""),
            "email_sent": result.get("email_sent", False),
            "email_error": result.get("email_error", ""),
        }
        yield f"data: {json.dumps({'event': 'pipeline-complete', 'data': final})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

# ── CALL ENDPOINT (Phase 2: Vapi Voice Chain) ────────────────────────────
class CallRequest(BaseModel):
    phone_number: str
    prospect_name: str = ""
    company_name: str = ""
    crm_prospect_id: str = ""
    pipeline_context: dict = {}

@app.post("/call")
async def call_endpoint(request: CallRequest):
    """
    Place a Vapi call with pipeline intelligence as context.
    Creates a Vapi Call Log in CRM, then triggers the call.
    """
    import os
    from eaia.agents.zo import CRMClient

    # Build dossier from pipeline context
    ctx = request.pipeline_context
    signals = ctx.get("distilled_signals", {})
    email = ctx.get("email_draft", {}).get("email", {})
    calendar_context = ""  # will be filled in try block if Google Calendar token exists

    dossier = f"""
TARGET DOSSIER — {request.prospect_name} @ {request.company_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCORE: {ctx.get('score', 'N/A')}/100 ({ctx.get('framework', 'N/A')} framework)
KEY SIGNAL: {signals.get('specific_number', 'N/A')}
BLIND SPOT: {signals.get('blind_spot', 'N/A')[:200]}
EMAIL SUBJECT: {email.get('subject', 'N/A')}

OBJECTIVE: Reference the email we sent about "{email.get('subject', 'strategic insights')}".

IF THEY AGREE TO MEET:
- Mention available times from the calendar below
- Say: "I'll send a calendar invite right now"
- The booking system will auto-confirm

IF THEY SAY NO: ask who handles alt-data/quant strategy decisions
"""

    # Build system message for Vapi
    system_message = f"""You are Nyx, an AI Executive Assistant for Zeta Intelligence.
You are calling {request.prospect_name} at {request.company_name}.

{dossier}

RULES:
- Be professional, concise, and confident
- Never say "I'm an AI" — say "I'm calling on behalf of our research team"
- If voicemail: leave a 20-second message referencing the email subject
- If they answer: use the blind spot hook to open, then ask for 15 min
- If they say no: ask who handles alt-data/quant strategy decisions
"""

    try:
        # Fetch caller's calendar to give Vapi real availability
        calendar_context = ""
        calendar_email = os.getenv("CALENDAR_EMAIL", os.getenv("GMAIL_USER", ""))
        if calendar_email:
            try:
                from eaia.gmail import get_credentials, get_events_for_days, print_events
                from googleapiclient.discovery import build
                from datetime import datetime, timedelta
                secrets_dir = os.path.join(os.path.dirname(__file__), ".secrets")
                token_path = os.path.join(secrets_dir, "token.json")
                if os.path.exists(token_path):
                    creds = await get_credentials(calendar_email)
                    cal_service = build("calendar", "v3", credentials=creds)
                    today = datetime.utcnow().date()
                    next_days = [(today + timedelta(days=i)).strftime("%d-%m-%Y") for i in range(1, 4)]
                    import asyncio
                    # Build availability snippet for next 3 business days
                    avail_lines = []
                    for d in next_days:
                        day_obj = datetime.strptime(d, "%d-%m-%Y").date()
                        start = f"{day_obj.isoformat()}T00:00:00Z"
                        end = f"{day_obj.isoformat()}T23:59:59Z"
                        events_result = cal_service.events().list(
                            calendarId="primary", timeMin=start, timeMax=end,
                            singleEvents=True, orderBy="startTime"
                        ).execute()
                        events = events_result.get("items", [])
                        if events:
                            busy_times = ", ".join([e["start"].get("dateTime", "")[:16] for e in events[:3]])
                            avail_lines.append(f"{d}: BUSY at {busy_times}")
                        else:
                            avail_lines.append(f"{d}: OPEN")
                    calendar_context = "\nCALENDAR AVAILABILITY (next 3 days):\n" + "\n".join(avail_lines)
                    calendar_context += "\nWhen prospect agrees to meet: offer these open slots."
            except Exception as cal_e:
                logger.warning(f"Calendar context failed: {cal_e}")

        # ── Vapi REST API (direct — no MCP subprocess, instant) ─────────────
        import httpx
        vapi_key = os.getenv("VAPI_API_KEY", "53593b76-8c70-46e2-b01a-d2996afec5ba")
        phone_number_id = os.getenv("VAPI_PHONE_NUMBER_ID", "05559ed7-9762-4887-a690-2f8b3a8a7837")

        # Build final system message (with calendar context if available)
        full_system = system_message
        if calendar_context:
            full_system = system_message.rstrip() + "\n" + calendar_context

        first_message = (
            f"Hi, is this {request.prospect_name}? "
            f"I'm calling on behalf of Zeta Intelligence — we sent you a note about "
            f"\"{ctx.get('email_draft', {}).get('email', {}).get('subject', 'our research')}\". "
            f"Do you have 60 seconds?"
        )

        vapi_payload = {
            "phoneNumberId": phone_number_id,
            "customer": {"number": request.phone_number},
            "assistant": {
                "firstMessage": first_message,
                "model": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "system", "content": full_system}],
                    "temperature": 0.7,
                    "maxTokens": 250
                },
                "voice": {
                    "provider": "11labs",
                    "voiceId": "burt"
                },
                "endCallFunctionEnabled": True,
                "recordingEnabled": True,
                "maxDurationSeconds": 300,
                "silenceTimeoutSeconds": 30,
                "backgroundSound": "office"
            }
        }

        async with httpx.AsyncClient(timeout=20.0) as http:
            resp = await http.post(
                "https://api.vapi.ai/call",
                headers={
                    "Authorization": f"Bearer {vapi_key}",
                    "Content-Type": "application/json"
                },
                json=vapi_payload
            )
        
        if resp.status_code in (200, 201):
            vapi_data = resp.json()
            call_id = vapi_data.get("id", "")
            logger.info(f"📞 CALL: ✅ Vapi REST → {request.phone_number} (call_id={call_id})")

            # Update CRM status
            if request.crm_prospect_id:
                try:
                    import requests as req_sync
                    _c = CRMClient()
                    req_sync.put(
                        f"{_c.base_url}/api/resource/Lead Prospect/{request.crm_prospect_id}",
                        headers=_c.headers,
                        json={"outreach_status": "Call Scheduled"}
                    )
                except Exception:
                    pass

            return {
                "status": "call_initiated",
                "phone_number": request.phone_number,
                "prospect": request.prospect_name,
                "call_id": call_id,
                "vapi_status": vapi_data.get("status"),
                "vapi_result": str(vapi_data)[:400]
            }
        else:
            error_body = resp.text[:300]
            logger.error(f"📞 CALL: Vapi REST error {resp.status_code} — {error_body}")
            return {
                "status": "call_failed",
                "http_status": resp.status_code,
                "error": error_body,
                "phone_number": request.phone_number
            }

    except Exception as e:
        logger.error(f"Call failed: {e}")
        return {
            "status": "call_failed",
            "error": str(e),
            "phone_number": request.phone_number
        }



# Farfalle Request Model
class Message(BaseModel):
    role: str
    content: str
    
class FarfalleChatRequest(BaseModel):
    query: str
    history: List[Message] = []
    model: Optional[str] = "command-r-plus"
    pro_search: Optional[bool] = False
    thread_id: Optional[str] = None

@app.post("/chat")
async def chat_endpoint(request: FarfalleChatRequest):
    """
    Farfalle-compatible SSE Chat Endpoint.
    """
    
    async def event_generator():
        try:
            # 1. BEGIN_STREAM
            yield f"data: {json.dumps({'event': 'begin-stream', 'data': {'query': request.query}})}\n\n"
            
            # --- AGENT LOGIC ---
            
            # Convert history for Agent
            messages = [{"role": m.role, "content": m.content} for m in request.history[-5:]]
            messages.append({"role": "user", "content": request.query})
            
            initial_state = {
                "messages": messages,
                "email": {
                    "page_content": f"COMMAND: {request.query}\nCONTEXT: The user is interacting via a Chat Interface. Do NOT ask for clarification unless critical. You have permission to use all tools directly. EXECUTE IMMEDIATELY.",
                    "from_email": "Admin User",
                    "subject": "URGENT: EXECUTE COMMAND",
                    "to_email": "Nyx Agent"
                }
            }
            
            # Invoke Graph (for reasoning)
            final_state = await graph.ainvoke(initial_state)
            last_message = final_state["messages"][-1]
            content = last_message.content
            
            # Streaming the initial thought process
            # (We simulate streaming by chunking the static response for UX)
            words = content.split(" ")
            for word in words:
                chunk = word + " "
                yield f"data: {json.dumps({'event': 'text-chunk', 'data': {'text': chunk}})}\n\n"
                await asyncio.sleep(0.01) # fast typing
                
            # MANUAL TOOL EXECUTION
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                action_msg = "\n\n--- ⚡️ Agent Action ---\n"
                yield f"data: {json.dumps({'event': 'text-chunk', 'data': {'text': action_msg}})}\n\n"
                
                for tool_call in last_message.tool_calls:
                    name = tool_call.get('name')
                    args = tool_call.get('args')
                    
                    tool_output = ""
                    
                    if name == 'lead_hunter':
                        msg = f"Executing Skill: {name}...\n"
                        yield f"data: {json.dumps({'event': 'text-chunk', 'data': {'text': msg}})}\n\n"
                        # Import underlying async function to avoid asyncio.run() conflict
                        from eaia.skills.lead_hunter_tool import _async_lead_hunter
                        
                        try:
                            # Extract args safely
                            role = args.get('role') or "Executive"
                            industry = args.get('industry') or "Tech"
                            location = args.get('location') or "US"
                            limit = args.get('limit', 5)
                            
                            result = await _async_lead_hunter(role, industry, location, limit)
                            tool_output = f"{result}\n"
                        except Exception as tool_e:
                            tool_output = f"❌ Tool Execution Failed: {str(tool_e)}\n"

                    elif name == 'brightdata_web_search':
                        msg = f"Executing Skill: {name}...\n"
                        yield f"data: {json.dumps({'event': 'text-chunk', 'data': {'text': msg}})}\n\n"
                        from eaia.brightdata_tool import brightdata_web_search
                        try:
                            # brightdata_web_search expects 'query'
                            query = args.get('query')
                            if query:
                                # Use ainvoke which handles sync/async and threadpooling
                                result = await brightdata_web_search.ainvoke(query)
                                tool_output = f"{result}\n"
                            else:
                                tool_output = "❌ Missing query for brightdata_web_search.\n"
                        except Exception as tool_e:
                            tool_output = f"❌ Tool Execution Failed: {str(tool_e)}\n"

                    elif name == 'Question':
                         # If the agent wants to ask a question, we just display it.
                         question = args.get('content')
                         tool_output = f"❓ **Clarification Needed**: {question}\n"

                    elif name == 'ResponseEmailDraft':
                        # If the agent drafts an email, we show it
                        draft = args.get('content')
                        tool_output = f"📝 **Draft Response**:\n{draft}\n"

                    elif name == 'research_company':
                        msg = f"Executing Skill: {name}...\n"
                        yield f"data: {json.dumps({'event': 'text-chunk', 'data': {'text': msg}})}\n\n"
                        from eaia.research_tool import research_company
                        try:
                            company = args.get('company_name')
                            if company:
                                # Tool is sync, but we are in async def. 
                                # Ideally run in executor, but for now direct call (blocks event loop briefly)
                                result = research_company.invoke({"company_name": company})
                                tool_output = f"{result}\n"
                            else:
                                tool_output = "❌ Missing company_name for research_company.\n"
                        except Exception as tool_e:
                            tool_output = f"❌ Tool Execution Failed: {str(tool_e)}\n"

                    elif name == 'web_search':
                        msg = f"Executing Skill: {name}...\n"
                        yield f"data: {json.dumps({'event': 'text-chunk', 'data': {'text': msg}})}\n\n"
                        from eaia.research_tool import web_search
                        try:
                            query = args.get('query')
                            if query:
                                result = web_search.invoke({"query": query})
                                tool_output = f"{result}\n"
                            else:
                                tool_output = "❌ Missing query for web_search.\n"
                        except Exception as tool_e:
                            tool_output = f"❌ Tool Execution Failed: {str(tool_e)}\n"

                    elif name == 'voice_call':
                        msg = f"Executing Skill: {name}...\n"
                        yield f"data: {json.dumps({'event': 'text-chunk', 'data': {'text': msg}})}\n\n"
                        from eaia.skills.voice_tool import voice_call
                        try:
                            phone = args.get('phone_number')
                            objective = args.get('objective')
                            if phone and objective:
                                # Tool is sync
                                result = voice_call.invoke({"phone_number": phone, "objective": objective})
                                tool_output = f"{result}\n"
                            else:
                                tool_output = "❌ Missing phone_number or objective for voice_call.\n"
                        except Exception as tool_e:
                            tool_output = f"❌ Tool Execution Failed: {str(tool_e)}\n"
                    
                    elif name == 'score_lead':
                        msg = f"Executing Skill: {name}...\n"
                        yield f"data: {json.dumps({'event': 'text-chunk', 'data': {'text': msg}})}\n\n"
                        from eaia.skills.lead_scoring_tool import score_lead
                        try:
                            # Tool takes a string argument
                            lead_data_str = args.get('lead_data_str')
                            if not lead_data_str and isinstance(args, dict):
                                # Fallback if LLM passes args differently
                                lead_data_str = str(args)
                            
                            result = score_lead.invoke({"lead_data_str": lead_data_str})
                            tool_output = f"{result}\\n"
                        except Exception as tool_e:
                            tool_output = f"❌ Tool Execution Failed: {str(tool_e)}\\n"

                    elif name == 'vapi_mcp_call':
                        msg = f"Executing Skill: {name} (MCP)...\n"
                        yield f"data: {json.dumps({'event': 'text-chunk', 'data': {'text': msg}})}\n\n"
                        from eaia.skills.vapi_mcp_tool import vapi_mcp_call
                        try:
                            # Tool takes phone_number and objective
                            phone_number = args.get('phone_number')
                            objective = args.get('objective')
                            result = vapi_mcp_call.invoke({"phone_number": phone_number, "objective": objective})
                            # result is usually multiple lines
                            tool_output = f"{result}\n"
                        except Exception as tool_e:
                            tool_output = f"❌ Tool Execution Failed: {str(tool_e)}\n"

                    elif name == 'run_harvest_mission':
                        msg = "🚀 Launching Operation Harvest (The Revenue Army)...\n"
                        yield f"data: {json.dumps({'event': 'text-chunk', 'data': {'text': msg}})}\n\n"
                        from eaia.skills.harvest_tool import run_harvest_mission
                        try:
                            disease = args.get('target_disease')
                            # Tool returns a string summary directly
                            result = run_harvest_mission.invoke({"target_disease": disease})
                            tool_output = f"{result}\n"
                        except Exception as tool_e:
                            tool_output = f"❌ Harvest Failed: {str(tool_e)}\n"

                    elif name == 'distill_signals':
                        msg = "🔬 Distilling research signals...\n"
                        yield f"data: {json.dumps({'event': 'text-chunk', 'data': {'text': msg}})}\n\n"
                        from eaia.skills.signal_distiller import distill_signals
                        try:
                            raw_intel = args.get('raw_intel', '')
                            result = distill_signals.invoke({"raw_intel": raw_intel})
                            tool_output = f"{result}\n"
                        except Exception as tool_e:
                            tool_output = f"❌ Signal Distillation Failed: {str(tool_e)}\n"

                    elif name == 'write_challenger_email':
                        msg = "✍️ Two-pass email generation (Think → Write)...\n"
                        yield f"data: {json.dumps({'event': 'text-chunk', 'data': {'text': msg}})}\n\n"
                        from eaia.skills.challenger_email_writer import write_challenger_email
                        try:
                            result = write_challenger_email.invoke({
                                "prospect_name": args.get('prospect_name', ''),
                                "company_name": args.get('company_name', ''),
                                "distilled_signals_json": args.get('distilled_signals_json', '{}'),
                                "prospect_summary": args.get('prospect_summary', ''),
                                "framework_override": args.get('framework_override', '')
                            })
                            tool_output = f"{result}\n"
                        except Exception as tool_e:
                            tool_output = f"❌ Challenger Email Writer Failed: {str(tool_e)}\n"

                    else:
                        tool_output = f"⚠️ Skill '{name}' is not wired.\n"
                        
                    # Stream tool output
                    yield f"data: {json.dumps({'event': 'text-chunk', 'data': {'text': tool_output}})}\n\n"

            # 3. STREAM_END
            yield f"data: {json.dumps({'event': 'stream-end', 'data': {'thread_id': request.thread_id or 'new'}})}\n\n"
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            err_msg = str(e)
            yield f"data: {json.dumps({'event': 'error', 'data': {'detail': err_msg}})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/voice/initiate-call")
async def initiate_call_endpoint(phone: str, topic: str = "General Inquiry"):
    """Initiate an outbound voice call via Vapi (using voice_tool logic)"""
    from eaia.skills.voice_tool import voice_call
    
    # We use .invoke directly as it's a sync tool
    result = voice_call.invoke({"phone_number": phone, "objective": topic})
    
    if "Initiated" in result:
        # Extract ID roughly
        try:
            call_id = result.split("Call ID: ")[1].split("\n")[0]
        except:
            call_id = "vapi_unknown"
            
        return {
            "status": "success",
            "message": "Call initiated successfully via Vapi",
            "data": {
                "call_id": call_id,
                "provider": "vapi"
            }
        }
    else:
        raise HTTPException(status_code=500, detail=f"Vapi Call Failed: {result}")

@app.post("/voice/call-with-context")
async def call_with_context_endpoint(phone: str, company: str, contact_name: str = None):
    """Contextual call endpoint"""
    topic = f"Call regarding {company}"
    if contact_name:
        topic += f" with {contact_name}"
        
    return await initiate_call_endpoint(phone, topic)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Nyx Agent (Farfalle Mode)"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
