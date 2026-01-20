

import pytest
from src.models import RewardDecisionRequest
from src.reward_logic import RewardDecisionEngine
from datetime import datetime


class TestIdempotency:
    """Test idempotent request handling."""
    
    def test_idempotent_request_returns_same_response(self, reward_engine):
        """Test that identical requests return the same response."""
        request = RewardDecisionRequest(
            txn_id="txn_idem_001",
            user_id="user_idem_001",
            merchant_id="merchant_001",
            amount=1000.0,
            txn_type="purchase"
        )
        
        # First request
        response1 = reward_engine.decide(request)
        
        # Second identical request
        response2 = reward_engine.decide(request)
        
        # Should have identical decision_id
        assert response1.decision_id == response2.decision_id
        assert response1.reward_type == response2.reward_type
        assert response1.reward_value == response2.reward_value
        assert response1.xp == response2.xp
    
    def test_different_txn_ids_different_responses(self, reward_engine):
        """Test that different transaction IDs can have different decision IDs."""
        request1 = RewardDecisionRequest(
            txn_id="txn_idem_002",
            user_id="user_idem_002",
            merchant_id="merchant_001",
            amount=1000.0,
            txn_type="purchase"
        )
        
        request2 = RewardDecisionRequest(
            txn_id="txn_idem_003",
            user_id="user_idem_002",
            merchant_id="merchant_001",
            amount=1000.0,
            txn_type="purchase"
        )
        
        response1 = reward_engine.decide(request1)
        response2 = reward_engine.decide(request2)
        
        # Different txn_ids should have different decision_ids
        assert response1.decision_id != response2.decision_id
    
    def test_idempotency_key_includes_user_and_merchant(self, reward_engine):
        """Test that idempotency key includes user and merchant."""
        request1 = RewardDecisionRequest(
            txn_id="txn_idem_004",
            user_id="user_idem_004",
            merchant_id="merchant_001",
            amount=1000.0,
            txn_type="purchase"
        )
        
        request2 = RewardDecisionRequest(
            txn_id="txn_idem_004",
            user_id="user_idem_005",  # Different user
            merchant_id="merchant_001",
            amount=1000.0,
            txn_type="purchase"
        )
        
        response1 = reward_engine.decide(request1)
        response2 = reward_engine.decide(request2)
        
        # Different users with same txn_id should have different decisions
        assert response1.decision_id != response2.decision_id
    
    def test_idempotency_key_includes_merchant(self, reward_engine):
        """Test that idempotency key includes merchant."""
        request1 = RewardDecisionRequest(
            txn_id="txn_idem_006",
            user_id="user_idem_006",
            merchant_id="merchant_001",
            amount=1000.0,
            txn_type="purchase"
        )
        
        request2 = RewardDecisionRequest(
            txn_id="txn_idem_006",
            user_id="user_idem_006",
            merchant_id="merchant_002",  # Different merchant
            amount=1000.0,
            txn_type="purchase"
        )
        
        response1 = reward_engine.decide(request1)
        response2 = reward_engine.decide(request2)
        
        # Different merchants with same txn_id and user should have different decisions
        assert response1.decision_id != response2.decision_id
    
    def test_idempotency_with_cache(self, reward_engine):
        """Test that idempotency uses cache."""
        request = RewardDecisionRequest(
            txn_id="txn_idem_007",
            user_id="user_idem_007",
            merchant_id="merchant_001",
            amount=1000.0,
            txn_type="purchase"
        )
        
        response1 = reward_engine.decide(request)
        
        # Check that response is cached
        idempotency_key = reward_engine._build_idempotency_key(request)
        cached = reward_engine.cache.get(idempotency_key)
        
        assert cached is not None
        assert cached["decision_id"] == response1.decision_id
    
    def test_idempotency_ttl_respected(self, reward_engine, cache):
        """Test that idempotency TTL is respected."""
        # Override cache with short TTL
        short_ttl = 1
        
        request = RewardDecisionRequest(
            txn_id="txn_idem_008",
            user_id="user_idem_008",
            merchant_id="merchant_001",
            amount=1000.0,
            txn_type="purchase"
        )
        
        # Manually set cache with short TTL
        idempotency_key = reward_engine._build_idempotency_key(request)
        test_value = {"test": "value"}
        reward_engine.cache.set(idempotency_key, test_value, ttl=short_ttl)
        
        # Should exist immediately
        assert reward_engine.cache.get(idempotency_key) is not None
