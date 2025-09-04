---
alwaysApply: true
---
instructions
During you interaction with the user, if you find anything reusable in this project (e.g. version of a library, model name), especially about a fix to a mistake you made or a correction you received, you should take note in the Lessons section in the .cursorrules file so you will not make the same mistake again.

You should also use the .cursorrules file as a scratchpad to organize your thoughts. Especially when you receive a new task, you should first review the content of the scratchpad, clear old different task if necessary, first explain the task, and plan the steps you need to take to complete the task. You can use todo markers to indicate the progress, e.g. [X] Task 1 [ ] Task 2

Also update the progress of the task in the Scratchpad when you finish a subtask. Especially when you finished a milestone, it will help to improve your depth of task accomplishment to use the scratchpad to reflect and plan. The goal is to help you maintain a big picture as well as the progress of the task. Always refer to the Scratchpad when you plan the next step.

Tools
Note all the tools are in python. So in the case you need to do batch processing, you can always consult the python files and write your own script.

Screenshot Verification
The screenshot verification workflow allows you to capture screenshots of web pages and verify their appearance using LLMs. The following tools are available:

Screenshot Capture:
venv/bin/python tools/screenshot_utils.py URL [--output OUTPUT] [--width WIDTH] [--height HEIGHT]
LLM Verification with Images:
venv/bin/python tools/llm_api.py --prompt "Your verification question" --provider {openai|anthropic} --image path/to/screenshot.png
Example workflow:

from screenshot_utils import take_screenshot_sync
from llm_api import query_llm

# Take a screenshot
screenshot_path = take_screenshot_sync('https://example.com', 'screenshot.png')

# Verify with LLM
response = query_llm(
    "What is the background color and title of this webpage?",
    provider="openai",  # or "anthropic"
    image_path=screenshot_path
)
print(response)
LLM
You always have an LLM at your side to help you with the task. For simple tasks, you could invoke the LLM by running the following command:

venv/bin/python ./tools/llm_api.py --prompt "What is the capital of France?" --provider "anthropic"
The LLM API supports multiple providers:

OpenAI (default, model: gpt-4o)
Azure OpenAI (model: configured via AZURE_OPENAI_MODEL_DEPLOYMENT in .env file, defaults to gpt-4o-ms)
DeepSeek (model: deepseek-chat)
Anthropic (model: claude-3-sonnet-20240229)
Gemini (model: gemini-1.5-pro)
Local LLM (model: Qwen/Qwen2.5-32B-Instruct-AWQ)
But usually it's a better idea to check the content of the file and use the APIs in the tools/llm_api.py file to invoke the LLM if needed.

Web browser
You could use the tools/web_scraper.py file to scrape the web.

venv/bin/python ./tools/web_scraper.py --max-concurrent 3 URL1 URL2 URL3
This will output the content of the web pages.

Search engine
You could use the tools/search_engine.py file to search the web.

venv/bin/python ./tools/search_engine.py "your search keywords"
This will output the search results in the following format:

URL: https://example.com
Title: This is the title of the search result
Snippet: This is a snippet of the search result
If needed, you can further use the web_scraper.py file to scrape the web page content.

Cursor learned
=======


Scratchpad
==========

# Current Task: Implement Intelligent Question-Driven CRM System

## Task Analysis
Transform the current data-dump CRM intelligence system into an intelligent business advisor that answers specific questions with actionable insights.

**Problem**: Current system produces 12,080 lines of redundant data instead of answering specific business questions
**Goal**: Create specialist agents with LLM integration that provide structured, actionable responses

## Implementation Plan
Based on existing scalable_crm_intelligence/ architecture, we need to:

### Phase 1: Foundation (Current Focus)
- [X] Analyze existing architecture strengths/weaknesses
- [X] Design intelligent agent architecture plan
- [ ] Implement LLM integration layer
- [ ] Create question decomposition engine
- [ ] Build response synthesis framework

### What to Reuse from Existing Architecture:
✅ Core interfaces and base classes (core/interfaces/, core/base/)
✅ Configuration management system (config/)
✅ Testing framework (tests/)
✅ API structure (api/)
✅ Orchestration foundation (orchestration/)

### What to Replace/Enhance:
❌ Generic intelligence components → Specialist agents
❌ Data dump outputs → Structured question responses
❌ Manual orchestration → LLM-driven coordination
❌ Static workflows → Dynamic question-driven workflows

### Implementation Strategy:
1. Build on existing scalable_crm_intelligence/ foundation
2. Add LLM integration components
3. Convert existing components to specialist agents
4. Implement question-driven workflows
5. Create new response formats

## Next Steps:
1. [X] Create LLM integration components
2. [X] Implement question decomposition engine
3. [X] Build specialist agent framework
4. [X] Create demo with Abbey Capital example question
5. [ ] Test the implementation
6. [ ] Add Investment Intelligence Agent
7. [ ] Add Gap Analysis Agent
8. [ ] Integrate with CLI interface

## Progress Update:
✅ Completed Phase 1 Foundation:
- LLM integration layer with OpenAI/Anthropic support
- Question decomposition engine with intelligent routing
- Response synthesis framework with structured outputs
- Specialist agent base framework
- Executive Intelligence Agent implementation
- Intelligent Q&A workflow orchestrator
- Demo application with Abbey Capital example

✅ Phase 1 COMPLETE! Successfully built and demonstrated intelligent question-driven system.

## Demo Results:
🎯 Question: "For Abbey Capital, find healthcare decision makers and recent investments"
✅ Result: Specific contacts, investment details, strategic gaps, action plan
📊 Transformation: 12,080 lines → Actionable intelligence in 30 seconds

## Architecture Delivered:
- LLM integration layer (OpenAI/Anthropic with fallback)
- Question decomposition engine  
- Response synthesis framework
- Specialist agent framework
- Executive Intelligence Agent
- Intelligent Q&A workflow orchestrator
- Complete demo system

## Testing Real System:
- [X] User provided Tavily API key: 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
- [X] User provided Gemini API key: AIzaSyDmPm3J2yqzJD1nXvd_5-8i6TX6rygwZ0Y
- [X] Configure system for real API testing
- [X] Test Abbey Capital question with live data
- [X] Validate real intelligence gathering

## Real API Test Results:
✅ APIs Working: Gemini LLM + Tavily Intelligence
✅ Question Decomposition: 3 targeted sub-questions generated
✅ Intelligence Gathering: 9 sources searched across 3 focus areas
✅ Response Synthesis: Actionable recommendations generated
⏱️ Processing Time: 28.76 seconds (vs. hours of manual analysis)
📊 Output: Structured intelligence with next steps (vs. 12,080 lines of data dump)

## Intelligent Agents with Brain Context - COMPLETED:
✅ Agent Brain: Domain knowledge, pattern recognition, contextual reasoning
✅ Intelligent Executive Agent: Domain-specific executive extraction
✅ Intelligent Investment Agent: Contextual investment analysis  
✅ Intelligent Gap Analysis Agent: Strategic opportunity identification
✅ Quality Filtering: 76 relevant sources (vs. irrelevant Wikipedia/dictionary)
✅ Strategic Synthesis: 4 actionable opportunities with LLM reasoning
✅ Confidence Scoring: 0.47 overall (vs. 0.0 from generic system)

## Key Breakthrough:
The agents now have "brain context" - they understand healthcare vs fintech, 
filter irrelevant sources, and provide strategic analysis instead of data dumps.

## Ready for Phase 2: Additional Specialist Agents
