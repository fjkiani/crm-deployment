# 📁 CRM Intelligence Scripts - Organized by Capability

This directory contains all scripts and data for the CRM Intelligence Platform, organized by component capabilities for better maintainability and clarity.

## 🏗️ Directory Structure

```
scripts/
├── data/                          # 📊 Data management
│   ├── input/                     # Raw input data
│   ├── output/                    # Generated results & logs
│   └── processing/               # ETL & data transformation
├── intelligence/                  # 🧠 Intelligence operations
│   ├── analysis/                  # Intelligence gathering & analysis
│   └── outreach/                  # Personalized outreach generation
├── config/                        # ⚙️ Configuration files
├── tests/                         # 🧪 Test scripts & utilities
├── demos/                         # 🎯 Demo & creation scripts
└── docs/                         # 📚 Documentation
```

## 📊 Data Layer (`data/`)

### Input Data (`input/`)
Contains raw data sources and templates:
- `leads.csv` - Main leads database
- `contacts_frm_formatted.csv` - Formatted contact data
- `preview_top50.csv` - Sample dataset for testing
- `template.csv` - Data format templates

### Output Data (`output/`)
Generated results, logs, and campaign outputs:
- `organized_leads.json` - Structured lead data
- `3edge_focused_analysis.json` - Intelligence analysis results
- `3edge_ai_outreach_campaign/` - Generated personalized emails
- `*.log` - Execution logs and debug information

### Data Processing (`processing/`)
ETL scripts for data transformation:
- `comprehensive_organizer.py` - Main data organization script
- `convert_contacts_to_csv.py` - Contact data conversion
- `etl_preview.py` - Data preview and validation
- `etl_to_crm_lead_csv.py` - CRM lead format conversion

## 🧠 Intelligence Layer (`intelligence/`)

### Analysis (`analysis/`)
Core intelligence gathering and analysis:
- `intelligence_gathering_agents.py` - Multi-agent intelligence system
- `focused_3edge_analysis.py` - Company-specific deep analysis
- `deep_intelligence_scout.py` - Advanced intelligence gathering
- `lead_enrichment_engine.py` - Lead data enrichment
- `setup_intelligence_system.py` - System initialization

### Outreach (`outreach/`)
Personalized communication generation:
- `hyper_personalized_3edge_emails.py` - AI-powered email generation

## ⚙️ Configuration (`config/`)

Configuration files for different components:
- `enrichment_config.json` - Enrichment engine settings

## 🧪 Testing (`tests/`)

Test scripts and utilities:
- `test_tavily_connection.py` - API connectivity testing
- Integration test scripts

## 🎯 Demos (`demos/`)

Demonstration and creation scripts:
- `create_scalable_structure.py` - Architecture creation demo
- `create_crm_platform_structure.py` - Platform structure demo

## 📚 Documentation (`docs/`)

Documentation and guides:
- `INTELLIGENCE_README.md` - Intelligence system documentation
- `ENRICHMENT_README.md` - Enrichment engine documentation
- `INTELLIGENCE_SYSTEM_OVERVIEW.md` - System overview

## 🚀 Quick Start

### Data Processing Workflow
```bash
# 1. Process and organize leads
cd scripts/data/processing
python3 comprehensive_organizer.py

# 2. Preview processed data
cd ../output
cat organized_leads.json
```

### Intelligence Analysis Workflow
```bash
# 1. Run intelligence analysis
cd scripts/intelligence/analysis
python3 focused_3edge_analysis.py

# 2. View results
cd ../../data/output
cat 3edge_focused_analysis.json
```

### Outreach Generation Workflow
```bash
# 1. Generate personalized outreach
cd scripts/intelligence/outreach
python3 hyper_personalized_3edge_emails.py

# 2. View generated campaigns
cd ../../data/output/3edge_ai_outreach_campaign
cat campaign_summary.md
```

## 📋 Usage Guidelines

### Adding New Scripts
1. **Identify the capability** - Which component does this belong to?
2. **Choose the right directory** - Place in appropriate capability folder
3. **Update documentation** - Add to this README if needed
4. **Follow naming conventions** - Use descriptive, capability-focused names

### Data Management
- **Input data** goes in `data/input/`
- **Generated results** go in `data/output/`
- **Processing scripts** go in `data/processing/`
- **Never modify input files** - Always work with copies

### Script Dependencies
- Scripts should be self-contained within their capability
- Use relative imports when referencing other components
- Document external dependencies in script docstrings

## 🔧 Maintenance

### Regular Cleanup
```bash
# Remove old logs and temporary files
find scripts/data/output -name "*.log" -mtime +7 -delete
find scripts/data/output -name "temp_*" -delete
```

### Organization Checks
```bash
# Verify all scripts are in correct directories
find scripts -name "*.py" -exec dirname {} \; | sort | uniq
```

## 🎯 Benefits of This Organization

### ✅ Clear Separation of Concerns
- Each directory has a single, well-defined purpose
- Easy to find scripts by functionality
- Reduced cognitive load when navigating

### ✅ Scalable Structure
- Easy to add new capabilities as separate directories
- Consistent organization patterns
- Room for growth without clutter

### ✅ Improved Maintainability
- Related scripts are grouped together
- Easier to understand system architecture
- Simplified dependency management

### ✅ Better Development Experience
- Quick location of relevant scripts
- Clear workflow paths
- Reduced time spent searching for files

## 📞 Support

If you need to add new scripts or modify the organization:
1. Identify the appropriate capability directory
2. Follow the existing naming conventions
3. Update this README if adding new capabilities
4. Test that all imports and paths still work

---

*This organization reflects our component-based architecture and makes the CRM Intelligence Platform more maintainable and scalable.*
