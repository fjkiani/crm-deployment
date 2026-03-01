
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

app = FastAPI(title="EAIA Agent Service (Farfalle Compatible)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://127.0.0.1:3000", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
