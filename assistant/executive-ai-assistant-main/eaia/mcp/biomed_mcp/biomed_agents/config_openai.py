"""
Modified configuration to support standard OpenAI API (not just Azure)

This file patches BioMed-MCP to work with standard OpenAI API keys.
"""
import os
from typing import Optional
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel


def get_openai_llm() -> BaseChatModel:
    """
    Initialize OpenAI model (supports both standard OpenAI API and Azure OpenAI)
    
    Priority:
    1. Standard OpenAI API (if OPENAI_API_KEY is set)
    2. Azure OpenAI (if AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY are set)
    
    Returns:
        Configured OpenAI chat model
    """
    # Check for standard OpenAI API key first
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if openai_api_key:
        # Use standard OpenAI API
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
        temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
        
        print(f"✅ Using standard OpenAI API with model: {model_name}")
        
        llm = init_chat_model(
            model=f"openai/{model_name}",
            api_key=openai_api_key,
            temperature=temperature
        )
        return llm
    
    # Fall back to Azure OpenAI
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("OPENAI_API_VERSION", "2025-01-01-preview")
    model_provider = os.getenv("AZURE_OPENAI_MODEL_PROVIDER", "azure_openai")
    model_name = os.getenv("AZURE_OPENAI_MODEL", "o3")
    azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gsds-o3")
    
    if not endpoint or not api_key:
        raise ValueError(
            "Either OPENAI_API_KEY (standard OpenAI) or "
            "AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY (Azure OpenAI) "
            "environment variables are required"
        )
    
    print(f"✅ Using Azure OpenAI with model: {model_name}")
    
    llm = init_chat_model(
        model=model_name,
        api_version=api_version,
        azure_endpoint=endpoint,
        api_key=api_key,
        azure_deployment=azure_deployment,
        model_provider=model_provider
    )
    
    return llm


# Re-export the original function name for compatibility
get_azure_openai_llm = get_openai_llm











