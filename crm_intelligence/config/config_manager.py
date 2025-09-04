"""
Configuration Management Layer
Centralized configuration for all platform components
"""

from typing import Dict, List, Any, Optional
import json
import os
from pathlib import Path

class ConfigurationManager:
    """Manages all platform configuration"""

    def __init__(self):
        self.config = {}
        self.config_sources = []

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from multiple sources"""

        # Start with defaults
        config = self._get_default_config()

        # Load from environment
        config = self._merge_env_config(config)

        # Load from files
        config = self._merge_file_config(config)

        self.config = config
        return config

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "platform": {
                "name": "CRM Intelligence Platform",
                "version": "1.0.0",
                "environment": "development"
            },
            "intelligence": {
                "max_companies_per_batch": 10,
                "cache_enabled": True,
                "cache_ttl_hours": 24
            },
            "outreach": {
                "max_emails_per_company": 5,
                "personalization_threshold": 0.7,
                "sender_name": "[Your Name]",
                "sender_company": "[Your Company]"
            },
            "data": {
                "input_path": "data/input",
                "output_path": "data/output",
                "cache_path": "data/cache"
            },
            "api": {
                "tavily_base_url": "https://api.tavily.com/search",
                "timeout": 30,
                "max_retries": 3
            },
            "logging": {
                "level": "INFO",
                "file_enabled": True,
                "console_enabled": True
            }
        }

    def _merge_env_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge environment variable configuration"""
        env_mappings = {
            'TAVILY_API_KEY': 'api.tavily_api_key',
            'PLATFORM_ENV': 'platform.environment',
            'LOG_LEVEL': 'logging.level'
        }

        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value:
                config = self._set_nested_value(config, config_path, env_value)

        return config

    def _merge_file_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge file-based configuration"""
        config_files = [
            "config/platform_config.json",
            "config/intelligence_config.json",
            "config/outreach_config.json"
        ]

        for config_file in config_files:
            if Path(config_file).exists():
                try:
                    with open(config_file, 'r') as f:
                        file_config = json.load(f)
                    config = self._deep_merge(config, file_config)
                    self.config_sources.append(config_file)
                except Exception as e:
                    print(f"Warning: Could not load {config_file}: {e}")

        return config

    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = base.copy()

        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _set_nested_value(self, config: Dict[str, Any], path: str, value: Any) -> Dict[str, Any]:
        """Set nested configuration value using dot notation"""
        keys = path.split('.')
        current = config

        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set the value
        current[keys[-1]] = value
        return config

    def save_config(self, filename: str = "config/current_config.json") -> None:
        """Save current configuration"""
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(self.config, f, indent=2)

    def get_config_value(self, path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation"""
        keys = path.split('.')
        current = self.config

        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default

    def validate_config(self) -> List[str]:
        """Validate configuration"""
        errors = []

        # Check required API keys
        if not self.get_config_value('api.tavily_api_key'):
            errors.append("Missing TAVILY_API_KEY")

        # Check data paths
        required_paths = ['data.input_path', 'data.output_path', 'data.cache_path']
        for path_key in required_paths:
            path_value = self.get_config_value(path_key)
            if not path_value:
                errors.append(f"Missing data path: {path_key}")

        return errors
