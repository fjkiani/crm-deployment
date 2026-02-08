# Research Framework - Usage Guide

**Quick start guide for using the Research Framework**

---

## 🚀 **Quick Start**

### **1. Basic Search**

```python
from research_framework import ResearchOrchestrator

# Initialize framework
framework = ResearchOrchestrator()

# Simple search
result = await framework.search(
    query="pharmacogenomics DPYD toxicity prevention",
    sources=['pubmed', 'clinical_trials'],
    synthesize=True
)

# Access results
print(result.synthesis.summary)  # Synthesized summary
print(result.sources[0].results)  # PubMed results
print(result.sources[1].results)  # Clinical trials results
```

---

### **2. Using a Domain Agent**

```python
from research_framework.agents.pgx_agent import PGxValidationAgent

# Initialize PGx agent
pgx_agent = PGxValidationAgent()

# Validate a claim
validation = await pgx_agent.validate_claim(
    claim="DPYD testing prevents 95% of fluoropyrimidine toxicity",
    genes=["DPYD"],
    drugs=["fluorouracil", "capecitabine"]
)

print(f"Validated: {validation['validated']}")
print(f"Confidence: {validation['confidence']}")
print(f"Evidence: {validation['evidence_count']} sources")
```

---

### **3. Structured Data Extraction**

```python
result = await framework.search(
    query="DPYD testing prevention rates",
    extract_structured={
        "prevention_rate": "extract percentage of toxicity prevented",
        "sample_size": "extract number of patients in study",
        "study_type": "extract study design (randomized, observational, etc.)",
        "publication_year": "extract year of publication"
    }
)

# Access structured data
if result.structured_data:
    print(result.structured_data.data)
    # {
    #   "prevention_rate": "95%",
    #   "sample_size": "150 patients",
    #   "study_type": "randomized controlled trial",
    #   "publication_year": "2023"
    # }
```

---

### **4. Multi-Query Search**

```python
# Search multiple related queries
queries = [
    "DPYD toxicity prevention",
    "DPYD cost-effectiveness",
    "DPYD clinical implementation"
]

results = await framework.multi_source_search(
    queries=queries,
    sources=['pubmed', 'clinical_trials'],
    synthesis=True
)

# Results for each query
for i, result in enumerate(results.results):
    print(f"Query {i+1}: {results.queries[i]}")
    print(f"Summary: {result.synthesis.summary if result.synthesis else 'N/A'}")
```

---

## 🎯 **Common Patterns**

### **Pattern 1: Literature Review**

```python
result = await framework.search(
    query="systematic review pharmacogenomics implementation",
    sources=['pubmed'],
    max_results=50,
    include_fulltext=True,
    synthesize=True
)

# Get comprehensive review
review = result.synthesis.summary
key_findings = result.synthesis.key_findings
```

---

### **Pattern 2: Trial Discovery**

```python
result = await framework.search(
    query="Phase 3 pharmacogenomics testing cancer",
    sources=['clinical_trials'],
    max_results=20
)

# Get trial details
trials = result.get_source_result('clinical_trials')
for trial in trials.results:
    print(f"Trial: {trial.get('title', 'N/A')}")
    print(f"NCT ID: {trial.get('nct_id', 'N/A')}")
```

---

### **Pattern 3: Evidence Synthesis**

```python
# Search multiple sources
result = await framework.search(
    query="pharmacogenomics clinical outcomes",
    sources=['pubmed', 'clinical_trials'],
    synthesize=True  # Automatically synthesizes across sources
)

# Access synthesis
if result.synthesis:
    print("Unified Summary:", result.synthesis.summary)
    print("Key Findings:", result.synthesis.key_findings)
    print("Consensus Points:", result.synthesis.consensus_points)
    print("Contradictions:", result.synthesis.contradictions)
```

---

## 🔧 **Creating Your Own Domain Agent**

### **Step 1: Extend BaseDomainAgent**

```python
from research_framework.agents.base_agent import BaseDomainAgent
from research_framework.models import ResearchResult

class MyDomainAgent(BaseDomainAgent):
    def _get_domain_name(self) -> str:
        return "my_domain"
    
    async def my_domain_method(self, query: str):
        # Use framework for research
        result = await self.framework.search(
            query=query,
            sources=['pubmed', 'clinical_trials'],
            synthesize=True
        )
        
        # Interpret in domain context
        return self._interpret_for_my_domain(result)
    
    def _interpret_for_my_domain(self, result: ResearchResult):
        # Domain-specific interpretation
        return {
            'domain_insight': '...',
            'result': result
        }
```

### **Step 2: Use Your Agent**

```python
agent = MyDomainAgent()
insight = await agent.my_domain_method("my query")
```

---

## 📊 **Result Structure**

### **ResearchResult**

```python
result = await framework.search(...)

# result.query - Original query
# result.sources - List of AgentResult (one per source)
# result.synthesis - Synthesis object (if synthesize=True)
# result.structured_data - StructuredData object (if extract_structured provided)
# result.metadata - Framework metadata
# result.timestamp - When search was executed
```

### **AgentResult** (per source)

```python
source_result = result.sources[0]

# source_result.agent_type - 'pubmed' or 'clinical_trials'
# source_result.query - Query that was executed
# source_result.results - List of raw results
# source_result.summary - Agent-generated summary
# source_result.metadata - Agent-specific metadata
```

### **Synthesis**

```python
synthesis = result.synthesis

# synthesis.summary - Unified summary
# synthesis.key_findings - List of key findings
# synthesis.consensus_points - Points of consensus
# synthesis.contradictions - Contradictory findings
# synthesis.confidence - Overall confidence (0-1)
```

---

## ⚙️ **Configuration**

### **Environment Variables**

The framework uses BioMed-MCP agents, which require:

```bash
# Standard OpenAI API (recommended)
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.7

# OR Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-azure-key
OPENAI_API_VERSION=2025-01-01-preview

# PubMed (required)
PUBMED_EMAIL=your-email@example.com
```

---

## 🎓 **Best Practices**

1. **Use Domain Agents**: Create domain-specific agents for specialized use cases
2. **Enable Synthesis**: Always use `synthesize=True` for multi-source searches
3. **Extract Structured Data**: Use `extract_structured` for specific data points
4. **Reuse Framework Instance**: Create one framework instance and reuse it
5. **Handle Errors**: Framework continues with other sources if one fails

---

## 🆘 **Troubleshooting**

### **Error: "BioMed-MCP agents not found"**
- Ensure BioMed-MCP is installed in `mcp_servers/BioMed-MCP/`
- Check that environment variables are set

### **Error: "Unknown source"**
- Available sources: `['pubmed', 'clinical_trials']`
- Check source name spelling

### **No Results**
- Try broader queries
- Check that sources are available
- Verify API keys are configured

---

**For more details, see `BIOMED_AGENTIC_FRAMEWORK_PRODUCT.md`**

