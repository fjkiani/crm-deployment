# Getting Started with CRM Intelligence System

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd scalable_crm_intelligence

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export TAVILY_API_KEY="your_api_key_here"
export CRM_ENV="development"
```

### 2. Configuration

```bash
# Initialize configuration
python -m config.configuration_manager init

# Configure for your environment
python -m api.cli.main config set --key tavily.api_key --value "your_key"
```

### 3. Run Intelligence Gathering

```bash
# Gather company intelligence
python -m api.cli.main intel "3EDGE Asset Management" --types company executives

# Process data file
python -m api.cli.main process --input-file data/leads.csv
```

## Component Usage Examples

### Using Individual Components

```python
from components.intelligence.company_intelligence import CompanyIntelligenceComponent
from config.configuration_manager import ConfigurationManager

# Setup
config_manager = ConfigurationManager(Path("config"))
component_config = config_manager.get_component_config("company_intelligence")

# Initialize component
component = CompanyIntelligenceComponent(component_config)
await component.initialize()

# Gather intelligence
result = await component.gather_intelligence("Company Name", {})
```

### Using Workflow Orchestrator

```python
from orchestration.workflow_orchestrator import WorkflowOrchestrator
from orchestration.workflow_orchestrator import WorkflowConfig, WorkflowStep

# Setup orchestrator
orchestrator = WorkflowOrchestrator()

# Register components
orchestrator.register_component("company_intel", company_component)
orchestrator.register_component("executive_intel", executive_component)

# Define workflow
workflow = WorkflowConfig(
    name="complete_intelligence",
    description="Complete intelligence gathering workflow",
    steps=[
        WorkflowStep(
            component_name="company_intel",
            input_mapping={"company_name": "input.company"},
            output_mapping={"company_data": "company_info"}
        ),
        WorkflowStep(
            component_name="executive_intel", 
            input_mapping={"company_name": "input.company"},
            output_mapping={"executive_data": "executives"},
            dependencies=["company_intel"]
        )
    ]
)

orchestrator.register_workflow(workflow)

# Execute workflow
result = await orchestrator.execute_workflow("complete_intelligence", {
    "company": "Target Company"
})
```

## Advanced Usage

### Custom Components

```python
from core.interfaces.intelligence import IntelligenceComponent

class CustomIntelligenceComponent(IntelligenceComponent):
    async def gather_intelligence(self, target: str, context: Dict[str, Any]) -> Dict[str, Any]:
        # Your custom intelligence logic
        return {"custom_data": "gathered"}
```

### Custom Workflows

```yaml
# workflow.yaml
name: custom_workflow
description: Custom intelligence workflow
steps:
  - component: company_intel
    input_mapping:
      company_name: input.company
    output_mapping:
      company_data: company_info
      
  - component: custom_intel
    input_mapping:
      company_name: input.company
      company_data: company_info
    dependencies: [company_intel]
```

## Configuration Reference

### System Configuration

```json
{
  "environment": "production",
  "log_level": "INFO",
  "components": {
    "company_intelligence": {
      "enabled": true,
      "rate_limit": 1.0,
      "search_depth": "comprehensive"
    }
  }
}
```

### Company Configuration

```json
{
  "name": "Company Name",
  "industry": "Technology",
  "priority": "high",
  "intelligence_types": ["company", "executives", "investments"],
  "outreach_settings": {
    "enabled": true,
    "templates": ["professional"],
    "frequency": "weekly"
  }
}
```

## Troubleshooting

### Common Issues

1. **API Key Not Set**
   ```bash
   export TAVILY_API_KEY="your_key_here"
   ```

2. **Component Initialization Failed**
   ```bash
   python -m api.cli.main status
   ```

3. **Configuration Not Found**
   ```bash
   python -m config.configuration_manager init
   ```

### Debug Mode

```bash
export CRM_ENV="development"
export LOG_LEVEL="DEBUG"
python -m api.cli.main intel "Company" --debug
```
