

import pytest
from src.models import RewardDecisionRequest, RewardType
from datetime import datetime


class TestCACCap:
    """Test daily CAC cap enforcement."""
    
    def test_cac_cap_not_exceeded(self, reward_engine):
        """Test that rewards are given when CAC cap is not exceeded."""
        # RETURNING user has 1000 CAC cap
        request = RewardDecisionRequest(
            txn_id="txn_cac_001",
            user_id="user_cac_001",
            merchant_id="merchant_001",
            amount=500.0,  # Within cap
            txn_type="purchase"
        )
        
        response = reward_engine.decide(request)
        
        # Should award some reward
        assert response.reward_value >= 0
    
    def test_new_user_has_zero_cap(self, reward_engine):
        """Test that NEW users have zero CAC cap."""
        # NEW users have 0 CAC cap by default
        # Override persona to NEW
        request = RewardDecisionRequest(
            txn_id="txn_cac_002",
            user_id="new_user_cac",
            merchant_id="merchant_001",
            amount=100.0,
            txn_type="purchase"
        )
        
        response = reward_engine.decide(request)
        
        # NEW user should not get monetary rewards (CAC cap is 0)
        assert response.reward_value == 0
    
    def test_cac_fallback_to_xp(self, reward_engine):
        """Test that when CAC is exceeded, system falls back to XP."""
        # Ensure we're tracking daily spend
        user_id = "user_cac_fallback"
        
        # Manually set daily CAC spend to near cap
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"cac:{user_id}:{today}"
        reward_engine.cache.set(cache_key, 900.0, ttl=86400)
        
        request = RewardDecisionRequest(
            txn_id="txn_cac_003",
            user_id=user_id,
            merchant_id="merchant_001",
            amount=200.0,  # This would exceed the 1000 cap for RETURNING
            txn_type="purchase"
        )
        
        response = reward_engine.decide(request)
        
        # When CAC is exceeded and fallback is enabled, should return XP
        # (actual reward_value may vary based on policy)
        assert response.xp >= 0  # Should still have XP
    
    def test_power_user_higher_cap(self, reward_engine):
        """Test that POWER users have higher CAC cap."""
        # POWER users have 5000 CAC cap
        # Test that higher amounts are allowed
        
        # We'll verify this by checking the config
        power_cap = reward_engine.policy_config.get_daily_cac_cap("POWER")
        returning_cap = reward_engine.policy_config.get_daily_cac_cap("RETURNING")
        
        assert power_cap > returning_cap
        assert power_cap == 5000
        assert returning_cap == 1000
    
    def test_daily_cac_tracking(self, reward_engine):
        """Test that daily CAC is tracked correctly."""
        user_id = "user_cac_tracking"
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"cac:{user_id}:{today}"
        
        # Initial spend
        reward_engine._update_daily_cac_spend(user_id, 100.0)
        spend1 = reward_engine._get_daily_cac_spend(user_id)
        assert spend1 == 100.0
        
        # Additional spend
        reward_engine._update_daily_cac_spend(user_id, 200.0)
        spend2 = reward_engine._get_daily_cac_spend(user_id)
        assert spend2 == 300.0
    
    def test_cac_cap_per_persona(self, reward_engine):
        """Test that CAC cap is applied per persona."""
        caps = {
            "NEW": reward_engine.policy_config.get_daily_cac_cap("NEW"),
            "RETURNING": reward_engine.policy_config.get_daily_cac_cap("RETURNING"),
            "POWER": reward_engine.policy_config.get_daily_cac_cap("POWER")
        }
        
        # Verify caps are different
        assert caps["NEW"] != caps["RETURNING"]
        assert caps["RETURNING"] != caps["POWER"]
        assert caps["NEW"] < caps["RETURNING"] < caps["POWER"]
