

import pytest
from src.models import RewardDecisionRequest, RewardType, PersonaType
from src.reward_logic import RewardDecisionEngine
from datetime import datetime


class TestRewardLogic:
    """Test reward decision logic."""
    
    def test_xp_calculation_new_user(self, reward_engine):
        """Test XP calculation for NEW user."""
        # NEW user has 1x multiplier
        # XP = amount * xp_per_rupee * multiplier
        # XP = 1000 * 0.1 * 1.0 = 100
        xp = reward_engine._calculate_xp(1000, "NEW")
        assert xp == 100
    
    def test_xp_calculation_returning_user(self, reward_engine):
        """Test XP calculation for RETURNING user."""
        # RETURNING user has 1.5x multiplier
        # XP = 1000 * 0.1 * 1.5 = 150
        xp = reward_engine._calculate_xp(1000, "RETURNING")
        assert xp == 150
    
    def test_xp_calculation_power_user(self, reward_engine):
        """Test XP calculation for POWER user."""
        # POWER user has 2x multiplier
        # XP = 1000 * 0.1 * 2.0 = 200
        xp = reward_engine._calculate_xp(1000, "POWER")
        assert xp == 200
    
    def test_xp_max_cap(self, reward_engine):
        """Test that XP is capped at max_xp_per_txn."""
        # Large amount should be capped
        # max_xp = 500
        xp = reward_engine._calculate_xp(10000, "POWER")
        assert xp == 500
    
    def test_xp_small_amount(self, reward_engine):
        """Test XP calculation for small amounts."""
        # 100 * 0.1 * 1.0 = 10
        xp = reward_engine._calculate_xp(100, "NEW")
        assert xp == 10
    
    def test_reward_decision_response_structure(self, reward_engine):
        """Test that reward decision response has correct structure."""
        request = RewardDecisionRequest(
            txn_id="txn_001",
            user_id="user_001",
            merchant_id="merchant_001",
            amount=1000.0,
            txn_type="purchase",
            ts=int(datetime.now().timestamp())
        )
        
        response = reward_engine.decide(request)
        
        assert response.decision_id is not None
        assert response.policy_version == "v1.0.0"
        assert response.reward_type in [RewardType.XP, RewardType.CHECKOUT, RewardType.GOLD]
        assert response.reward_value >= 0
        assert response.xp >= 0
        assert isinstance(response.reason_codes, list)
        assert isinstance(response.meta, dict)
    
    def test_reason_codes_generated(self, reward_engine):
        """Test that reason codes are properly generated."""
        request = RewardDecisionRequest(
            txn_id="txn_002",
            user_id="user_001",
            merchant_id="merchant_001",
            amount=500.0,
            txn_type="purchase"
        )
        
        response = reward_engine.decide(request)
        
        assert len(response.reason_codes) > 0
        assert any(code in response.reason_codes for code in [
            "NEW_USER", "RETURNING_USER", "POWER_USER"
        ])
    
    def test_deterministic_reward_for_same_user(self, reward_engine):
        """Test that same user gets deterministic reward type."""
        request1 = RewardDecisionRequest(
            txn_id="txn_003",
            user_id="deterministic_user",
            merchant_id="merchant_001",
            amount=1000.0,
            txn_type="purchase"
        )
        
        request2 = RewardDecisionRequest(
            txn_id="txn_004",
            user_id="deterministic_user",
            merchant_id="merchant_001",
            amount=1000.0,
            txn_type="purchase"
        )
        
        response1 = reward_engine.decide(request1)
        response2 = reward_engine.decide(request2)
        
        # Same user should get the same reward type (deterministic)
        assert response1.reward_type == response2.reward_type
    
    def test_different_amounts_same_reward_type(self, reward_engine):
        """Test that reward type is deterministic per user regardless of amount."""
        request1 = RewardDecisionRequest(
            txn_id="txn_005",
            user_id="test_user_det",
            merchant_id="merchant_001",
            amount=100.0,
            txn_type="purchase"
        )
        
        request2 = RewardDecisionRequest(
            txn_id="txn_006",
            user_id="test_user_det",
            merchant_id="merchant_001",
            amount=5000.0,
            txn_type="purchase"
        )
        
        response1 = reward_engine.decide(request1)
        response2 = reward_engine.decide(request2)
        
        assert response1.reward_type == response2.reward_type
    
    def test_meta_contains_transaction_info(self, reward_engine):
        """Test that meta contains transaction information."""
        request = RewardDecisionRequest(
            txn_id="txn_007",
            user_id="user_007",
            merchant_id="merchant_007",
            amount=1000.0,
            txn_type="purchase"
        )
        
        response = reward_engine.decide(request)
        
        assert response.meta["txn_id"] == request.txn_id
        assert response.meta["user_id"] == request.user_id
        assert response.meta["merchant_id"] == request.merchant_id
        assert "persona" in response.meta
        assert "multiplier" in response.meta
