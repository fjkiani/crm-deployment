# Biomed MCP Dockerfile
# First principles: Create minimal, secure, production-ready container

# Use Python 3.10 slim for smaller footprint and compatibility
FROM python:3.10-slim

# Set metadata
LABEL maintainer="Biomed MCP Team"
LABEL description="Intelligent biomedical research MCP server with ReAct agents"
LABEL version="0.1.0"

# First principle: Security - Create non-root user
RUN groupadd -r biomcp && useradd -r -g biomcp biomcp

# First principle: Efficiency - Set up working directory
WORKDIR /app

# First principle: Layer optimization - Copy requirements first for better caching
COPY requirements.txt ./

# First principle: Security - Update system and install dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        curl \
        && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# First principle: Dependency management - Create directories for external MCPs
RUN mkdir -p /app/external_mcps

# Copy external MCP dependencies (pubmed-mcp and clinical-trial-mcp)
# Note: These should be built into the image or mounted as volumes
COPY ../pubmed-mcp /app/external_mcps/pubmed-mcp
COPY ../clinical-trial-mcp /app/external_mcps/clinical-trial-mcp

# Add external MCPs to Python path
ENV PYTHONPATH="/app:/app/external_mcps/pubmed-mcp:/app/external_mcps/clinical-trial-mcp"

# Copy application code
COPY . .

# First principle: Security - Change ownership to non-root user
RUN chown -R biomcp:biomcp /app

# First principle: Reliability - Set required environment variables with defaults
ENV PYTHONPATH="/app:/app/external_mcps/pubmed-mcp:/app/external_mcps/clinical-trial-mcp"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# First principle: Configuration - Environment variables for runtime config
ENV BIOMED_MAX_RESULTS=20
ENV BIOMED_CACHE_TTL=3600
ENV AZURE_OPENAI_MODEL=azure_openai:o3
ENV OPENAI_API_VERSION=2025-01-01-preview

# Required environment variables (must be provided at runtime)
# AZURE_OPENAI_ENDPOINT - Azure OpenAI service endpoint
# AZURE_OPENAI_API_KEY - Azure OpenAI API key  
# PUBMED_EMAIL - Email for PubMed API access

# First principle: Security - Switch to non-root user
USER biomcp

# First principle: Monitoring - Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from biomed_agents.server import health_check; result = health_check(); exit(0 if 'healthy' in result.lower() else 1)"

# First principle: Documentation - Expose port for MCP protocol
# Note: MCP typically uses stdio, but exposing for potential HTTP transport
EXPOSE 8000

# First principle: Reliability - Set proper entrypoint
ENTRYPOINT ["python", "-m", "biomed_agents"]

# First principle: Flexibility - Allow CMD override for different modes
CMD []