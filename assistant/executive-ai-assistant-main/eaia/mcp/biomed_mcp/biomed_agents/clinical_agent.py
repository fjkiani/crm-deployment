"""
Clinical Trials ReAct Agent using LangGraph
"""
import os
from typing import Dict, Any, List, Optional, TypedDict
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.messages.utils import trim_messages, filter_messages
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

from .config import get_azure_openai_llm, CLINICAL_AGENT_PROMPT
from .tools.clinical_tools import CLINICAL_TOOLS


class ResearchComplete(BaseModel):
    """Tool to signal research completion with summary"""
    summary: str = Field(description="Comprehensive summary of clinical trial research findings")
    key_findings: List[str] = Field(description="List of key findings from the research")
    recommendations: str = Field(description="Clinical recommendations based on the findings")

class ClinicalState(TypedDict):
    """Enhanced state with step tracking and summarization"""
    messages: List
    step_count: int
    summarized: bool
    research_complete: bool
    tool_call_iterations: int


class ClinicalTrialsAgent:
    """
    ReAct agent for Clinical Trials research and analysis
    """
    
    def __init__(self):
        """Initialize the Clinical Trials agent with LangGraph"""
        self.llm = get_azure_openai_llm()
        # Store tools with ResearchComplete
        all_tools = CLINICAL_TOOLS + [ResearchComplete]
        self.tools = CLINICAL_TOOLS  # Keep original tools for ToolNode
        
        # Bind tools to the model (including ResearchComplete)
        self.llm_with_tools = self.llm.bind_tools(all_tools)
        
        # Create tool node (only with actual callable tools)
        self.tool_node = ToolNode(self.tools)
        
        # Build the graph
        self.graph = self._build_graph()
        
        # Compile with memory
        self.memory = MemorySaver()
        self.app = self.graph.compile(checkpointer=self.memory)
    
    def validate_message_sequence(self, messages: List) -> List:
        """Validate and fix message sequence to comply with OpenAI requirements"""
        if not messages:
            return []
        
        validated_messages = []
        i = 0
        
        while i < len(messages):
            current_msg = messages[i]
            
            # Skip system messages in the middle of conversation
            if isinstance(current_msg, SystemMessage) and validated_messages:
                i += 1
                continue
            
            # Handle AI messages with tool calls
            if isinstance(current_msg, AIMessage) and hasattr(current_msg, 'tool_calls') and current_msg.tool_calls:
                validated_messages.append(current_msg)
                
                # Look for corresponding tool messages
                j = i + 1
                tool_call_ids = {tc.get("id") for tc in current_msg.tool_calls}
                
                while j < len(messages) and tool_call_ids:
                    next_msg = messages[j]
                    if isinstance(next_msg, ToolMessage) and hasattr(next_msg, 'tool_call_id'):
                        if next_msg.tool_call_id in tool_call_ids:
                            validated_messages.append(next_msg)
                            tool_call_ids.discard(next_msg.tool_call_id)
                    elif not isinstance(next_msg, ToolMessage):
                        # Stop if we hit a non-tool message
                        break
                    j += 1
                
                i = j
                
            # Handle other message types
            elif isinstance(current_msg, (HumanMessage, AIMessage)) and not (hasattr(current_msg, 'tool_calls') and current_msg.tool_calls):
                validated_messages.append(current_msg)
                i += 1
                
            # Skip standalone tool messages (they're invalid without preceding tool calls)
            else:
                i += 1
        
        return validated_messages
    
    def _build_graph(self) -> StateGraph:
        """Build the ReAct graph for Clinical Trials agent with summarization"""
        
        def should_continue(state: ClinicalState) -> str:
            """Determine whether to continue with tools, summarize, or end"""
            last_message = state["messages"][-1]
            step_count = state.get("step_count", 0)
            tool_call_iterations = state.get("tool_call_iterations", 0)
            summarized = state.get("summarized", False)
            
            # Exit Criteria (following deep researcher pattern):
            # 1. Exceeded max tool call iterations
            # 2. No tool calls were made
            # 3. ResearchComplete tool call was made
            # 4. Already summarized
            
            exceeded_max_iterations = tool_call_iterations >= 4
            no_tool_calls = not (hasattr(last_message, 'tool_calls') and last_message.tool_calls)
            research_complete_called = (hasattr(last_message, 'tool_calls') and 
                                      last_message.tool_calls and 
                                      any(tc.get("name") == "ResearchComplete" for tc in last_message.tool_calls))
            
            if exceeded_max_iterations or no_tool_calls or research_complete_called or summarized:
                if not summarized and not research_complete_called:
                    return "summarize"
                return "__end__"
            
            # If LLM makes tool calls, route to tools
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "tools"
            
            # Otherwise, end the conversation
            return "__end__"
        


        async def call_model(state: ClinicalState) -> Dict[str, Any]:
            """Call the LLM with properly validated message history"""
            messages = state["messages"]
            step_count = state.get("step_count", 0)
            
            # Create system prompt
            enhanced_prompt = f"""{CLINICAL_AGENT_PROMPT}

IMPORTANT INSTRUCTIONS:
- You have a maximum of 4 tool calls to complete your research
- Focus on gathering key clinical trial information efficiently
- When you have sufficient data, use the ResearchComplete tool to signal completion
- Use ResearchComplete tool to provide summary, key findings, and recommendations
- Provide analysis based on the data you collect"""
            
            # Validate message sequence to prevent OpenAI API errors
            validated_messages = self.validate_message_sequence(messages)
            
            # Build final message list
            llm_messages = [SystemMessage(content=enhanced_prompt)]
            
            # Add validated messages (keeping recent ones if too many)
            if len(validated_messages) > 10:
                # Keep the first human message and last 9 messages to preserve context
                first_human = next((msg for msg in validated_messages if isinstance(msg, HumanMessage)), None)
                recent_messages = validated_messages[-9:]
                
                if first_human and first_human not in recent_messages:
                    llm_messages.extend([first_human] + recent_messages)
                else:
                    llm_messages.extend(recent_messages)
            else:
                llm_messages.extend(validated_messages)
            
            response = await self.llm_with_tools.ainvoke(llm_messages)
            return {"messages": [response], "step_count": step_count + 1}

        async def call_tools(state: ClinicalState) -> Dict[str, Any]:
            """Call tools and update counters, handling ResearchComplete specially"""
            messages = state["messages"]
            last_message = messages[-1]
            step_count = state.get("step_count", 0)
            tool_call_iterations = state.get("tool_call_iterations", 0)
            
            # Check if ResearchComplete was called
            if (hasattr(last_message, 'tool_calls') and last_message.tool_calls and 
                any(tc.get("name") == "ResearchComplete" for tc in last_message.tool_calls)):
                
                # Handle ResearchComplete tool calls by creating appropriate tool messages
                tool_messages = []
                for tool_call in last_message.tool_calls:
                    if tool_call.get("name") == "ResearchComplete":
                        tool_messages.append(ToolMessage(
                            content="Research completed successfully. Proceeding to final summary.",
                            tool_call_id=tool_call["id"]
                        ))
                
                return {
                    "messages": tool_messages,
                    "step_count": step_count + 1,
                    "tool_call_iterations": tool_call_iterations + 1,
                    "research_complete": True
                }
            
            # Handle regular tools
            result = await self.tool_node.ainvoke(state)
            return {
                "messages": result["messages"], 
                "step_count": step_count + 1,
                "tool_call_iterations": tool_call_iterations + 1
            }
        
        async def summarize_findings(state: ClinicalState) -> Dict[str, Any]:
            """Advanced summarization following deep researcher pattern"""
            messages = state["messages"]
            
            # Extract research findings from tool messages and AI responses
            research_content = []
            for msg in filter_messages(messages, include_types=["tool", "ai"]):
                if isinstance(msg, (ToolMessage, AIMessage)) and msg.content:
                    research_content.append(str(msg.content))
            
            findings = "\n".join(research_content)
            
            # Find the original query
            original_query = "clinical trials research"
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    original_query = msg.content
                    break
            
            # Advanced summarization prompt
            compression_prompt = f"""You are a clinical research expert conducting a comprehensive analysis.

ORIGINAL RESEARCH QUERY: {original_query}

RESEARCH FINDINGS TO SYNTHESIZE:
{findings}

Please provide a comprehensive summary that includes:

1. **Executive Summary**: Brief overview of key findings
2. **Clinical Trials Identified**: List trials with NCT IDs and brief descriptions
3. **Study Characteristics**: Phases, participant counts, interventions
4. **Key Findings**: Important results and patterns observed
5. **Clinical Implications**: What these findings mean for clinical practice
6. **Limitations**: Any gaps or limitations in the research
7. **Recommendations**: Next steps or clinical recommendations

Format your response as a structured clinical research report. Be thorough but concise."""

            max_retries = 3
            current_retry = 0
            
            while current_retry < max_retries:
                try:
                    # Use a clean message context for summarization
                    summary_messages = [
                        SystemMessage(content="You are an expert clinical researcher. Provide comprehensive, evidence-based summaries."),
                        HumanMessage(content=compression_prompt)
                    ]
                    
                    summary_response = await self.llm.ainvoke(summary_messages)
                    
                    return {
                        "messages": [summary_response], 
                        "step_count": state.get("step_count", 0),
                        "summarized": True,
                        "research_complete": True
                    }
                    
                except Exception as e:
                    current_retry += 1
                    if "token" in str(e).lower() and current_retry < max_retries:
                        # Reduce findings size if token limit exceeded
                        findings = findings[:int(len(findings) * 0.7)]
                        compression_prompt = compression_prompt.replace(findings, findings)
                        continue
                    else:
                        # Fallback summary on final retry
                        fallback_response = AIMessage(content=f"Research completed with {len(research_content)} data points collected. Unable to generate detailed summary due to: {str(e)}")
                        return {
                            "messages": [fallback_response], 
                            "step_count": state.get("step_count", 0),
                            "summarized": True,
                            "research_complete": True
                        }
            
            # Should not reach here, but provide fallback
            fallback_response = AIMessage(content="Research completed. Maximum retry attempts exceeded for summary generation.")
            return {
                "messages": [fallback_response], 
                "step_count": state.get("step_count", 0),
                "summarized": True,
                "research_complete": True
            }
        
        # Create the graph
        workflow = StateGraph(ClinicalState)
        
        # Add nodes
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", call_tools)
        workflow.add_node("summarize", summarize_findings)
        
        # Set entry point
        workflow.set_entry_point("agent")
        
        # Add edges
        workflow.add_conditional_edges("agent", should_continue, ["tools", "summarize", "__end__"])
        workflow.add_edge("tools", "agent")
        workflow.add_edge("summarize", "__end__")
        
        return workflow
    
    async def research_condition(
        self, 
        condition: str, 
        thread_id: str = "default",
        max_studies: int = 15,
        analyze_patterns: bool = True
    ) -> str:
        """
        Research clinical trials for a specific medical condition
        
        Args:
            condition: Medical condition or intervention to research
            thread_id: Conversation thread identifier
            max_studies: Maximum number of studies to analyze
            analyze_patterns: Whether to perform pattern analysis
            
        Returns:
            Comprehensive clinical trials research results
        """
        
        research_prompt = f"""Please help me research clinical trials for the following condition:

Condition: {condition}

Requirements:
- Search for up to {max_studies} relevant clinical trials
- Provide analysis of current trial landscape
- Identify key research trends and patterns
- Highlight important ongoing and completed studies
{'- Analyze patterns in study phases, status, and interventions' if analyze_patterns else ''}
- Include NCT IDs for reference

IMPORTANT: After gathering the clinical trial data, provide a comprehensive summary and analysis. Do NOT continue searching for more data unless the initial search returns insufficient results. Aim to complete your analysis in 2-3 tool calls maximum."""
        
        # Invoke the agent with enhanced state tracking
        final_state = await self.app.ainvoke(
            {
                "messages": [HumanMessage(content=research_prompt)], 
                "step_count": 0, 
                "summarized": False,
                "research_complete": False,
                "tool_call_iterations": 0
            },
            config={
                "configurable": {"thread_id": thread_id},
                "recursion_limit": 20  # Allow for tool calls and summarization
            }
        )
        
        # Return the final response
        return final_state["messages"][-1].content
    
    async def analyze_trial_details(
        self, 
        nct_id: str, 
        thread_id: str = "default"
    ) -> str:
        """
        Analyze a specific clinical trial in detail
        
        Args:
            nct_id: NCT ID of the clinical trial
            thread_id: Conversation thread identifier
            
        Returns:
            Detailed trial analysis
        """
        
        analysis_prompt = f"""Please provide a detailed analysis of this clinical trial:

NCT ID: {nct_id}

Please:
1. Get comprehensive trial details
2. Analyze the study design and methodology
3. Evaluate eligibility criteria and target population
4. Assess primary and secondary outcomes
5. Identify the current status and timeline
6. Note any unique aspects or innovations
7. Assess potential clinical impact

IMPORTANT: Focus on analyzing the specific trial details. After retrieving the trial information, provide a comprehensive analysis. Complete your analysis in 1-2 tool calls maximum.

Be thorough and provide clinical insights."""
        
        final_state = await self.app.ainvoke(
            {
                "messages": [HumanMessage(content=analysis_prompt)], 
                "step_count": 0, 
                "summarized": False,
                "research_complete": False,
                "tool_call_iterations": 0
            },
            config={
                "configurable": {"thread_id": thread_id},
                "recursion_limit": 15  # Allow for tool calls and summarization
            }
        )
        
        return final_state["messages"][-1].content
    
    async def compare_interventions(
        self,
        intervention_a: str,
        intervention_b: str,
        condition: str,
        thread_id: str = "default"
    ) -> str:
        """
        Compare two interventions for a specific condition
        
        Args:
            intervention_a: First intervention to compare
            intervention_b: Second intervention to compare
            condition: Medical condition context
            thread_id: Conversation thread identifier
            
        Returns:
            Comparative analysis of interventions
        """
        
        comparison_prompt = f"""Please compare these two interventions for {condition}:

Intervention A: {intervention_a}
Intervention B: {intervention_b}
Condition: {condition}

Please:
1. Search for trials involving each intervention
2. Analyze trial phases and progression for each
3. Compare study designs and methodologies
4. Evaluate patient populations and eligibility
5. Assess outcome measures and endpoints
6. Identify any head-to-head comparison studies
7. Provide insights on current research trends

IMPORTANT: Focus on gathering trial data for both interventions efficiently. After collecting the data, provide a comprehensive comparison. Complete your analysis in 2-3 tool calls maximum.

Be analytical and provide evidence-based comparisons."""
        
        final_state = await self.app.ainvoke(
            {
                "messages": [HumanMessage(content=comparison_prompt)], 
                "step_count": 0, 
                "summarized": False,
                "research_complete": False,
                "tool_call_iterations": 0
            },
            config={
                "configurable": {"thread_id": thread_id},
                "recursion_limit": 18  # Allow for tool calls and summarization
            }
        )
        
        return final_state["messages"][-1].content