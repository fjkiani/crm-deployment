# Biomed-MCP

Intelligent biomedical research MCP server combining PubMed and Clinical Trials functionality using LangGraph ReAct agents.

## Overview

Biomed-MCP provides AI-powered research assistance for biomedical literature and clinical trials through a unified MCP (Model Context Protocol) interface. Instead of simple API wrappers, it uses sophisticated ReAct agents that can reason, plan, and synthesize information across multiple data sources with advanced state management and intelligent summarization.

## Features

### 🧠 Enhanced ReAct Agents
- **PubMed Agent**: Literature search, full-text retrieval, and intelligent synthesis
- **Clinical Trials Agent**: Trial discovery, pattern analysis, and comprehensive insights
- **Advanced ReAct Architecture**: Reasoning → Action → Observation workflow with state tracking
- **Multi-step Research**: Chains multiple API calls with iteration limits (max 4 tool calls)
- **Research Completion Detection**: Intelligent stopping criteria with ResearchComplete tool
- **Message Validation**: OpenAI API compliance with proper message sequence handling

### 🔧 Advanced Capabilities
- **Literature Synthesis**: Combine findings across multiple papers with structured summaries
- **Pattern Analysis**: Identify trends in clinical trial data with comprehensive analysis
- **Cross-referencing**: Link related papers and trials intelligently
- **Full-text Analysis**: Extract insights from complete papers when available
- **Thread Memory**: Persistent conversation context with LangGraph checkpointing
- **Advanced Summarization**: Multi-retry summarization with token limit handling
- **Structured Reporting**: Clinical research reports and literature reviews

### 🚀 MCP Integration
- **4 Main Tools**: Literature search, clinical trials research, trial analysis, paper analysis
- **Resource Endpoints**: Health checks and status monitoring
- **Thread Management**: Maintain context across conversations with memory persistence
- **Error Handling**: Graceful degradation when services unavailable
- **Example Scripts**: Ready-to-use examples for both PubMed and Clinical Trials research

## Installation

### Prerequisites
- Python 3.10+
- Azure OpenAI account with API access
- PubMed email for NCBI API access
- Access to existing pubmed-mcp and clinical-trial-mcp directories

### Environment Setup

1. Copy environment template:
```bash
cp environment.example .env
```

2. Configure environment variables:
```bash
# Required for PubMed access
PUBMED_EMAIL=your-email@example.com
PUBMED_API_KEY=optional-api-key

# Required for Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-azure-openai-key
OPENAI_API_VERSION=2025-01-01-preview

# Optional configuration
BIOMED_MAX_RESULTS=20
AZURE_OPENAI_MODEL=azure_openai:o3
```

### Installation

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Run the server
python -m biomed_agents
```

## Usage

### MCP Tools

#### 1. biomedical_literature_search
Intelligent literature research with AI analysis:
```python
{
    "query": "CRISPR gene editing cancer therapy",
    "max_papers": 15,
    "include_fulltext": true,
    "synthesize_findings": true
}
```

#### 2. clinical_trials_research  
Comprehensive clinical trials research:
```python
{
    "condition": "diabetes type 2",
    "study_phase": "Phase 3", 
    "max_studies": 20,
    "analyze_trends": true
}
```

#### 3. analyze_clinical_trial
Detailed analysis of specific trials:
```python
{
    "nct_id": "NCT04280705"
}
```

#### 4. analyze_research_paper
In-depth paper analysis:
```python
{
    "pmid": "39661433"
}
```

### Example Scripts

The project includes ready-to-use example scripts:

**PubMed Literature Analysis:**
```bash
python pubmed_example.py
```
Analyzes CRISPR gene editing literature with intelligent synthesis and saves results to timestamped files.

**Clinical Trials Research:**
```bash
python clinical_trial_example.py
```
Analyzes COVID-19 vaccine Phase 3 trials with pattern analysis and comprehensive reporting.

### Example Queries

**Literature Research:**
- "Find recent papers on mRNA vaccine mechanisms"
- "Research CAR-T cell therapy for lymphoma"
- "Analyze biomarkers for Alzheimer's disease"
- "Compare therapeutic approaches for rare diseases"

**Clinical Trials Research:**
- "Find Phase 3 trials for obesity treatments"
- "Compare immunotherapy approaches for melanoma"
- "Analyze recruitment patterns for rare disease trials"
- "Research intervention effectiveness across different phases"

## Architecture

### Enhanced ReAct Agent Pattern
```
User Query → Agent Reasoning → Tool Selection → API Calls → Result Synthesis → Intelligent Summarization → Response
```

**Key Components:**
- **State Management**: Track step count, tool iterations, and completion status
- **Message Validation**: Ensure OpenAI API compliance with proper sequence handling
- **Iteration Limits**: Maximum 4 tool calls to prevent excessive API usage
- **Research Completion**: ResearchComplete tool signals when sufficient data is gathered
- **Advanced Summarization**: Multi-retry with token limit handling and fallback responses

### Agent-Specific Methods

**PubMed Agent:**
- `search_literature()`: Intelligent literature search with synthesis
- `get_paper_insights()`: Detailed analysis of specific papers

**Clinical Trials Agent:**
- `research_condition()`: Comprehensive condition-based trial research
- `analyze_trial_details()`: In-depth analysis of specific trials
- `compare_interventions()`: Comparative analysis of different treatments

### Tool Abstraction Layer
- **PubMed Tools**: search_pubmed_articles, get_pubmed_fulltext
- **Clinical Tools**: search_clinical_trials, get_clinical_trial_details, analyze_clinical_trials_patterns
- **LangGraph Integration**: StateGraph with conditional edges and memory checkpointing
- **Error Handling**: Graceful degradation with detailed error reporting

### Azure OpenAI Integration
```python
from langchain import init_chat_model

llm = init_chat_model(
    model="azure_openai:o3",
    api_version="2025-01-01-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
)
```

## Development

### Project Structure
```
biomed-mcp/
├── biomed_agents/
│   ├── __init__.py
│   ├── config.py              # Azure OpenAI configuration
│   ├── pubmed_agent.py        # Enhanced PubMed ReAct agent with state management
│   ├── clinical_agent.py      # Enhanced Clinical Trials ReAct agent with summarization
│   ├── server.py             # Main MCP server with resource endpoints
│   └── tools/
│       ├── __init__.py
│       ├── pubmed_tools.py    # PubMed tool wrappers
│       └── clinical_tools.py  # Clinical Trials tool wrappers
├── pubmed_example.py          # Literature analysis example script
├── clinical_trial_example.py  # Clinical trials analysis example script
├── example/                   # Output directory for example results
├── requirements.txt
├── pyproject.toml
├── environment.example
├── .gitignore
├── Dockerfile                 # Docker deployment configuration
├── docker-compose.yml         # Multi-container setup
└── README.md
```

### Testing

**Run Example Scripts:**
```bash
# Test PubMed literature analysis
python pubmed_example.py

# Test clinical trials research
python clinical_trial_example.py
```

**Test Individual Agents:**
```bash
# Test PubMed agent directly
python -c "
import asyncio
from biomed_agents import PubMedAgent
agent = PubMedAgent()
result = asyncio.run(agent.search_literature('COVID-19 vaccines'))
print(result)
"

# Test Clinical Trials agent directly  
python -c "
import asyncio
from biomed_agents import ClinicalTrialsAgent
agent = ClinicalTrialsAgent()
result = asyncio.run(agent.research_condition('diabetes'))
print(result)
"
```

**Test MCP Server:**
```bash
# Start the MCP server
python -m biomed_agents

# Test with MCP client
python test_client.py
```

## Dependencies

- **FastMCP**: MCP framework (2.10.0+)
- **LangGraph**: Agent framework  
- **LangChain**: Tool abstractions and Azure OpenAI integration
- **Biopython**: PubMed API access
- **PyTrials**: Clinical Trials API access
- **Pandas**: Data manipulation
- **Pydantic**: Data validation

## Troubleshooting

### Common Issues

**Import Errors:**
Ensure pubmed-mcp and clinical-trial-mcp directories are accessible:
```bash
export PYTHONPATH="${PYTHONPATH}:../pubmed-mcp:../clinical-trial-mcp"
```

**Azure OpenAI Errors:**
- Verify endpoint URL format: `https://your-resource.openai.azure.com/`
- Check API version compatibility: `2025-01-01-preview`
- Ensure model deployment name matches `AZURE_OPENAI_MODEL`

**Rate Limiting:**
- PubMed: Respects NCBI guidelines (3 req/sec, 10 with API key)
- Azure OpenAI: Configurable through environment variables

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request