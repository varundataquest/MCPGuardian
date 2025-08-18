"""LangGraph workflow definition for the MCP selector."""

from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .nodes import ManagerAgent, CrawlerAgent, WriterAgent, SecurityAgent, FinalizerAgent


def create_workflow() -> StateGraph:
    """Create the LangGraph workflow."""
    
    # Create the state graph
    workflow = StateGraph(StateType=Dict[str, Any])
    
    # Add nodes
    workflow.add_node("manager", ManagerAgent().run)
    workflow.add_node("crawler", CrawlerAgent().run)
    workflow.add_node("writer", WriterAgent().run)
    workflow.add_node("security", SecurityAgent().run)
    workflow.add_node("finalizer", FinalizerAgent().run)
    
    # Define the workflow
    workflow.set_entry_point("manager")
    
    # Linear workflow: manager -> crawler -> writer -> security -> finalizer
    workflow.add_edge("manager", "crawler")
    workflow.add_edge("crawler", "writer")
    workflow.add_edge("writer", "security")
    workflow.add_edge("security", "finalizer")
    workflow.add_edge("finalizer", END)
    
    # Compile the workflow
    app = workflow.compile(checkpointer=MemorySaver())
    
    return app


# Global workflow instance
workflow = create_workflow()


async def run_pipeline(user_task: str, max_candidates: int = 50) -> Dict[str, Any]:
    """
    Run the complete pipeline.
    
    Args:
        user_task: The user's task description
        max_candidates: Maximum number of candidates to process
        
    Returns:
        Pipeline results
    """
    # Initial state
    initial_state = {
        "user_task": user_task,
        "max_candidates": max_candidates
    }
    
    # Run the workflow
    result = await workflow.ainvoke(initial_state)
    
    return result 