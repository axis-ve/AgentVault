# AgentVault Token (AVT) - Economics & Smart Contract Documentation

## Table of Contents
- [Overview](#overview)
- [Token Specifications](#token-specifications)
- [Airdrop Mechanism](#airdrop-mechanism)
- [Usage Tracking](#usage-tracking)
- [Economic Model](#economic-model)
- [Smart Contract API](#smart-contract-api)
- [Deployment Guide](#deployment-guide)
- [Security Considerations](#security-considerations)

## Overview

**AgentVault Token (AVT)** is an ERC-20 utility token that powers the AgentVault platform. It implements a usage-based reward system where active users receive periodic airdrops based on their API consumption.

### Purpose

1. **Payment Token**: Users pay for agent services using AVT
2. **Reward Token**: Active users earn AVT through airdrops
3. **Governance Token** (future): Voting on platform parameters
4. **Staking Token** (future): Earn rewards by locking tokens

### Key Features

- ✅ ERC-20 standard compliance
- ✅ Usage-based airdrop system (30-day intervals)
- ✅ Automatic user activation at 10+ API calls
- ✅ Bonus rewards for high usage
- ✅ ReentrancyGuard protection
- ✅ Owner-controlled usage recording
- ✅ Burnable tokens

## Token Specifications

### Basic Parameters

```solidity
Name:           AgentVault Token
Symbol:         AVT
Decimals:       18
Total Supply:   Configurable at deployment (e.g., 1,000,000,000 AVT)
Contract:       AgentVaultToken.sol
Standard:       ERC-20 (OpenZeppelin)
Security:       Ownable + ReentrancyGuard
```

### Deployment Configuration

```javascript
// Example deployment (Hardhat)
const initialSupply = ethers.parseEther("1000000000"); // 1 billion AVT

const AgentVaultToken = await ethers.getContractFactory("AgentVaultToken");
const token = await AgentVaultToken.deploy(initialSupply);
```

## Airdrop Mechanism

### Eligibility Criteria

**Minimum Requirements**:
```
✓ User must have 10+ API calls recorded
✓ 30 days must have passed since last airdrop claim
✓ Contract must have sufficient tokens in owner's balance
```

### Reward Calculation

**Formula**:
```solidity
function calculateAirdropAmount(uint256 userUsage) public pure returns (uint256) {
    if (userUsage < 10) return 0;

    // Base reward: 100 AVT
    uint256 amount = 100 * 10**18;

    // Bonus: +10 AVT per additional 10 calls
    uint256 bonusUsage = userUsage - 10;
    uint256 bonusTokens = (bonusUsage / 10) * 10 * 10**18;

    return amount + bonusTokens;
}
```

**Examples**:
```
Usage Count    Base Reward    Bonus    Total Airdrop
─────────────────────────────────────────────────────
0-9 calls      0 AVT          0 AVT    Not eligible
10 calls       100 AVT        0 AVT    100 AVT
20 calls       100 AVT        10 AVT   110 AVT
50 calls       100 AVT        40 AVT   140 AVT
100 calls      100 AVT        90 AVT   190 AVT
500 calls      100 AVT        490 AVT  590 AVT
1000 calls     100 AVT        990 AVT  1090 AVT
```

### Claim Process

**User Flow**:
```
1. User reaches 10+ API calls
   ↓
2. User becomes "active" (isActiveUser[user] = true)
   ↓
3. User waits 30 days from last claim (or first activation)
   ↓
4. User calls claimAirdrop()
   ↓
5. Contract calculates reward based on total usage
   ↓
6. Tokens transferred from owner to user
   ↓
7. lastAirdrop[user] timestamp updated
   ↓
8. User can claim again after another 30 days
```

**Smart Contract Call**:
```solidity
// User claims airdrop
try agentVaultToken.claimAirdrop() returns (uint256 amount) {
    // Success! Received 'amount' tokens
} catch Error(string memory reason) {
    // Handle errors:
    // - "User not active"
    // - "Airdrop not available yet"
    // - "No airdrop available"
    // - "Insufficient contract balance"
}
```

### Airdrop Economics

**Supply Dynamics**:
```
Total Supply:        1,000,000,000 AVT
Owner Reserve:       500,000,000 AVT (50% for airdrops)
Circulating:         500,000,000 AVT (50% for initial distribution)

Monthly Airdrops:    ~50,000 users × 150 AVT avg = 7,500,000 AVT
Annual Airdrops:     90,000,000 AVT (9% of total supply)
Runway:              ~5.5 years at full capacity
```

**Deflationary Mechanism**:
```solidity
// Users can burn tokens to reduce supply
function burn(uint256 amount) external {
    _burn(msg.sender, amount);
}
```

## Usage Tracking

### Recording System

**Owner-Only Function**:
```solidity
function recordUsage(address user, uint256 count) external onlyOwner {
    usageCount[user] += count;

    // Auto-activate user at 10+ calls
    if (!isActiveUser[user] && usageCount[user] >= 10) {
        isActiveUser[user] = true;
        emit UserActivated(user);
    }

    emit UsageRecorded(user, count);
}
```

**Backend Integration**:
```python
# dashboard/backend/main.py
from web3 import Web3
from eth_account import Account

# Load contract
avt_contract = web3.eth.contract(address=AVT_ADDRESS, abi=AVT_ABI)

# Owner account (server-side wallet)
owner_account = Account.from_key(OWNER_PRIVATE_KEY)

async def record_user_usage(user_address: str, api_calls: int):
    """Record API usage on-chain"""

    # Build transaction
    tx = avt_contract.functions.recordUsage(
        user_address,
        api_calls
    ).build_transaction({
        'from': owner_account.address,
        'nonce': await web3.eth.get_transaction_count(owner_account.address),
        'gas': 100000,
        'maxFeePerGas': await web3.eth.gas_price,
        'maxPriorityFeePerGas': web3.to_wei(2, 'gwei'),
    })

    # Sign and send
    signed = owner_account.sign_transaction(tx)
    tx_hash = await web3.eth.send_raw_transaction(signed.rawTransaction)

    # Wait for confirmation
    receipt = await web3.eth.wait_for_transaction_receipt(tx_hash)

    return receipt.transactionHash.hex()
```

**Batch Recording** (Gas Optimization):
```solidity
// TODO: Add batch recording function
function recordUsageBatch(
    address[] calldata users,
    uint256[] calldata counts
) external onlyOwner {
    require(users.length == counts.length, "Length mismatch");

    for (uint256 i = 0; i < users.length; i++) {
        recordUsage(users[i], counts[i]);
    }
}
```

### User Statistics

**View Functions**:
```solidity
// Get user stats
function getUserStats(address user) external view returns (
    uint256 totalUsage,
    bool active,
    uint256 lastClaim
) {
    return (
        usageCount[user],
        isActiveUser[user],
        lastAirdrop[user]
    );
}

// Get airdrop info
function getAirdropInfo(address user) external view returns (
    bool eligible,
    uint256 amount,
    uint256 timeUntilNext
) {
    if (!isActiveUser[user]) {
        return (false, 0, 0);
    }

    uint256 nextClaimTime = lastAirdrop[user] + AIRDROP_INTERVAL;
    eligible = block.timestamp >= nextClaimTime;

    if (eligible) {
        amount = calculateAirdropAmount(usageCount[user]);
    } else {
        amount = 0;
    }

    timeUntilNext = eligible ? 0 : nextClaimTime - block.timestamp;
}
```

## Economic Model

### Pricing Structure

**Base Pricing**:
```
Service                    Cost (AVT)    Notes
───────────────────────────────────────────────────
API Call (basic)          0.01 AVT      Standard agent operation
API Call (complex)        0.05 AVT      Strategy execution, DeFi
Transaction               0.10 AVT      On-chain wallet operation
Agent Creation            1.00 AVT      One-time setup fee
Premium Features          10.00 AVT/mo  Advanced analytics, priority
```

**Volume Discounts**:
```
Monthly Usage             Discount      Effective Rate
─────────────────────────────────────────────────────
0-1,000 calls            0%            0.01 AVT/call
1,001-10,000 calls       10%           0.009 AVT/call
10,001-100,000 calls     25%           0.0075 AVT/call
100,001+ calls           40%           0.006 AVT/call
```

**Subscription Tiers**:
```
Plan         Monthly Cost    Included Calls    Overage
──────────────────────────────────────────────────────
Starter      10 AVT          1,000 calls       0.01 AVT
Pro          50 AVT          10,000 calls      0.008 AVT
Enterprise   200 AVT         100,000 calls     0.005 AVT
```

### Token Velocity

**Expected Circulation**:
```
Average User:
- 100 API calls/month × 0.01 AVT = 1 AVT spent
- Airdrop (every 30 days) = 190 AVT earned
- Net: +189 AVT/month

Power User:
- 1,000 API calls/month × 0.008 AVT = 8 AVT spent
- Airdrop (every 30 days) = 1,090 AVT earned
- Net: +1,082 AVT/month

Enterprise:
- 100,000 calls/month × 0.005 AVT = 500 AVT spent
- Airdrop (every 30 days) = 10,000+ AVT earned
- Net: +9,500 AVT/month
```

**Token Demand Drivers**:
1. Platform usage (pay-per-use)
2. Subscription fees
3. Premium features
4. Governance participation (future)
5. Staking requirements (future)

**Token Supply Controls**:
1. Airdrops incentivize usage (inflationary)
2. Burn mechanism (deflationary)
3. Staking locks (reduces circulating supply)
4. Transaction fees (buy-back & burn, future)

### Game Theory

**User Incentives**:
```
✓ Use platform more → Earn larger airdrops
✓ Hold tokens → Access premium features
✓ Stake tokens → Earn yield (future)
✓ Participate in governance → Influence platform
```

**Anti-Gaming Mechanisms**:
```
✓ 30-day cooldown prevents airdrop farming
✓ Owner-controlled usage recording prevents spoofing
✓ Minimum 10 calls prevents Sybil attacks
✓ Time-locked claims reduce sell pressure
```

## Smart Contract API

### Core ERC-20 Functions

```solidity
// Standard ERC-20
function totalSupply() external view returns (uint256);
function balanceOf(address account) external view returns (uint256);
function transfer(address to, uint256 amount) external returns (bool);
function allowance(address owner, address spender) external view returns (uint256);
function approve(address spender, uint256 amount) external returns (bool);
function transferFrom(address from, address to, uint256 amount) external returns (bool);
```

### Airdrop Functions

```solidity
// User callable
function claimAirdrop() external nonReentrant returns (uint256 amount);

// View functions
function getAirdropInfo(address user) external view returns (
    bool eligible,
    uint256 amount,
    uint256 timeUntilNext
);

function calculateAirdropAmount(uint256 userUsage) public pure returns (uint256 amount);

function getUserStats(address user) external view returns (
    uint256 totalUsage,
    bool active,
    uint256 lastClaim
);
```

### Admin Functions

```solidity
// Owner only
function recordUsage(address user, uint256 count) external onlyOwner;
function mint(address to, uint256 amount) external onlyOwner;

// Anyone can burn their own tokens
function burn(uint256 amount) external;
```

### Events

```solidity
event UsageRecorded(address indexed user, uint256 count);
event UserActivated(address indexed user);
event AirdropClaimed(address indexed user, uint256 amount);

// Standard ERC-20 events
event Transfer(address indexed from, address indexed to, uint256 value);
event Approval(address indexed owner, address indexed spender, uint256 value);
```

### Constants

```solidity
uint256 public constant AIRDROP_INTERVAL = 30 days;
uint256 public constant MIN_USAGE_FOR_AIRDROP = 10;
```

## Deployment Guide

### Prerequisites

```bash
# Install dependencies
npm install --save-dev hardhat @openzeppelin/contracts

# Project structure
contracts/
  └── AgentVaultToken.sol
scripts/
  └── deploy.js
test/
  └── AgentVaultToken.test.js
hardhat.config.js
```

### Configuration

**hardhat.config.js**:
```javascript
require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

module.exports = {
  solidity: {
    version: "0.8.19",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  networks: {
    sepolia: {
      url: process.env.SEPOLIA_RPC_URL,
      accounts: [process.env.DEPLOYER_PRIVATE_KEY],
      chainId: 11155111
    },
    mainnet: {
      url: process.env.MAINNET_RPC_URL,
      accounts: [process.env.DEPLOYER_PRIVATE_KEY],
      chainId: 1
    }
  },
  etherscan: {
    apiKey: process.env.ETHERSCAN_API_KEY
  }
};
```

### Deployment Script

**scripts/deploy.js**:
```javascript
const { ethers } = require("hardhat");

async function main() {
  // Get deployer account
  const [deployer] = await ethers.getSigners();
  console.log("Deploying with account:", deployer.address);

  // Check balance
  const balance = await ethers.provider.getBalance(deployer.address);
  console.log("Account balance:", ethers.formatEther(balance), "ETH");

  // Deploy contract
  const initialSupply = ethers.parseEther("1000000000"); // 1 billion AVT

  console.log("Deploying AgentVaultToken with supply:", ethers.formatEther(initialSupply));

  const AgentVaultToken = await ethers.getContractFactory("AgentVaultToken");
  const token = await AgentVaultToken.deploy(initialSupply);

  await token.waitForDeployment();

  const address = await token.getAddress();
  console.log("AgentVaultToken deployed to:", address);

  // Verify deployment
  const name = await token.name();
  const symbol = await token.symbol();
  const decimals = await token.decimals();
  const totalSupply = await token.totalSupply();

  console.log("Token Name:", name);
  console.log("Token Symbol:", symbol);
  console.log("Token Decimals:", decimals);
  console.log("Total Supply:", ethers.formatEther(totalSupply), symbol);

  // Save deployment info
  const fs = require("fs");
  const deployment = {
    network: hre.network.name,
    address: address,
    deployer: deployer.address,
    timestamp: new Date().toISOString(),
    initialSupply: ethers.formatEther(initialSupply)
  };

  fs.writeFileSync(
    `deployments/${hre.network.name}.json`,
    JSON.stringify(deployment, null, 2)
  );

  console.log("\nDeployment info saved to deployments/" + hre.network.name + ".json");
  console.log("\nNext steps:");
  console.log("1. Verify contract: npx hardhat verify --network", hre.network.name, address, initialSupply);
  console.log("2. Update dashboard config with contract address");
  console.log("3. Transfer ownership if needed");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
```

### Deployment Commands

**Testnet (Sepolia)**:
```bash
# Deploy
npx hardhat run scripts/deploy.js --network sepolia

# Verify on Etherscan
npx hardhat verify --network sepolia <CONTRACT_ADDRESS> <INITIAL_SUPPLY>

# Example
npx hardhat verify --network sepolia 0x123... "1000000000000000000000000000"
```

**Mainnet**:
```bash
# Deploy (use with caution!)
npx hardhat run scripts/deploy.js --network mainnet

# Verify
npx hardhat verify --network mainnet <CONTRACT_ADDRESS> <INITIAL_SUPPLY>
```

### Post-Deployment

**Configuration Updates**:

1. **Dashboard Frontend** (`dashboard/src/config/web3.ts`):
```typescript
export const CONTRACT_ADDRESSES = {
  AGENT_VAULT_TOKEN: {
    [mainnet.id]: '0x...',  // Deployed mainnet address
    [sepolia.id]: '0x...',  // Deployed testnet address
  },
};
```

2. **Backend** (`dashboard/backend/.env`):
```bash
AVT_TOKEN_ADDRESS=0x...
AVT_TOKEN_OWNER_KEY=0x...  # Private key for recordUsage calls
```

3. **MCP Server** (`.env`):
```bash
AVT_TOKEN_ADDRESS=0x...
```

## Security Considerations

### Auditing Checklist

**Before Mainnet Deployment**:
- [ ] Professional smart contract audit
- [ ] Formal verification of critical functions
- [ ] Testnet deployment and testing (min 2 weeks)
- [ ] Bug bounty program
- [ ] Emergency pause mechanism (consider adding)
- [ ] Timelock for owner actions (consider adding)
- [ ] Multi-sig for ownership (recommended)

### Known Considerations

**1. Centralization**:
```
⚠️ Owner controls usage recording
   - Mitigation: Owner is backend server with rate limiting
   - Future: Decentralized oracle network

⚠️ Airdrops come from owner's balance
   - Mitigation: Reserve wallet with monitoring
   - Future: Dedicated airdrop contract
```

**2. Gas Costs**:
```
recordUsage():     ~50,000 gas
claimAirdrop():    ~60,000 gas
mint():            ~50,000 gas

At 50 gwei gas price:
- recordUsage cost: ~$3 per call
- Solution: Batch recording, L2 deployment
```

**3. Reentrancy**:
```
✓ ReentrancyGuard on claimAirdrop()
✓ Checks-Effects-Interactions pattern
✓ No external calls before state updates
```

**4. Integer Overflow**:
```
✓ Solidity 0.8.x has built-in overflow checks
✓ No unchecked arithmetic blocks
```

### Recommended Improvements

**1. Pausability**:
```solidity
import "@openzeppelin/contracts/security/Pausable.sol";

contract AgentVaultToken is ERC20, Ownable, ReentrancyGuard, Pausable {
    function claimAirdrop() external nonReentrant whenNotPaused returns (uint256) {
        // ...
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }
}
```

**2. Timelock**:
```solidity
import "@openzeppelin/contracts/governance/TimelockController.sol";

// Deploy timelock as owner
TimelockController timelock = new TimelockController(
    2 days,    // Minimum delay
    [],        // Proposers
    [],        // Executors
    msg.sender // Admin
);

// Transfer ownership to timelock
token.transferOwnership(address(timelock));
```

**3. Multi-sig**:
```bash
# Use Gnosis Safe as owner
# Create Safe at https://app.safe.global
# Transfer ownership:
token.transferOwnership(SAFE_ADDRESS);
```

**4. Emergency Withdrawal**:
```solidity
function emergencyWithdraw(address token, address to) external onlyOwner {
    // Recover accidentally sent tokens
    IERC20(token).transfer(to, IERC20(token).balanceOf(address(this)));
}
```

## Testing

### Unit Tests

**test/AgentVaultToken.test.js**:
```javascript
const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("AgentVaultToken", function () {
  let token, owner, user1, user2;

  beforeEach(async function () {
    [owner, user1, user2] = await ethers.getSigners();

    const AgentVaultToken = await ethers.getContractFactory("AgentVaultToken");
    token = await AgentVaultToken.deploy(ethers.parseEther("1000000000"));
  });

  describe("Deployment", function () {
    it("Should set the right owner", async function () {
      expect(await token.owner()).to.equal(owner.address);
    });

    it("Should assign the total supply to the owner", async function () {
      const ownerBalance = await token.balanceOf(owner.address);
      expect(await token.totalSupply()).to.equal(ownerBalance);
    });
  });

  describe("Usage Recording", function () {
    it("Should record usage and activate user", async function () {
      await token.recordUsage(user1.address, 10);

      const [usage, active] = await token.getUserStats(user1.address);
      expect(usage).to.equal(10);
      expect(active).to.be.true;
    });

    it("Should not activate user below threshold", async function () {
      await token.recordUsage(user1.address, 5);

      const [usage, active] = await token.getUserStats(user1.address);
      expect(usage).to.equal(5);
      expect(active).to.be.false;
    });
  });

  describe("Airdrops", function () {
    it("Should calculate correct airdrop amount", async function () {
      expect(await token.calculateAirdropAmount(10))
        .to.equal(ethers.parseEther("100"));

      expect(await token.calculateAirdropAmount(50))
        .to.equal(ethers.parseEther("140"));
    });

    it("Should allow eligible users to claim", async function () {
      // Activate user
      await token.recordUsage(user1.address, 50);

      // Fast forward 30 days
      await ethers.provider.send("evm_increaseTime", [30 * 24 * 60 * 60]);
      await ethers.provider.send("evm_mine");

      // Claim
      const tx = await token.connect(user1).claimAirdrop();
      await expect(tx).to.emit(token, "AirdropClaimed");

      // Check balance
      const balance = await token.balanceOf(user1.address);
      expect(balance).to.equal(ethers.parseEther("140"));
    });

    it("Should reject claims before cooldown", async function () {
      await token.recordUsage(user1.address, 10);

      await expect(
        token.connect(user1).claimAirdrop()
      ).to.be.revertedWith("Airdrop not available yet");
    });
  });
});
```

**Run Tests**:
```bash
npx hardhat test
npx hardhat test --network hardhat
npx hardhat coverage  # Test coverage report
```

---

## Integration Examples

### Frontend (React + wagmi)

```typescript
// hooks/useAirdrop.ts
import { useContractRead, useContractWrite, useWaitForTransaction } from 'wagmi';
import { AVT_ADDRESS, AVT_ABI } from '../config/contracts';

export function useAirdrop(userAddress: string) {
  // Read airdrop info
  const { data: airdropInfo } = useContractRead({
    address: AVT_ADDRESS,
    abi: AVT_ABI,
    functionName: 'getAirdropInfo',
    args: [userAddress],
    watch: true,
  });

  // Claim airdrop
  const { data, write: claimAirdrop } = useContractWrite({
    address: AVT_ADDRESS,
    abi: AVT_ABI,
    functionName: 'claimAirdrop',
  });

  const { isLoading } = useWaitForTransaction({
    hash: data?.hash,
  });

  return {
    eligible: airdropInfo?.[0] ?? false,
    amount: airdropInfo?.[1] ?? 0n,
    timeUntilNext: airdropInfo?.[2] ?? 0n,
    claimAirdrop,
    isLoading,
  };
}
```

### Backend (Python + web3.py)

```python
# services/airdrop_service.py
from web3 import Web3
from eth_account import Account

class AirdropService:
    def __init__(self, web3: Web3, contract_address: str, abi: list):
        self.web3 = web3
        self.contract = web3.eth.contract(address=contract_address, abi=abi)
        self.owner = Account.from_key(os.getenv("AVT_OWNER_KEY"))

    async def record_usage(self, user_address: str, count: int) -> str:
        """Record usage on-chain (owner only)"""
        tx = self.contract.functions.recordUsage(user_address, count).build_transaction({
            'from': self.owner.address,
            'nonce': await self.web3.eth.get_transaction_count(self.owner.address),
            'gas': 100000,
        })

        signed = self.owner.sign_transaction(tx)
        tx_hash = await self.web3.eth.send_raw_transaction(signed.rawTransaction)

        return tx_hash.hex()

    async def get_user_stats(self, user_address: str) -> dict:
        """Get user statistics"""
        usage, active, last_claim = self.contract.functions.getUserStats(user_address).call()

        return {
            "total_usage": usage,
            "is_active": active,
            "last_claim_timestamp": last_claim,
        }

    async def check_eligibility(self, user_address: str) -> dict:
        """Check airdrop eligibility"""
        eligible, amount, time_until = self.contract.functions.getAirdropInfo(user_address).call()

        return {
            "eligible": eligible,
            "amount_wei": amount,
            "amount_avt": Web3.from_wei(amount, 'ether'),
            "seconds_until_next": time_until,
        }
```

---

## Conclusion

The AgentVault Token (AVT) creates a sustainable economic model that:

1. ✅ **Rewards Active Users**: Usage-based airdrops incentivize platform engagement
2. ✅ **Aligns Incentives**: More usage = larger rewards = platform growth
3. ✅ **Prevents Gaming**: Time locks and minimum thresholds prevent exploitation
4. ✅ **Maintains Security**: ReentrancyGuard, owner controls, comprehensive testing
5. ✅ **Enables Growth**: Deflationary burn + inflationary airdrops balance supply

**Next Steps**:
1. Complete testnet deployment and testing
2. Professional security audit
3. Integrate with dashboard and MCP server
4. Deploy to mainnet
5. Launch token distribution

For deployment instructions, see [Deployment Guide](#deployment-guide).
For security details, see [../security-audit.md](security-audit.md).
