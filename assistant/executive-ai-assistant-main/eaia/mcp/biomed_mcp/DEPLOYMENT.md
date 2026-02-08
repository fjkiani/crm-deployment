# Biomed MCP Deployment Guide

## Overview
This guide follows first principles for deploying the Biomed MCP server in different environments.

## Prerequisites

### Required Environment Variables
```bash
# Azure OpenAI Configuration (Required)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-azure-openai-key
OPENAI_API_VERSION=2025-01-01-preview
AZURE_OPENAI_MODEL=azure_openai:o3

# PubMed Configuration (Required)  
PUBMED_EMAIL=your-email@example.com
PUBMED_API_KEY=optional-but-recommended

# Optional Configuration
BIOMED_MAX_RESULTS=20
BIOMED_CACHE_TTL=3600
```

### Dependencies
- Docker (for containerized deployment)
- Python 3.10+ (for local deployment)
- Access to pubmed-mcp and clinical-trial-mcp source code

## Quick Start Testing

### 1. Test Azure OpenAI Connection
```bash
# Set environment variables
cp environment.example .env
# Edit .env with your credentials

# Quick connection test
python quick_test.py
```

### 2. Run Comprehensive Tests  
```bash
# Full test suite
python test_client.py
```

## Deployment Options

### Option 1: Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_API_KEY="your-key"
export PUBMED_EMAIL="your-email@example.com"

# Run server
python -m biomed_agents
```

### Option 2: Docker Deployment
```bash
# Build image
docker build -t biomed-mcp .

# Run container
docker run -d \
  --name biomed-mcp \
  -e AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/" \
  -e AZURE_OPENAI_API_KEY="your-key" \
  -e PUBMED_EMAIL="your-email@example.com" \
  -p 8000:8000 \
  biomed-mcp
```

### Option 3: Docker Compose (Recommended)
```bash
# Create .env file with your credentials
cp environment.example .env
# Edit .env file

# Deploy with compose
docker-compose up -d

# Check logs
docker-compose logs -f biomed-mcp

# Check health
docker-compose exec biomed-mcp python -c "from biomed_agents.server import health_check; print(health_check())"
```

## Production Deployment

### Security Considerations
1. **Environment Variables**: Use secrets management (e.g., Azure Key Vault, AWS Secrets Manager)
2. **Network Security**: Deploy behind reverse proxy with TLS
3. **Access Control**: Implement authentication for MCP access
4. **Monitoring**: Set up logging and health monitoring

### Scaling Considerations
1. **Resource Limits**: Configure appropriate CPU/memory limits
2. **Rate Limiting**: Implement request throttling for Azure OpenAI
3. **Caching**: Use Redis for response caching (included in docker-compose)
4. **Load Balancing**: Deploy multiple instances behind load balancer


## Monitoring and Troubleshooting

### Health Checks
```bash
# Check server health
curl http://localhost:8000/health

# Or using Python
python -c "from biomed_agents.server import health_check; print(health_check())"
```

## Integration with MCP Clients

### Claude Desktop
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "biomed-mcp": {
      "command": "docker",
      "args": ["exec", "biomed-mcp", "python", "-m", "biomed_agents"]
    }
  }
}
```

### Custom MCP Client
The server exposes these tools:
- `biomedical_literature_search`
- `clinical_trials_research` 
- `analyze_clinical_trial`
- `analyze_research_paper`
