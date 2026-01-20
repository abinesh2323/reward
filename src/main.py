

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from src.models import RewardDecisionRequest, RewardDecisionResponse
from src.reward_logic import get_reward_engine
from src.config import get_policy_config

# Create FastAPI app
app = FastAPI(
    title="Reward Decision Service",
    description="Low-latency microservice for deterministic reward decisions",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "reward-decision-service",
        "version": "1.0.0"
    }


@app.post(
    "/reward/decide",
    response_model=RewardDecisionResponse,
    tags=["Reward"],
    summary="Get reward decision for a transaction",
    description="Returns a deterministic reward outcome for each transaction"
)
async def decide_reward(request: RewardDecisionRequest) -> RewardDecisionResponse:
    """
    Decide reward for a transaction.
    
    **Request Parameters:**
    - **txn_id**: Unique transaction identifier
    - **user_id**: User identifier
    - **merchant_id**: Merchant identifier
    - **amount**: Transaction amount (must be > 0)
    - **txn_type**: Type of transaction (e.g., 'purchase')
    - **ts**: Optional transaction timestamp (unix seconds)
    
    **Response Fields:**
    - **decision_id**: Unique decision identifier (UUID)
    - **policy_version**: Policy version applied
    - **reward_type**: Type of reward (XP, CHECKOUT, or GOLD)
    - **reward_value**: Monetary reward value
    - **xp**: XP points awarded
    - **reason_codes**: List of reason codes for the decision
    - **meta**: Additional metadata about the decision
    """
    try:
        engine = get_reward_engine()
        response = engine.decide(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing reward decision: {str(e)}")


@app.get("/config/policy", tags=["Configuration"])
async def get_policy():
    """Get current policy configuration."""
    try:
        policy = get_policy_config()
        return {
            "version": policy.version,
            "config": policy.config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving policy: {str(e)}")


@app.get("/docs", include_in_schema=False)
async def get_docs():
    """Redirect to OpenAPI documentation."""
    from fastapi.openapi.docs import get_swagger_ui_html
    return get_swagger_ui_html(openapi_url="/openapi.json", title="API")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
