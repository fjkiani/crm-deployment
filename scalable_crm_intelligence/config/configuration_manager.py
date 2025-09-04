"""
Configuration Manager
Centralized configuration management with environment support
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class SystemConfig:
    """System-wide configuration"""
    environment: str = "development"
    log_level: str = "INFO"
    api_keys: Dict[str, str] = None
    components: Dict[str, Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.api_keys is None:
            self.api_keys = {}
        if self.components is None:
            self.components = {}

class ConfigurationManager:
    """Manages all system configuration"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.system_config = None
        self.company_configs = {}
        
    def load_system_config(self, environment: str = "development") -> SystemConfig:
        """Load system configuration for environment"""
        
        config_file = self.config_dir / "environments" / f"{environment}.json"
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                config_data = json.load(f)
                
            # Load environment variables
            config_data["api_keys"] = self._load_api_keys()
            
            self.system_config = SystemConfig(**config_data)
        else:
            self.system_config = SystemConfig(environment=environment)
            
        return self.system_config
        
    def load_company_config(self, company_name: str) -> Dict[str, Any]:
        """Load configuration for specific company"""
        
        safe_name = company_name.lower().replace(' ', '_').replace('.', '_')
        config_file = self.config_dir / "companies" / f"{safe_name}.json"
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            config = self._create_default_company_config(company_name)
            
        self.company_configs[company_name] = config
        return config
        
    def save_company_config(self, company_name: str, config: Dict[str, Any]):
        """Save company configuration"""
        
        safe_name = company_name.lower().replace(' ', '_').replace('.', '_')
        config_file = self.config_dir / "companies" / f"{safe_name}.json"
        
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
            
    def get_component_config(self, component_name: str) -> Dict[str, Any]:
        """Get configuration for specific component"""
        
        if not self.system_config:
            self.load_system_config()
            
        return self.system_config.components.get(component_name, {})
        
    def _load_api_keys(self) -> Dict[str, str]:
        """Load API keys from environment variables"""
        
        return {
            "tavily": os.getenv("TAVILY_API_KEY", ""),
            "openai": os.getenv("OPENAI_API_KEY", ""),
            "anthropic": os.getenv("ANTHROPIC_API_KEY", "")
        }
        
    def _create_default_company_config(self, company_name: str) -> Dict[str, Any]:
        """Create default configuration for a company"""
        
        return {
            "name": company_name,
            "industry": "Unknown",
            "priority": "medium",
            "intelligence_types": ["company", "executives", "investments"],
            "outreach_settings": {
                "enabled": True,
                "templates": ["professional", "technical"],
                "frequency": "weekly"
            },
            "custom_fields": {}
        }
