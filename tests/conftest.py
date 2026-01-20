

import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.cache import InMemoryCache
from src.reward_logic import RewardDecisionEngine
from src.config import PolicyConfig


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def cache():
    """Create a test cache."""
    return InMemoryCache()


@pytest.fixture
def policy_config(tmp_path):
    """Create a test policy config."""
    # Create a temporary policy file
    policy_file = tmp_path / "policy.yaml"
    policy_file.write_text("""
version: "v1.0.0"
reward_types:
  XP:
    weight: 0.7
  CHECKOUT:
    weight: 0.2
  GOLD:
    weight: 0.1
xp:
  xp_per_rupee: 0.1
  max_xp_per_txn: 500
  persona_multipliers:
    NEW: 1.0
    RETURNING: 1.5
    POWER: 2.0
cac:
  daily_cap_per_persona:
    NEW: 0
    RETURNING: 1000
    POWER: 5000
  fallback_to_xp: true
features:
  prefer_xp_mode: false
  cooldown_enabled: false
  cooldown_hours: 24
""")
    return PolicyConfig(str(policy_file))


@pytest.fixture
def reward_engine(policy_config, cache):
    """Create a reward decision engine."""
    engine = RewardDecisionEngine()
    engine.policy_config = policy_config
    engine.cache = cache
    return engine
