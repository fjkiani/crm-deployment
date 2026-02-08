"""
Biomed MCP - Intelligent biomedical research using LangGraph ReAct agents
"""

# Load environment variables first, before any imports that might need them
from dotenv import load_dotenv
load_dotenv()

__version__ = "0.1.0"
__author__ = "Biomed MCP Team"

from .pubmed_agent import PubMedAgent
from .clinical_agent import ClinicalTrialsAgent
# from .server import main

__all__ = ["PubMedAgent", "ClinicalTrialsAgent", "main"]