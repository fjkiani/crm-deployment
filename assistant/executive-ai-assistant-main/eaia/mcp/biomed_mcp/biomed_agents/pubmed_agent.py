"""
PubMed ReAct Agent using LangGraph
"""
import os
from typing import Dict, Any, List, Optional, TypedDict
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.messages.utils import trim_messages, filter_messages
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

from .config import get_azure_openai_llm, PUBMED_AGENT_PROMPT
from .tools.pubmed_tools import PUBMED_TOOLS


class ResearchComplete(BaseModel):
    """Tool to signal literature research completion with summary"""
    summary: str = Field(description="Comprehensive summary of literature research findings")
    key_findings: List[str] = Field(description="List of key findings from the research")
    recommendations: str = Field(description="Research implications and recommendations")

class PubMedState(TypedDict):
    """Enhanced state with step tracking and summarization"""
    messages: List
    step_count: int
    summarized: bool
    research_complete: bool
    tool_call_iterations: int


class PubMedAgent:
    """
    ReAct agent for PubMed literature search and analysis
    """
    
    def __init__(self):
        """Initialize the PubMed agent with LangGraph"""
        self.llm = get_azure_openai_llm()
        # Store tools with ResearchComplete
        all_tools = PUBMED_TOOLS + [ResearchComplete]
        self.tools = PUBMED_TOOLS  
        
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
        """Build the ReAct graph for PubMed agent with summarization"""
        
        def should_continue(state: PubMedState) -> str:
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
        


        async def call_model(state: PubMedState) -> Dict[str, Any]:
            """Call the LLM with properly validated message history"""
            messages = state["messages"]
            step_count = state.get("step_count", 0)
            
            # Create system prompt
            enhanced_prompt = f"""{PUBMED_AGENT_PROMPT}

IMPORTANT INSTRUCTIONS:
- You have a maximum of 4 tool calls to complete your research
- Focus on gathering key literature information efficiently
- When you have sufficient papers and data, use the ResearchComplete tool to signal completion
- Use ResearchComplete tool to provide summary, key findings, and recommendations
- Provide analysis based on the papers you find"""
            
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

        async def call_tools(state: PubMedState) -> Dict[str, Any]:
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
                            content="Literature research completed successfully. Proceeding to final summary.",
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
        
        async def summarize_findings(state: PubMedState) -> Dict[str, Any]:
            """Advanced summarization following deep researcher pattern"""
            messages = state["messages"]
            
            # Extract research findings from tool messages and AI responses
            research_content = []
            for msg in filter_messages(messages, include_types=["tool", "ai"]):
                if isinstance(msg, (ToolMessage, AIMessage)) and msg.content:
                    research_content.append(str(msg.content))
            
            findings = "\n".join(research_content)
            
            # Find the original query
            original_query = "biomedical literature research"
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    original_query = msg.content
                    break
            
            # Advanced summarization prompt
            compression_prompt = f"""You are a biomedical literature research expert conducting a comprehensive analysis.

ORIGINAL RESEARCH QUERY: {original_query}

RESEARCH FINDINGS TO SYNTHESIZE:
{findings}

Please provide a comprehensive summary that includes:

1. **Executive Summary**: Brief overview of key findings
2. **Papers Identified**: List key publications with PMIDs and brief descriptions
3. **Research Trends**: Important patterns and trends in the literature
4. **Methodologies**: Study designs and approaches used
5. **Key Findings**: Important discoveries and insights
6. **Clinical Implications**: What these findings mean for clinical practice/research
7. **Research Gaps**: Areas needing further investigation
8. **Recommendations**: Future research directions and applications

Format your response as a structured literature review. Be thorough but concise."""

            max_retries = 3
            current_retry = 0
            
            while current_retry < max_retries:
                try:
                    # Use a clean message context for summarization
                    summary_messages = [
                        SystemMessage(content="You are an expert biomedical researcher. Provide comprehensive, evidence-based literature reviews."),
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
                        fallback_response = AIMessage(content=f"Literature research completed with {len(research_content)} data points collected. Unable to generate detailed summary due to: {str(e)}")
                        return {
                            "messages": [fallback_response], 
                            "step_count": state.get("step_count", 0),
                            "summarized": True,
                            "research_complete": True
                        }
            
            # Should not reach here, but provide fallback
            fallback_response = AIMessage(content="Literature research completed. Maximum retry attempts exceeded for summary generation.")
            return {
                "messages": [fallback_response], 
                "step_count": state.get("step_count", 0),
                "summarized": True,
                "research_complete": True
            }
        
        # Create the graph
        workflow = StateGraph(PubMedState)
        
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
    
    async def search_literature(
        self, 
        query: str, 
        thread_id: str = "default",
        max_papers: int = 10,
        include_fulltext: bool = False
    ) -> str:
        """
        Search biomedical literature with intelligent reasoning
        
        Args:
            query: Research question or topic
            thread_id: Conversation thread identifier
            max_papers: Maximum number of papers to retrieve
            include_fulltext: Whether to attempt full-text retrieval
            
        Returns:
            Comprehensive literature search results and analysis
        """
        
        # Construct research prompt
        research_prompt = f"""Please help me research the following topic in biomedical literature:

Query: {query}

Requirements:
- Search for up to {max_papers} relevant papers
- Provide a comprehensive summary of findings
- Include key insights and recent developments
{'- Attempt to retrieve full text for the most relevant papers' if include_fulltext else ''}
- Cite PMIDs and DOIs for reference

IMPORTANT: After searching and gathering the literature, provide a comprehensive analysis and summary. Do NOT continue searching for more papers unless the initial search returns insufficient results. Aim to complete your analysis in 2-3 tool calls maximum.

Please be thorough in your search and analysis."""
        
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
    
    async def get_paper_insights(
        self, 
        pmid: str, 
        thread_id: str = "default"
    ) -> str:
        """
        Get detailed insights from a specific paper
        
        Args:
            pmid: PubMed ID of the paper
            thread_id: Conversation thread identifier
            
        Returns:
            Detailed analysis of the paper
        """
        
        insight_prompt = f"""Please analyze this specific paper in detail:

PMID: {pmid}

Please:
1. Retrieve the full text if available
2. Provide a comprehensive summary of the paper
3. Extract key findings and conclusions
4. Identify the methodology used
5. Note any limitations or future research directions mentioned

IMPORTANT: Focus on analyzing the specific paper. After retrieving the paper information, provide a comprehensive analysis. Complete your analysis in 1-2 tool calls maximum.

Be thorough in your analysis."""
        
        final_state = await self.app.ainvoke(
            {
                "messages": [HumanMessage(content=insight_prompt)], 
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