# 🛠️ Data Extraction Framework - Implementation Guide

**Purpose:** Detailed implementation guide for agentic data extraction framework  
**Status:** Implementation Ready  
**Date:** January 2025

---

## 📋 IMPLEMENTATION OVERVIEW

This document provides detailed implementation code for the Data Extraction Framework, addressing all gaps identified in the analysis.

---

## 🏗️ CORE ARCHITECTURE

### File Structure

```
research_framework/
├── extraction_framework/
│   ├── __init__.py
│   ├── extraction_engine.py          # Main extraction interface
│   ├── models.py                     # Pydantic models
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── base_extractor.py         # Base extractor interface
│   │   ├── regex_extractor.py        # Regex-based extraction
│   │   ├── llm_extractor.py          # LLM-assisted extraction
│   │   └── structured_extractor.py   # API-based extraction
│   ├── templates/
│   │   ├── __init__.py
│   │   ├── template_registry.py      # Template registry
│   │   ├── clinical_metrics.py      # Clinical metric templates
│   │   ├── economic_metrics.py       # Economic metric templates
│   │   ├── trial_data.py             # Trial data templates
│   │   └── cohort_data.py            # Cohort data templates
│   ├── validation/
│   │   ├── __init__.py
│   │   ├── validator.py              # Validation engine
│   │   └── rules.py                  # Validation rules
│   └── agents/
│       ├── __init__.py
│       ├── extraction_agent.py       # Agentic extraction
│       └── refinement_strategies.py # Refinement logic
```

---

## 📦 CORE MODELS

### `models.py`

```python
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any, Union, Literal
from enum import Enum

class ExtractionMethod(str, Enum):
    """Extraction methods"""
    REGEX = "regex"
    LLM = "llm"
    STRUCTURED = "structured"
    AUTO = "auto"

class FieldSchema(BaseModel):
    """Schema for a single field to extract"""
    name: str
    type: Literal["str", "int", "float", "bool", "list", "dict"]
    description: str
    patterns: List[str] = Field(default_factory=list)  # Regex patterns
    llm_prompt: Optional[str] = None  # LLM extraction prompt
    required: bool = True
    default: Optional[Any] = None
    validation_rules: Dict[str, Any] = Field(default_factory=dict)
    # e.g., {"min": 0.0, "max": 1.0} for prevention_rate

class ExtractionSchema(BaseModel):
    """Schema defining what to extract"""
    name: str
    description: str
    fields: List[FieldSchema]
    cross_field_validation: Optional[Dict[str, str]] = None
    # e.g., {"prevention_rate <= 1.0": "prevention_rate must be <= 1.0"}

class ExtractionResult(BaseModel):
    """Result of extraction"""
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    method_used: ExtractionMethod
    validation_status: Literal["valid", "invalid", "partial"] = "partial"
    validation_errors: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ExtractionTemplate(BaseModel):
    """Reusable extraction template"""
    name: str
    description: str
    schema: ExtractionSchema
    examples: List[Dict[str, Any]] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
```

---

## 🔧 EXTRACTION ENGINE

### `extraction_engine.py`

```python
from typing import Any, Optional
from .models import ExtractionSchema, ExtractionResult, ExtractionMethod
from .extractors.regex_extractor import RegexExtractor
from .extractors.llm_extractor import LLMExtractor
from .extractors.structured_extractor import StructuredExtractor
from .validation.validator import ExtractionValidator

class ExtractionEngine:
    """Unified extraction engine"""
    
    def __init__(
        self,
        llm_client=None,  # Optional LLM client for LLM extraction
        enable_validation: bool = True
    ):
        self.regex_extractor = RegexExtractor()
        self.llm_extractor = LLMExtractor(llm_client) if llm_client else None
        self.structured_extractor = StructuredExtractor()
        self.validator = ExtractionValidator() if enable_validation else None
    
    async def extract(
        self,
        source: str,  # "pubmed", "clinicaltrials", "text", "json", "cbioportal", "pds"
        content: Any,  # Abstract, trial data, text, JSON, etc.
        schema: ExtractionSchema,
        method: ExtractionMethod = ExtractionMethod.AUTO,
        context: Optional[str] = None
    ) -> ExtractionResult:
        """
        Extract structured data from content based on schema.
        
        Args:
            source: Data source type
            content: Content to extract from
            schema: What to extract
            method: Extraction method (auto chooses best)
            context: Additional context for extraction
        
        Returns:
            ExtractionResult with extracted data and validation
        """
        # Choose extraction method
        if method == ExtractionMethod.AUTO:
            method = self._choose_method(source, content, schema)
        
        # Extract based on method
        if method == ExtractionMethod.REGEX:
            result = await self.regex_extractor.extract(content, schema)
        elif method == ExtractionMethod.LLM:
            if not self.llm_extractor:
                raise ValueError("LLM extractor not available")
            result = await self.llm_extractor.extract(content, schema, context)
        elif method == ExtractionMethod.STRUCTURED:
            result = await self.structured_extractor.extract(source, content, schema)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # Validate if enabled
        if self.validator:
            validation = self.validator.validate(result.data, schema)
            result.validation_status = validation.status
            result.validation_errors = validation.errors
            result.confidence = validation.confidence
        
        return result
    
    def _choose_method(
        self,
        source: str,
        content: Any,
        schema: ExtractionSchema
    ) -> ExtractionMethod:
        """Choose best extraction method automatically"""
        # If structured source, use structured extractor
        if source in ["cbioportal", "project_data_sphere", "clinicaltrials"]:
            return ExtractionMethod.STRUCTURED
        
        # If schema has regex patterns, try regex first
        has_patterns = any(field.patterns for field in schema.fields)
        if has_patterns:
            return ExtractionMethod.REGEX
        
        # Otherwise, use LLM
        if self.llm_extractor:
            return ExtractionMethod.LLM
        
        # Fallback to regex
        return ExtractionMethod.REGEX
```

---

## 📝 EXTRACTORS

### `extractors/regex_extractor.py`

```python
import re
from typing import Any, Dict
from ..models import ExtractionSchema, ExtractionResult, ExtractionMethod

class RegexExtractor:
    """Regex-based extraction"""
    
    async def extract(
        self,
        content: str,
        schema: ExtractionSchema
    ) -> ExtractionResult:
        """Extract using regex patterns"""
        text = str(content).lower() if isinstance(content, str) else str(content)
        extracted = {}
        confidence = 1.0
        
        for field in schema.fields:
            value = None
            
            # Try each pattern
            for pattern in field.patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        value = self._parse_value(match.group(1), field.type)
                        break
                    except (ValueError, IndexError):
                        continue
            
            # Use default if not found
            if value is None and field.default is not None:
                value = field.default
                confidence *= 0.8  # Lower confidence for defaults
            
            extracted[field.name] = value
        
        return ExtractionResult(
            success=len(extracted) > 0,
            data=extracted,
            confidence=confidence,
            method_used=ExtractionMethod.REGEX
        )
    
    def _parse_value(self, value: str, field_type: str) -> Any:
        """Parse extracted string to correct type"""
        value = value.replace(',', '')  # Remove commas
        
        if field_type == "int":
            return int(float(value))  # Handle "123.0" -> 123
        elif field_type == "float":
            return float(value)
        elif field_type == "bool":
            return value.lower() in ["true", "yes", "1"]
        else:
            return value
```

### `extractors/llm_extractor.py`

```python
from typing import Any, Dict, Optional
from ..models import ExtractionSchema, ExtractionResult, ExtractionMethod

class LLMExtractor:
    """LLM-assisted extraction"""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    async def extract(
        self,
        content: str,
        schema: ExtractionSchema,
        context: Optional[str] = None
    ) -> ExtractionResult:
        """Extract using LLM"""
        prompt = self._build_prompt(content, schema, context)
        
        # Call LLM
        response = await self.llm_client.complete(
            prompt,
            response_format={"type": "json_object"}
        )
        
        # Parse response
        try:
            extracted = self._parse_llm_response(response, schema)
            confidence = 0.9  # LLM extraction confidence
        except Exception as e:
            return ExtractionResult(
                success=False,
                data={},
                confidence=0.0,
                method_used=ExtractionMethod.LLM,
                validation_errors=[f"LLM parsing error: {e}"]
            )
        
        return ExtractionResult(
            success=True,
            data=extracted,
            confidence=confidence,
            method_used=ExtractionMethod.LLM
        )
    
    def _build_prompt(
        self,
        content: str,
        schema: ExtractionSchema,
        context: Optional[str]
    ) -> str:
        """Build LLM extraction prompt"""
        fields_desc = "\n".join([
            f"- {f.name} ({f.type}): {f.description}"
            for f in schema.fields
        ])
        
        prompt = f"""Extract structured data from the following text.

Schema: {schema.name}
Description: {schema.description}

Fields to extract:
{fields_desc}

{context or ""}

Text:
{content}

Return a JSON object with the extracted fields. Use null for missing values."""
        
        return prompt
    
    def _parse_llm_response(
        self,
        response: str,
        schema: ExtractionSchema
    ) -> Dict[str, Any]:
        """Parse LLM JSON response"""
        import json
        data = json.loads(response)
        
        # Type conversion
        result = {}
        for field in schema.fields:
            value = data.get(field.name, field.default)
            if value is not None:
                result[field.name] = self._convert_type(value, field.type)
            elif field.required:
                raise ValueError(f"Required field {field.name} missing")
        
        return result
    
    def _convert_type(self, value: Any, field_type: str) -> Any:
        """Convert value to correct type"""
        if field_type == "int":
            return int(value)
        elif field_type == "float":
            return float(value)
        elif field_type == "bool":
            return bool(value)
        else:
            return value
```

---

## 📚 TEMPLATE LIBRARY

### `templates/clinical_metrics.py`

```python
from ..models import ExtractionSchema, FieldSchema, ExtractionTemplate

# Prevention Rate Template
PREVENTION_RATE_SCHEMA = ExtractionSchema(
    name="prevention_rate",
    description="Extract prevention rates and related metrics from clinical text",
    fields=[
        FieldSchema(
            name="prevention_rate",
            type="float",
            description="Percentage of toxicities prevented (0.0-1.0)",
            patterns=[
                r'prevent[ed|ion|ing].*?(\d+(?:\.\d+)?)\s*%',
                r'(\d+(?:\.\d+)?)\s*%.*?prevent[ed|ion|ing]',
                r'reduction.*?(\d+(?:\.\d+)?)\s*%.*?toxicit',
            ],
            llm_prompt="Extract the percentage of toxicities prevented. Convert percentage to decimal (e.g., 83.1% -> 0.831)",
            validation_rules={"min": 0.0, "max": 1.0}
        ),
        FieldSchema(
            name="sample_size",
            type="int",
            description="Number of patients in study",
            patterns=[
                r'\bn\s*=\s*(\d+(?:,\d+)?)',
                r'(\d+(?:,\d+)?)\s*patient',
                r'enrolled.*?(\d+(?:,\d+)?)',
            ],
            llm_prompt="Extract the sample size (N) from the text",
            validation_rules={"min": 1}
        ),
        FieldSchema(
            name="toxicity_reduction_percent",
            type="float",
            description="Percentage reduction in toxicity",
            patterns=[
                r'toxicit.*?reduction.*?(\d+(?:\.\d+)?)\s*%',
                r'reduction.*?(\d+(?:\.\d+)?)\s*%.*?severe.*?toxicit',
            ],
            required=False
        ),
    ]
)

PREVENTION_RATE_TEMPLATE = ExtractionTemplate(
    name="prevention_rate",
    description="Extract prevention rates from clinical literature",
    schema=PREVENTION_RATE_SCHEMA,
    examples=[
        {
            "text": "DPYD testing prevented 83.1% of severe toxicities (n=563)",
            "expected": {
                "prevention_rate": 0.831,
                "sample_size": 563
            }
        }
    ],
    tags=["clinical", "prevention", "toxicity"]
)
```

### `templates/economic_metrics.py`

```python
from ..models import ExtractionSchema, FieldSchema, ExtractionTemplate

COST_DATA_SCHEMA = ExtractionSchema(
    name="cost_data",
    description="Extract cost-effectiveness data from clinical trials and literature",
    fields=[
        FieldSchema(
            name="cost_savings",
            type="float",
            description="Total cost savings in USD",
            patterns=[
                r'\$[\d,]+(?:\.\d+)?\s*(?:million|M|thousand|K)?',
                r'cost.*?saving.*?\$[\d,]+(?:\.\d+)?',
            ],
            llm_prompt="Extract total cost savings in USD. Convert millions to actual dollars (e.g., $4M -> 4000000)",
            required=False
        ),
        FieldSchema(
            name="cost_per_patient",
            type="float",
            description="Cost per patient in USD",
            patterns=[
                r'\$[\d,]+(?:\.\d+)?\s*per\s*patient',
                r'cost.*?[\d,]+(?:\.\d+)?\s*per\s*patient',
            ],
            required=False
        ),
        FieldSchema(
            name="cost_per_qaly",
            type="float",
            description="Cost per QALY in USD",
            patterns=[
                r'\$[\d,]+(?:\.\d+)?\s*per\s*QALY',
                r'[\d,]+(?:\.\d+)?\s*USD.*?QALY',
            ],
            required=False
        ),
    ]
)

COST_DATA_TEMPLATE = ExtractionTemplate(
    name="cost_data",
    description="Extract cost-effectiveness metrics",
    schema=COST_DATA_SCHEMA,
    tags=["economic", "cost", "qaly"]
)
```

---

## ✅ VALIDATION

### `validation/validator.py`

```python
from typing import Dict, List, Any
from ..models import ExtractionSchema, FieldSchema

class ValidationResult:
    """Validation result"""
    def __init__(self):
        self.status: str = "valid"  # "valid", "invalid", "partial"
        self.errors: List[str] = []
        self.confidence: float = 1.0

class ExtractionValidator:
    """Validate extracted data"""
    
    def validate(
        self,
        data: Dict[str, Any],
        schema: ExtractionSchema
    ) -> ValidationResult:
        """Validate extracted data against schema"""
        result = ValidationResult()
        
        # Check required fields
        for field in schema.fields:
            if field.required and field.name not in data:
                result.errors.append(f"Required field {field.name} missing")
                result.status = "invalid"
        
        # Validate field values
        for field in schema.fields:
            if field.name in data:
                value = data[field.name]
                
                # Type validation
                if not self._validate_type(value, field.type):
                    result.errors.append(
                        f"Field {field.name}: expected {field.type}, got {type(value).__name__}"
                    )
                    result.status = "invalid"
                
                # Range validation
                if field.validation_rules:
                    if "min" in field.validation_rules:
                        if value < field.validation_rules["min"]:
                            result.errors.append(
                                f"Field {field.name}: value {value} < min {field.validation_rules['min']}"
                            )
                            result.status = "invalid"
                    
                    if "max" in field.validation_rules:
                        if value > field.validation_rules["max"]:
                            result.errors.append(
                                f"Field {field.name}: value {value} > max {field.validation_rules['max']}"
                            )
                            result.status = "invalid"
        
        # Cross-field validation
        if schema.cross_field_validation:
            for rule, message in schema.cross_field_validation.items():
                if not self._evaluate_rule(rule, data):
                    result.errors.append(message)
                    result.status = "invalid"
        
        # Calculate confidence
        if result.status == "valid":
            result.confidence = 1.0
        elif result.status == "partial":
            result.confidence = 0.7
        else:
            result.confidence = 0.3
        
        return result
    
    def _validate_type(self, value: Any, field_type: str) -> bool:
        """Validate value type"""
        type_map = {
            "str": str,
            "int": int,
            "float": (int, float),  # Accept int as float
            "bool": bool,
            "list": list,
            "dict": dict,
        }
        expected_type = type_map.get(field_type)
        return isinstance(value, expected_type) if expected_type else True
    
    def _evaluate_rule(self, rule: str, data: Dict[str, Any]) -> bool:
        """Evaluate cross-field validation rule"""
        # Simple rule evaluation (e.g., "prevention_rate <= 1.0")
        try:
            return eval(rule, {"__builtins__": {}}, data)
        except:
            return False
```

---

## 🤖 AGENTIC EXTRACTION

### `agents/extraction_agent.py`

```python
from typing import Optional
from ..extraction_engine import ExtractionEngine
from ..models import ExtractionSchema, ExtractionResult, ExtractionMethod

class ExtractionAgent:
    """Agentic extraction with automatic refinement"""
    
    def __init__(self, extraction_engine: ExtractionEngine):
        self.engine = extraction_engine
    
    async def extract_with_refinement(
        self,
        source: str,
        content: Any,
        schema: ExtractionSchema,
        max_refinements: int = 3,
        context: Optional[str] = None
    ) -> ExtractionResult:
        """
        Extract with automatic refinement:
        1. Try regex extraction
        2. If validation fails, try LLM extraction
        3. If still fails, refine and retry
        """
        # Try regex first (fastest)
        result = await self.engine.extract(
            source=source,
            content=content,
            schema=schema,
            method=ExtractionMethod.REGEX,
            context=context
        )
        
        # If validation passed, return
        if result.validation_status == "valid":
            return result
        
        # Try LLM extraction if available
        if self.engine.llm_extractor:
            llm_result = await self.engine.extract(
                source=source,
                content=content,
                schema=schema,
                method=ExtractionMethod.LLM,
                context=context
            )
            
            # Use LLM result if better
            if llm_result.validation_status == "valid" or \
               llm_result.confidence > result.confidence:
                result = llm_result
        
        # Refinement loop
        for i in range(max_refinements):
            if result.validation_status == "valid":
                break
            
            # Refine context and retry
            refined_context = self._refine_context(
                content, schema, result.validation_errors, context
            )
            
            if self.engine.llm_extractor:
                result = await self.engine.extract(
                    source=source,
                    content=content,
                    schema=schema,
                    method=ExtractionMethod.LLM,
                    context=refined_context
                )
        
        return result
    
    def _refine_context(
        self,
        content: str,
        schema: ExtractionSchema,
        errors: list,
        original_context: Optional[str]
    ) -> str:
        """Refine extraction context based on validation errors"""
        error_summary = "\n".join([f"- {e}" for e in errors])
        
        refined = f"""Previous extraction attempt had these errors:
{error_summary}

Please extract the data more carefully, paying attention to:
- Type conversions (percentages to decimals, etc.)
- Missing required fields
- Range constraints

{original_context or ""}"""
        
        return refined
```

---

## 🔄 INTEGRATION WITH RESEARCH FRAMEWORK

### Update `orchestrator.py`

```python
from extraction_framework import ExtractionEngine, ExtractionTemplate
from extraction_framework.templates import PREVENTION_RATE_TEMPLATE, COST_DATA_TEMPLATE

class ResearchOrchestrator:
    def __init__(self):
        # ... existing init ...
        self.extraction_engine = ExtractionEngine(llm_client=self.llm_client)
    
    async def search_with_extraction(
        self,
        query: str,
        sources: List[str],
        extract_template: ExtractionTemplate,
        synthesize: bool = True
    ) -> ResearchResult:
        """
        Search + Extract in one call
        
        Example:
            result = await orchestrator.search_with_extraction(
                query="DPYD toxicity prevention",
                sources=["pubmed"],
                extract_template=PREVENTION_RATE_TEMPLATE
            )
        """
        # Search
        search_result = await self.search(query, sources, synthesize=False)
        
        # Extract from each source
        extracted_data = []
        for source_result in search_result.sources:
            # Extract from abstracts/titles
            for item in source_result.results:
                content = item.get("abstract", "") or item.get("title", "")
                
                extracted = await self.extraction_engine.extract(
                    source=source_result.agent_type,
                    content=content,
                    schema=extract_template.schema,
                    method=ExtractionMethod.AUTO
                )
                
                if extracted.success:
                    extracted_data.append({
                        "source": source_result.agent_type,
                        "item": item,
                        "extracted": extracted.data,
                        "confidence": extracted.confidence
                    })
        
        # Synthesize if requested
        synthesis = None
        if synthesize and extracted_data:
            synthesis = await self._synthesize_extracted_data(extracted_data)
        
        return ResearchResult(
            query=query,
            sources=search_result.sources,
            extracted_data=extracted_data,
            synthesis=synthesis
        )
```

---

## 📖 USAGE EXAMPLES

### Example 1: Extract Prevention Rates

```python
from extraction_framework import ExtractionEngine
from extraction_framework.templates import PREVENTION_RATE_TEMPLATE

engine = ExtractionEngine()

# Extract from PubMed abstract
abstract = "DPYD testing prevented 83.1% of severe toxicities in 563 patients."

result = await engine.extract(
    source="pubmed",
    content=abstract,
    schema=PREVENTION_RATE_TEMPLATE.schema,
    method=ExtractionMethod.AUTO
)

print(result.data)
# {
#   "prevention_rate": 0.831,
#   "sample_size": 563,
#   "toxicity_reduction_percent": None
# }
print(f"Confidence: {result.confidence}")
print(f"Validation: {result.validation_status}")
```

### Example 2: Extract Cost Data from Trials

```python
from extraction_framework import ExtractionEngine
from extraction_framework.templates import COST_DATA_TEMPLATE

engine = ExtractionEngine()

trial_data = {
    "title": "Cost-effectiveness of PGx testing",
    "outcome_measures": [
        {
            "measure": "Cost savings",
            "description": "Total cost savings of $4M per year"
        }
    ]
}

result = await engine.extract(
    source="clinicaltrials",
    content=trial_data,
    schema=COST_DATA_TEMPLATE.schema,
    method=ExtractionMethod.STRUCTURED
)
```

### Example 3: Agentic Extraction with Refinement

```python
from extraction_framework import ExtractionEngine, ExtractionAgent
from extraction_framework.templates import PREVENTION_RATE_TEMPLATE

engine = ExtractionEngine(llm_client=llm_client)
agent = ExtractionAgent(engine)

# Complex text that might need refinement
text = "The study showed significant reduction in adverse events..."

result = await agent.extract_with_refinement(
    source="pubmed",
    content=text,
    schema=PREVENTION_RATE_TEMPLATE.schema,
    max_refinements=3
)
```

---

## 🚀 MIGRATION GUIDE

### Migrating Existing Scripts

**Before (extract_prevention_rates_from_pubmed.py):**
```python
def extract_prevention_data(abstract: str, title: str):
    text = f"{title} {abstract}".lower()
    prevention_patterns = [
        r'prevent[ed|ion|ing].*?(\d+(?:\.\d+)?)\s*%',
        # ... manual regex
    ]
    # ... manual extraction
```

**After (Using Framework):**
```python
from extraction_framework import ExtractionEngine
from extraction_framework.templates import PREVENTION_RATE_TEMPLATE

engine = ExtractionEngine()

def extract_prevention_data(abstract: str, title: str):
    result = await engine.extract(
        source="pubmed",
        content=f"{title} {abstract}",
        schema=PREVENTION_RATE_TEMPLATE.schema
    )
    return result.data
```

---

## ✅ NEXT STEPS

1. **Implement Core Engine** - Start with `extraction_engine.py`
2. **Create Templates** - Start with `PREVENTION_RATE_TEMPLATE`
3. **Test on Existing Data** - Validate against current scripts
4. **Integrate with Research Framework** - Update `orchestrator.py`
5. **Migrate Existing Scripts** - Replace manual extraction

---

**Status:** Ready for Implementation  
**Estimated Time:** 2-3 weeks (phased approach)

