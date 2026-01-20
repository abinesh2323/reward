

import os
import yaml
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # Redis settings
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", 6379))
    redis_db: int = int(os.getenv("REDIS_DB", 0))
    use_redis: bool = os.getenv("USE_REDIS", "false").lower() == "true"
    
    # Cache settings
    idempotency_ttl: int = int(os.getenv("IDEMPOTENCY_TTL", 86400))  # 24 hours
    persona_cache_ttl: int = int(os.getenv("PERSONA_CACHE_TTL", 3600))  # 1 hour
    last_reward_cache_ttl: int = int(os.getenv("LAST_REWARD_CACHE_TTL", 86400))  # 24 hours
    
    # Service settings
    policy_config_path: str = os.getenv("POLICY_CONFIG_PATH", "./config/policy.yaml")
    persona_config_path: str = os.getenv("PERSONA_CONFIG_PATH", "./config/personas.json")
    
    # Performance settings
    enable_idempotency: bool = os.getenv("ENABLE_IDEMPOTENCY", "true").lower() == "true"
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class PolicyConfig:
    """Load and manage policy configuration."""
    
    def __init__(self, config_path: str = None):
        """Initialize policy configuration."""
        settings = Settings()
        config_path = config_path or settings.policy_config_path
        self.config = self._load_config(config_path)
        self.version = self.config.get("version", "v1.0.0")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load YAML configuration file."""
        path = Path(config_path)
        if not path.exists():
            # Return default config if file doesn't exist
            return self._default_config()
        
        with open(path, 'r') as f:
            config = yaml.safe_load(f)
        return config or {}
    
    def _default_config(self) -> Dict[str, Any]:
        """Return default policy configuration."""
        return {
            "version": "v1.0.0",
            "reward_types": {
                "XP": {"weight": 0.7},
                "CHECKOUT": {"weight": 0.2},
                "GOLD": {"weight": 0.1}
            },
            "xp": {
                "xp_per_rupee": 0.1,
                "max_xp_per_txn": 500,
                "persona_multipliers": {
                    "NEW": 1.0,
                    "RETURNING": 1.5,
                    "POWER": 2.0
                }
            },
            "cac": {
                "daily_cap_per_persona": {
                    "NEW": 0,
                    "RETURNING": 1000,
                    "POWER": 5000
                },
                "fallback_to_xp": True
            },
            "features": {
                "prefer_xp_mode": False,
                "cooldown_enabled": False,
                "cooldown_hours": 24
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key."""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default
    
    def get_reward_type_weights(self) -> Dict[str, float]:
        """Get reward type weights."""
        weights = {}
        reward_types = self.config.get("reward_types", {})
        for reward_type, config_data in reward_types.items():
            weights[reward_type] = config_data.get("weight", 0)
        return weights
    
    def get_xp_per_rupee(self) -> float:
        """Get XP per rupee rate."""
        return self.config.get("xp", {}).get("xp_per_rupee", 0.1)
    
    def get_max_xp_per_txn(self) -> int:
        """Get max XP per transaction."""
        return self.config.get("xp", {}).get("max_xp_per_txn", 500)
    
    def get_persona_multiplier(self, persona: str) -> float:
        """Get XP multiplier for a persona."""
        multipliers = self.config.get("xp", {}).get("persona_multipliers", {})
        return multipliers.get(persona, 1.0)
    
    def get_daily_cac_cap(self, persona: str) -> int:
        """Get daily CAC cap for a persona."""
        caps = self.config.get("cac", {}).get("daily_cap_per_persona", {})
        return caps.get(persona, 0)
    
    def get_cac_fallback_to_xp(self) -> bool:
        """Check if CAC should fallback to XP."""
        return self.config.get("cac", {}).get("fallback_to_xp", True)
    
    def prefer_xp_mode(self) -> bool:
        """Check if XP mode is preferred."""
        return self.config.get("features", {}).get("prefer_xp_mode", False)
    
    def cooldown_enabled(self) -> bool:
        """Check if cooldown feature is enabled."""
        return self.config.get("features", {}).get("cooldown_enabled", False)
    
    def get_cooldown_hours(self) -> int:
        """Get cooldown period in hours."""
        return self.config.get("features", {}).get("cooldown_hours", 24)


# Global policy config instance
_policy_config: Optional[PolicyConfig] = None


def get_policy_config() -> PolicyConfig:
    """Get or create the global policy config instance."""
    global _policy_config
    if _policy_config is None:
        _policy_config = PolicyConfig()
    return _policy_config
