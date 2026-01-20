

import json
from typing import Optional, Dict
from pathlib import Path
from src.models import UserPersona, PersonaType
from src.cache import get_cache
from src.config import Settings


class PersonaService:
    """Service for managing user personas."""
    
    def __init__(self):
        """Initialize persona service."""
        self.settings = Settings()
        self.cache = get_cache()
        self._personas_data = self._load_personas()
    
    def _load_personas(self) -> Dict[str, dict]:
        """Load personas from configuration file."""
        config_path = Path(self.settings.persona_config_path)
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading personas file: {e}")
                return {}
        
        # Return empty dict if file doesn't exist
        return {}
    
    def get_persona(self, user_id: str) -> UserPersona:
        """Get or infer user persona."""
        # Check cache first
        cache_key = f"persona:{user_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return UserPersona(**cached)
        
        # Check in personas data file
        if user_id in self._personas_data:
            persona_data = self._personas_data[user_id]
            persona = UserPersona(
                user_id=user_id,
                persona=PersonaType(persona_data.get("persona", "NEW")),
                lifetime_purchases=persona_data.get("lifetime_purchases", 0),
                last_reward_ts=persona_data.get("last_reward_ts")
            )
        else:
            # Default to NEW if not found
            persona = UserPersona(
                user_id=user_id,
                persona=PersonaType.NEW,
                lifetime_purchases=0
            )
        
        # Cache the persona
        self.cache.set(
            cache_key,
            persona.model_dump(),
            ttl=self.settings.persona_cache_ttl
        )
        
        return persona
    
    def update_persona(self, user_id: str, persona: UserPersona) -> None:
        """Update persona information."""
        self._personas_data[user_id] = persona.model_dump()
        
        # Update cache
        cache_key = f"persona:{user_id}"
        self.cache.set(
            cache_key,
            persona.model_dump(),
            ttl=self.settings.persona_cache_ttl
        )
    
    def infer_persona(self, lifetime_purchases: int) -> PersonaType:
        """Infer persona based on lifetime purchases."""
        if lifetime_purchases == 0:
            return PersonaType.NEW
        elif lifetime_purchases >= 10:
            return PersonaType.POWER
        else:
            return PersonaType.RETURNING


# Global persona service instance
_persona_service: Optional[PersonaService] = None


def get_persona_service() -> PersonaService:
    """Get or create the global persona service instance."""
    global _persona_service
    if _persona_service is None:
        _persona_service = PersonaService()
    return _persona_service
