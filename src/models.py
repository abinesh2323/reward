

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class RewardType(str, Enum):
    """Types of rewards that can be offered."""
    XP = "XP"
    CHECKOUT = "CHECKOUT"
    GOLD = "GOLD"


class RewardDecisionRequest(BaseModel):
    """Request model for /reward/decide endpoint."""
    txn_id: str = Field(..., description="Transaction ID")
    user_id: str = Field(..., description="User ID")
    merchant_id: str = Field(..., description="Merchant ID")
    amount: float = Field(..., gt=0, description="Transaction amount")
    txn_type: str = Field(..., description="Transaction type (e.g., 'purchase')")
    ts: Optional[int] = Field(None, description="Transaction timestamp (unix)")

    class Config:
        json_schema_extra = {
            "example": {
                "txn_id": "txn_12345",
                "user_id": "user_789",
                "merchant_id": "merchant_456",
                "amount": 1000.0,
                "txn_type": "purchase",
                "ts": 1705689600
            }
        }


class RewardDecisionResponse(BaseModel):
    """Response model for /reward/decide endpoint."""
    decision_id: str = Field(..., description="Unique decision ID (UUID)")
    policy_version: str = Field(..., description="Policy version applied")
    reward_type: RewardType = Field(..., description="Type of reward")
    reward_value: int = Field(..., ge=0, description="Monetary reward value")
    xp: int = Field(..., ge=0, description="XP points awarded")
    reason_codes: List[str] = Field(default_factory=list, description="Reason codes for decision")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "decision_id": "dec_uuid_12345",
                "policy_version": "v1.0.0",
                "reward_type": "XP",
                "reward_value": 0,
                "xp": 100,
                "reason_codes": ["RETURNING_USER", "XP_MODE_ENABLED"],
                "meta": {"persona": "RETURNING", "multiplier": 1.5}
            }
        }


class PersonaType(str, Enum):
    """User personas."""
    NEW = "NEW"
    RETURNING = "RETURNING"
    POWER = "POWER"


class UserPersona(BaseModel):
    """Persona information for a user."""
    user_id: str
    persona: PersonaType
    lifetime_purchases: int = 0
    last_reward_ts: Optional[int] = None
