# 🎯 Agentic Data Extraction Framework - Comprehensive Plan

**Goal:** Make data extraction easier, reusable, and agentic  
**Status:** Planning Phase  
**Date:** January 2025

---

## 📊 CURRENT STATE ANALYSIS

### What We Have (Patterns Identified)

#### 1. **Regex-Based Extraction** (Manual, Hard to Maintain)
**Examples:**
- `extract_prevention_rates_from_pubmed.py` - Regex patterns for percentages, sample sizes
- `extract_cost_data_from_trials.py` - Keyword matching for cost outcomes
- Manual pattern definitions, no reusability

**Problems:**
- ❌ Hard-coded regex patterns
- ❌ No validation of extracted values
- ❌ No handling of edge cases
- ❌ Each script is custom-built

#### 2. **Structured Data Extraction** (Partially Automated)
**Examples:**
- `extract_tcga_outcomes.py` - cBioPortal API → JSON
- `extract_pgx_validation_cohort.py` - Multi-source → validation schema
- `surrogate_validator.py` - End-to-end validation pipeline

**Problems:**
- ⚠️ Each extraction is custom
- ⚠️ No reusable extraction templates
- ⚠️ No LLM assistance for complex cases

#### 3. **Multi-Step Extraction Workflows** (Manual Orchestration)
**Examples:**
- Search PubMed → Extract prevention rates → Validate → Aggregate
- Search ClinicalTrials.gov → Filter by keywords → Extract outcomes → Transform

**Problems:**
- ⚠️ Manual workflow orchestration
- ⚠️ No agentic decision-making
- ⚠️ No automatic retry/refinement

---

## 🎯 VISION: Agentic Data Extraction Framework

### Core Principles

1. **Declarative Extraction** - Define what to extract, not how
2. **Multi-Modal Extraction** - Regex + LLM + Structured APIs
3. **Automatic Validation** - Validate extracted data against schemas
4. **Reusable Templates** - Common extraction patterns as templates
5. **Agentic Refinement** - LLM agents refine extraction when needed

---

## 🏗️ ARCHITECTURE

### Component 1: Extraction Engine

**Purpose:** Unified interface for all extraction methods

```python
class ExtractionEngine:
    """Unified extraction engine supporting multiple methods"""
    
    async def extract(
        self,
        source: str,  # "pubmed", "clinicaltrials", "text", "json"
        content: Any,  # Abstract, trial data, text, JSON
        schema: ExtractionSchema,  # What to extract
        method: str = "auto"  # "regex", "llm", "structured", "auto"
    ) -> ExtractionResult:
        """
        Extract structured data from unstructured/semi-structured sources.
        
        Methods:
        - "regex": Fast, pattern-based (for known formats)
        - "llm": LLM-assisted (for complex/ambiguous cases)
        - "structured": API-based (for structured sources)
        - "auto": Choose best method automatically
        """
```

### Component 2: Extraction Templates

**Purpose:** Reusable extraction patterns

```python
# Template: Prevention Rate Extraction
PREVENTION_RATE_TEMPLATE = ExtractionTemplate(
    name="prevention_rate",
    schema={
        "prevention_rate": {
            "type": "float",
            "range": [0.0, 1.0],
            "patterns": [
                r'prevent[ed|ion|ing].*?(\d+(?:\.\d+)?)\s*%',
                r'(\d+(?:\.\d+)?)\s*%.*?prevent[ed|ion|ing]',
            ],
            "llm_prompt": "Extract the percentage of toxicities prevented from this text"
        },
        "sample_size": {
            "type": "int",
            "patterns": [r'\bn\s*=\s*(\d+(?:,\d+)?)'],
            "llm_prompt": "Extract the sample size (N) from this text"
        }
    },
    validation_rules={
        "prevention_rate": lambda x: 0.0 <= x <= 1.0,
        "sample_size": lambda x: x > 0
    }
)

# Template: Cost Data Extraction
COST_DATA_TEMPLATE = ExtractionTemplate(
    name="cost_data",
    schema={
        "cost_savings": {
            "type": "float",
            "patterns": [r'\$[\d,]+(?:\.\d+)?'],
            "llm_prompt": "Extract cost savings in USD"
        },
        "cost_per_patient": {
            "type": "float",
            "patterns": [r'\$[\d,]+(?:\.\d+)?\s*per\s*patient'],
        }
    }
)
```

### Component 3: LLM-Assisted Extractor

**Purpose:** Handle complex/ambiguous extraction cases

```python
class LLMExtractor:
    """LLM-assisted extraction for complex cases"""
    
    async def extract_with_llm(
        self,
        text: str,
        schema: ExtractionSchema,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Use LLM to extract structured data from text.
        
        Example:
        - Extract prevention rate from ambiguous text
        - Extract multiple related values (prevention rate + sample size + confidence)
        - Handle edge cases (percentages vs. ratios, different units)
        """
        prompt = self._build_extraction_prompt(text, schema, context)
        response = await self.llm_client.complete(prompt)
        return self._parse_llm_response(response, schema)
```

### Component 4: Validation Layer

**Purpose:** Validate extracted data against schemas

```python
class ExtractionValidator:
    """Validate extracted data"""
    
    def validate(
        self,
        extracted: Dict[str, Any],
        schema: ExtractionSchema
    ) -> ValidationResult:
        """
        Validate extracted data:
        - Type checking
        - Range validation
        - Required fields
        - Cross-field validation (e.g., prevention_rate <= 1.0)
        """
```

### Component 5: Agentic Refinement

**Purpose:** Agents refine extraction when validation fails

```python
class ExtractionAgent:
    """Agentic extraction with automatic refinement"""
    
    async def extract_with_refinement(
        self,
        source: str,
        content: Any,
        schema: ExtractionSchema,
        max_refinements: int = 3
    ) -> ExtractionResult:
        """
        Extract data with automatic refinement:
        1. Try regex extraction
        2. If validation fails, try LLM extraction
        3. If still fails, refine prompt and retry
        4. Return best result with confidence score
        """
```

---

## 📋 EXTRACTION TEMPLATES LIBRARY

### Template Categories

#### 1. **Clinical Metrics**
- Prevention rates
- Toxicity reduction rates
- Sample sizes
- Confidence intervals
- P-values

#### 2. **Economic Metrics**
- Cost savings
- Cost per patient
- Cost per QALY
- Hospitalization costs

#### 3. **Trial Data**
- Outcome measures
- Enrollment numbers
- Phase information
- Status information

#### 4. **Cohort Data**
- Patient demographics
- Biomarker values
- Outcome labels
- Treatment history

#### 5. **Literature Data**
- Publication metadata
- Author information
- Citation counts
- Keywords

---

## 🔄 INTEGRATION WITH RESEARCH FRAMEWORK

### How It Fits

```python
# Research Framework uses Extraction Framework
from research_framework import ResearchOrchestrator
from extraction_framework import ExtractionEngine

class ResearchOrchestrator:
    def __init__(self):
        self.extraction_engine = ExtractionEngine()
    
    async def search_with_extraction(
        self,
        query: str,
        sources: List[str],
        extract_schema: ExtractionSchema
    ) -> ResearchResult:
        """
        Search + Extract in one call:
        1. Search PubMed/ClinicalTrials.gov
        2. Extract structured data from results
        3. Validate extracted data
        4. Return structured results
        """
        # Search
        search_results = await self.search(query, sources)
        
        # Extract
        extracted_data = []
        for result in search_results:
            extracted = await self.extraction_engine.extract(
                source=result.source,
                content=result.content,
                schema=extract_schema,
                method="auto"
            )
            extracted_data.append(extracted)
        
        return ResearchResult(
            query=query,
            sources=search_results,
            extracted_data=extracted_data
        )
```

---

## 🎯 USE CASES

### Use Case 1: Extract Prevention Rates from PubMed

**Current (Manual):**
```python
# extract_prevention_rates_from_pubmed.py
def extract_prevention_data(abstract: str, title: str):
    text = f"{title} {abstract}".lower()
    prevention_patterns = [
        r'prevent[ed|ion|ing].*?(\d+(?:\.\d+)?)\s*%',
        r'(\d+(?:\.\d+)?)\s*%.*?prevent[ed|ion|ing]',
    ]
    # ... manual regex matching
```

**With Framework:**
```python
from extraction_framework import ExtractionEngine, PREVENTION_RATE_TEMPLATE

engine = ExtractionEngine()
result = await engine.extract(
    source="pubmed",
    content=abstract,
    schema=PREVENTION_RATE_TEMPLATE,
    method="auto"  # Tries regex first, LLM if needed
)

# Result includes:
# - prevention_rate: 0.831
# - sample_size: 563
# - confidence: 0.95
# - validation_status: "valid"
```

### Use Case 2: Extract Cost Data from ClinicalTrials.gov

**Current (Manual):**
```python
# extract_cost_data_from_trials.py
cost_keywords = ["cost", "economic", "saving", "hospitalization"]
if any(keyword in measure for keyword in cost_keywords):
    # ... manual keyword matching
```

**With Framework:**
```python
from extraction_framework import ExtractionEngine, COST_DATA_TEMPLATE

engine = ExtractionEngine()
result = await engine.extract(
    source="clinicaltrials",
    content=trial_data,
    schema=COST_DATA_TEMPLATE,
    method="auto"
)

# Result includes:
# - cost_savings: 360000.0
# - cost_per_patient: 2500.0
# - validation_status: "valid"
```

### Use Case 3: Extract Cohort Data from Multiple Sources

**Current (Custom Scripts):**
- `extract_tcga_outcomes.py` - Custom cBioPortal extraction
- `extract_pgx_validation_cohort.py` - Custom PGx extraction
- Each script is custom-built

**With Framework:**
```python
from extraction_framework import ExtractionEngine, COHORT_DATA_TEMPLATE

engine = ExtractionEngine()

# Extract from cBioPortal
cbioportal_result = await engine.extract(
    source="cbioportal",
    content=study_data,
    schema=COHORT_DATA_TEMPLATE,
    method="structured"  # Use API directly
)

# Extract from Project Data Sphere
pds_result = await engine.extract(
    source="project_data_sphere",
    content=caslib_data,
    schema=COHORT_DATA_TEMPLATE,
    method="structured"
)

# Both results follow same schema, can be merged
```

---

## 🚀 IMPLEMENTATION PLAN

### Phase 1: Core Extraction Engine (Week 1)

**Deliverables:**
1. `ExtractionEngine` class
2. `ExtractionSchema` Pydantic models
3. `ExtractionResult` models
4. Basic regex extractor
5. Basic LLM extractor

**Files:**
- `extraction_framework/extraction_engine.py`
- `extraction_framework/models.py`
- `extraction_framework/extractors/regex_extractor.py`
- `extraction_framework/extractors/llm_extractor.py`

### Phase 2: Template Library (Week 1-2)

**Deliverables:**
1. `ExtractionTemplate` class
2. Template library (10+ common templates)
3. Template registry
4. Template validation

**Files:**
- `extraction_framework/templates/__init__.py`
- `extraction_framework/templates/clinical_metrics.py`
- `extraction_framework/templates/economic_metrics.py`
- `extraction_framework/templates/trial_data.py`
- `extraction_framework/templates/cohort_data.py`

### Phase 3: Validation Layer (Week 2)

**Deliverables:**
1. `ExtractionValidator` class
2. Schema validation
3. Range validation
4. Cross-field validation
5. Validation error reporting

**Files:**
- `extraction_framework/validation.py`
- `extraction_framework/validators/`

### Phase 4: Agentic Refinement (Week 2-3)

**Deliverables:**
1. `ExtractionAgent` class
2. Automatic method selection
3. Refinement logic
4. Confidence scoring
5. Error recovery

**Files:**
- `extraction_framework/agents/extraction_agent.py`
- `extraction_framework/agents/refinement_strategies.py`

### Phase 5: Integration (Week 3)

**Deliverables:**
1. Integration with Research Framework
2. Integration with existing scripts
3. Migration guide
4. Usage examples

**Files:**
- `extraction_framework/integration/research_framework.py`
- `extraction_framework/examples/`

---

## 📊 GAP ANALYSIS

### Current Gaps

| Gap | Impact | Solution |
|-----|--------|----------|
| **Manual regex patterns** | High maintenance | Template library |
| **No validation** | Data quality issues | Validation layer |
| **No LLM assistance** | Can't handle complex cases | LLM extractor |
| **No reusability** | Duplicate code | Template system |
| **No agentic refinement** | Manual retry | Agentic refinement |
| **No unified interface** | Inconsistent APIs | ExtractionEngine |

### What This Framework Enables

1. **Easier Extraction** - Declarative schemas, not manual regex
2. **Better Quality** - Automatic validation
3. **Handles Edge Cases** - LLM assistance for complex cases
4. **Reusable** - Templates for common patterns
5. **Agentic** - Automatic refinement and retry
6. **Unified** - One interface for all extraction

---

## 🎯 SUCCESS METRICS

### Phase 1-2 (Core + Templates)
- ✅ 10+ extraction templates
- ✅ Regex + LLM extractors working
- ✅ Basic validation layer

### Phase 3-4 (Validation + Agentic)
- ✅ Automatic validation
- ✅ Agentic refinement working
- ✅ 90%+ extraction accuracy on test cases

### Phase 5 (Integration)
- ✅ Research Framework integration
- ✅ 3+ existing scripts migrated
- ✅ Documentation complete

---

## 📚 NEXT STEPS

1. **Review this plan** - Get feedback on architecture
2. **Start Phase 1** - Build core extraction engine
3. **Create templates** - Start with prevention_rate template
4. **Test on existing data** - Validate against current scripts
5. **Iterate** - Refine based on real usage

---

**Status:** Ready for implementation  
**Priority:** High (enables easier data acquisition)  
**Estimated Effort:** 3 weeks (phased approach)

