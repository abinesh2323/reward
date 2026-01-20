

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from src.models import RewardDecisionRequest, RewardDecisionResponse, RewardType
from src.config import get_policy_config
from src.cache import get_cache
from src.persona import get_persona_service
from src.config import Settings


class RewardDecisionEngine:
    """Core engine for reward decision making."""
    
    def __init__(self):
        """Initialize reward decision engine."""
        self.policy_config = get_policy_config()
        self.cache = get_cache()
        self.persona_service = get_persona_service()
        self.settings = Settings()
    
    def decide(self, request: RewardDecisionRequest) -> RewardDecisionResponse:
        """Make a reward decision for a transaction."""
        # Check idempotency
        if self.settings.enable_idempotency:
            idempotency_key = self._build_idempotency_key(request)
            cached_response = self.cache.get(idempotency_key)
            if cached_response:
                return RewardDecisionResponse(**cached_response)
        
        # Get user persona
        persona = self.persona_service.get_persona(request.user_id)
        
        # Calculate XP
        xp = self._calculate_xp(request.amount, persona.persona.value)
        
        # Determine reward type and value
        reward_type, reward_value = self._determine_reward(
            request.user_id,
            persona.persona.value,
            request.amount,
            xp
        )
        
        # Generate decision
        decision = RewardDecisionResponse(
            decision_id=str(uuid.uuid4()),
            policy_version=self.policy_config.version,
            reward_type=reward_type,
            reward_value=reward_value,
            xp=xp,
            reason_codes=self._get_reason_codes(persona.persona.value, reward_type),
            meta={
                "persona": persona.persona.value,
                "multiplier": self.policy_config.get_persona_multiplier(persona.persona.value),
                "txn_id": request.txn_id,
                "user_id": request.user_id,
                "merchant_id": request.merchant_id
            }
        )
        
        # Cache the response for idempotency
        if self.settings.enable_idempotency:
            idempotency_key = self._build_idempotency_key(request)
            self.cache.set(
                idempotency_key,
                decision.model_dump(),
                ttl=self.settings.idempotency_ttl
            )
        
        # Update last reward timestamp
        self._update_last_reward(request.user_id, request.ts)
        
        return decision
    
    def _build_idempotency_key(self, request: RewardDecisionRequest) -> str:
        """Build idempotency key from request."""
        key_parts = [request.txn_id, request.user_id, request.merchant_id]
        return f"idem:{':'.join(key_parts)}"
    
    def _calculate_xp(self, amount: float, persona: str) -> int:
        """Calculate XP based on amount and persona."""
        xp_per_rupee = self.policy_config.get_xp_per_rupee()
        max_xp = self.policy_config.get_max_xp_per_txn()
        multiplier = self.policy_config.get_persona_multiplier(persona)
        
        calculated_xp = int(amount * xp_per_rupee * multiplier)
        return min(calculated_xp, max_xp)
    
    def _determine_reward(
        self,
        user_id: str,
        persona: str,
        amount: float,
        xp: int
    ) -> tuple[RewardType, int]:
        """Determine reward type and value based on policy and CAC cap."""
        daily_cap = self.policy_config.get_daily_cac_cap(persona)
        
        # Check daily CAC
        if daily_cap > 0:
            daily_spend = self._get_daily_cac_spend(user_id)
            
            if daily_spend + amount > daily_cap:
                # CAC exceeded, return only XP
                if self.policy_config.get_cac_fallback_to_xp():
                    return RewardType.XP, 0
                else:
                    return RewardType.XP, 0
        
        # Check if XP mode is preferred
        if self.policy_config.prefer_xp_mode():
            return RewardType.XP, 0
        
        # Check cooldown if enabled
        if self.policy_config.cooldown_enabled():
            if self._is_in_cooldown(user_id):
                return RewardType.XP, 0
        
        # Default reward type
        weights = self.policy_config.get_reward_type_weights()
        
        # Simple deterministic selection based on user_id hash
        seed = hash(user_id) % 100
        cumulative = 0
        
        for reward_type, weight in weights.items():
            cumulative += int(weight * 100)
            if seed < cumulative:
                if reward_type == "CHECKOUT":
                    return RewardType.CHECKOUT, int(amount * 0.05)  # 5% cashback
                elif reward_type == "GOLD":
                    return RewardType.GOLD, int(amount * 0.02)  # 2% gold
                else:
                    return RewardType.XP, 0
        
        return RewardType.XP, 0
    
    def _get_daily_cac_spend(self, user_id: str) -> float:
        """Get total CAC spend for the day."""
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"cac:{user_id}:{today}"
        
        cached = self.cache.get(cache_key)
        return cached or 0.0
    
    def _update_daily_cac_spend(self, user_id: str, amount: float) -> None:
        """Update daily CAC spend."""
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"cac:{user_id}:{today}"
        
        current = self._get_daily_cac_spend(user_id)
        self.cache.set(
            cache_key,
            current + amount,
            ttl=86400  # 24 hours
        )
    
    def _is_in_cooldown(self, user_id: str) -> bool:
        """Check if user is in cooldown period."""
        cache_key = f"last_reward:{user_id}"
        last_reward_ts = self.cache.get(cache_key)
        
        if last_reward_ts is None:
            return False
        
        cooldown_hours = self.policy_config.get_cooldown_hours()
        cooldown_seconds = cooldown_hours * 3600
        
        current_ts = int(datetime.now().timestamp())
        return (current_ts - last_reward_ts) < cooldown_seconds
    
    def _update_last_reward(self, user_id: str, ts: Optional[int]) -> None:
        """Update last reward timestamp."""
        cache_key = f"last_reward:{user_id}"
        timestamp = ts or int(datetime.now().timestamp())
        
        self.cache.set(
            cache_key,
            timestamp,
            ttl=self.settings.last_reward_cache_ttl
        )
    
    def _get_reason_codes(self, persona: str, reward_type: RewardType) -> List[str]:
        """Generate reason codes for the decision."""
        codes = []
        
        if persona == "NEW":
            codes.append("NEW_USER")
        elif persona == "RETURNING":
            codes.append("RETURNING_USER")
        elif persona == "POWER":
            codes.append("POWER_USER")
        
        if reward_type == RewardType.XP:
            codes.append("XP_MODE_ENABLED")
        elif reward_type == RewardType.CHECKOUT:
            codes.append("CHECKOUT_REWARD")
        elif reward_type == RewardType.GOLD:
            codes.append("GOLD_REWARD")
        
        if self.policy_config.prefer_xp_mode():
            codes.append("PREFER_XP_MODE")
        
        if self.policy_config.cooldown_enabled():
            codes.append("COOLDOWN_POLICY_ENABLED")
        
        return codes


# Global reward decision engine instance
_engine: Optional[RewardDecisionEngine] = None


def get_reward_engine() -> RewardDecisionEngine:
    """Get or create the global reward decision engine instance."""
    global _engine
    if _engine is None:
        _engine = RewardDecisionEngine()
    return _engine
