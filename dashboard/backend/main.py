from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import jwt
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="AgentVault Dashboard API",
    description="Backend API for AgentVault crypto platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"

# Models
class User(BaseModel):
    id: str
    email: str
    wallet_address: Optional[str] = None
    token_balance: float = 0
    total_usage: int = 0
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None

class Agent(BaseModel):
    id: str
    name: str
    description: str
    wallet_address: str
    status: str
    created_at: datetime
    last_active: Optional[datetime] = None

class UsageStats(BaseModel):
    total_requests: int
    total_cost: float
    daily_usage: List[Dict[str, Any]]
    monthly_usage: List[Dict[str, Any]]

class BillingHistory(BaseModel):
    id: str
    amount: float
    description: str
    timestamp: datetime
    status: str

class AirdropInfo(BaseModel):
    eligible: bool
    amount: float
    next_claim: Optional[datetime]
    total_claimed: float

# Mock data storage (in production, use a database)
users_db = {}
agents_db = {}
usage_db = {}
billing_db = {}

# Authentication
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

# API Endpoints

@app.get("/")
async def root():
    return {"message": "AgentVault Dashboard API", "version": "1.0.0"}

@app.post("/auth/login")
async def login(email: str, password: str):
    # Mock authentication - in production, verify against database
    if email not in users_db:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = users_db[email]
    # In production, verify password hash
    # if not bcrypt.checkpw(password.encode(), user.password_hash):
    #     raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.id, "email": user.email})
    return {"access_token": token, "user": user}

@app.get("/dashboard/stats")
async def get_dashboard_stats(token_data: dict = Depends(verify_token)):
    # Mock stats - in production, fetch from database
    return {
        "totalAgents": 12,
        "activeAgents": 8,
        "totalUsage": 15420,
        "monthlyUsage": 3420,
        "tokenBalance": "1,250.50",
        "airdropEligible": True,
        "nextAirdrop": "2024-02-15T10:00:00Z",
    }

@app.get("/agents")
async def get_agents(token_data: dict = Depends(verify_token)) -> List[Agent]:
    # Mock agents - in production, fetch from database
    return [
        Agent(
            id="1",
            name="Trading Bot Alpha",
            description="Automated ETH trading with DCA strategy",
            wallet_address="0x742d35Cc6cCc44C4Af2d4C8c4c4c4c4c4c4c4c4c4",
            status="active",
            created_at=datetime.now() - timedelta(days=30),
            last_active=datetime.now() - timedelta(hours=2)
        ),
        Agent(
            id="2",
            name="DeFi Arbitrage Bot",
            description="Cross-DEX arbitrage opportunities",
            wallet_address="0x8ba1f109551bD432803012645Ac136c04CB6328",
            status="active",
            created_at=datetime.now() - timedelta(days=15),
            last_active=datetime.now() - timedelta(minutes=30)
        )
    ]

@app.get("/usage")
async def get_usage_stats(token_data: dict = Depends(verify_token)) -> UsageStats:
    # Mock usage data - in production, fetch from database
    return UsageStats(
        total_requests=15420,
        total_cost=1250.50,
        daily_usage=[
            {"date": "2024-01-01", "requests": 120, "cost": 12.50},
            {"date": "2024-01-02", "requests": 98, "cost": 9.80},
            {"date": "2024-01-03", "requests": 156, "cost": 15.60},
        ],
        monthly_usage=[
            {"month": "2024-01", "requests": 3420, "cost": 342.00},
            {"month": "2023-12", "requests": 2890, "cost": 289.00},
        ]
    )

@app.get("/billing/history")
async def get_billing_history(token_data: dict = Depends(verify_token)) -> List[BillingHistory]:
    # Mock billing history - in production, fetch from database
    return [
        BillingHistory(
            id="1",
            amount=25.50,
            description="API Usage - January 2024",
            timestamp=datetime.now() - timedelta(days=5),
            status="paid"
        ),
        BillingHistory(
            id="2",
            amount=15.75,
            description="Agent Creation Fee",
            timestamp=datetime.now() - timedelta(days=12),
            status="paid"
        )
    ]

@app.get("/airdrop/info")
async def get_airdrop_info(token_data: dict = Depends(verify_token)) -> AirdropInfo:
    # Mock airdrop info - in production, fetch from smart contract/blockchain
    return AirdropInfo(
        eligible=True,
        amount=100.0,
        next_claim=datetime.now() + timedelta(days=25),
        total_claimed=450.0
    )

@app.post("/airdrop/claim")
async def claim_airdrop(token_data: dict = Depends(verify_token)):
    # Mock airdrop claim - in production, interact with smart contract
    return {
        "success": True,
        "amount": 100.0,
        "transaction_hash": "0x1234567890abcdef",
        "message": "Airdrop claimed successfully!"
    }

@app.get("/wallet/balance")
async def get_wallet_balance(token_data: dict = Depends(verify_token)):
    # Mock wallet balance - in production, fetch from blockchain
    return {
        "eth_balance": "1.25",
        "token_balance": "1250.50",
        "wallet_address": "0x742d35Cc6cCc44C4Af2d4C8c4c4c4c4c4c4c4c4c4"
    }

@app.post("/agents/create")
async def create_agent(
    name: str,
    description: str,
    token_data: dict = Depends(verify_token)
):
    # Mock agent creation - in production, create wallet and store in database
    return {
        "id": "new-agent-id",
        "name": name,
        "description": description,
        "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
        "status": "created",
        "message": "Agent created successfully"
    }

@app.get("/user/profile")
async def get_user_profile(token_data: dict = Depends(verify_token)):
    # Mock user profile - in production, fetch from database
    return {
        "id": "user-123",
        "email": "user@example.com",
        "wallet_address": "0x742d35Cc6cCc44C4Af2d4C8c4c4c4c4c4c4c4c4c4",
        "token_balance": 1250.50,
        "total_usage": 15420,
        "join_date": "2024-01-01T00:00:00Z",
        "tier": "premium"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)