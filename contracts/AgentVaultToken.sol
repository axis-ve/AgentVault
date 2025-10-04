// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/**
 * @title AgentVaultToken (AVT)
 * @dev ERC-20 token for the AgentVault ecosystem
 * Users pay with AVT tokens to use AI agent services
 * Active users receive airdrops based on usage
 */
contract AgentVaultToken is ERC20, Ownable, ReentrancyGuard {
    uint256 public constant AIRDROP_INTERVAL = 30 days;
    uint256 public constant MIN_USAGE_FOR_AIRDROP = 10; // Minimum API calls

    mapping(address => uint256) public lastAirdrop;
    mapping(address => uint256) public usageCount;
    mapping(address => bool) public isActiveUser;

    event UsageRecorded(address indexed user, uint256 count);
    event AirdropClaimed(address indexed user, uint256 amount);
    event UserActivated(address indexed user);

    constructor(
        uint256 initialSupply
    ) ERC20("AgentVault Token", "AVT") Ownable(msg.sender) {
        _mint(msg.sender, initialSupply * 10**decimals());
    }

    /**
     * @dev Record API usage for a user
     * @param user Address of the user
     * @param count Number of API calls made
     */
    function recordUsage(address user, uint256 count) external onlyOwner {
        usageCount[user] += count;

        if (!isActiveUser[user] && usageCount[user] >= MIN_USAGE_FOR_AIRDROP) {
            isActiveUser[user] = true;
            emit UserActivated(user);
        }

        emit UsageRecorded(user, count);
    }

    /**
     * @dev Claim airdrop if eligible
     * @return amount Amount of tokens claimed
     */
    function claimAirdrop() external nonReentrant returns (uint256 amount) {
        require(isActiveUser[msg.sender], "User not active");
        require(
            block.timestamp >= lastAirdrop[msg.sender] + AIRDROP_INTERVAL,
            "Airdrop not available yet"
        );

        // Calculate airdrop amount based on usage
        uint256 userUsage = usageCount[msg.sender];
        amount = calculateAirdropAmount(userUsage);

        require(amount > 0, "No airdrop available");
        require(balanceOf(owner()) >= amount, "Insufficient contract balance");

        // Transfer tokens from owner to user
        _transfer(owner(), msg.sender, amount);

        lastAirdrop[msg.sender] = block.timestamp;
        emit AirdropClaimed(msg.sender, amount);
    }

    /**
     * @dev Calculate airdrop amount based on usage
     * @param userUsage Total API usage count
     * @return amount Tokens to airdrop
     */
    function calculateAirdropAmount(uint256 userUsage) public pure returns (uint256 amount) {
        if (userUsage < MIN_USAGE_FOR_AIRDROP) {
            return 0;
        }

        // Base airdrop: 100 tokens for 10+ usage
        amount = 100 * 10**18();

        // Bonus for high usage: +10 tokens per additional 10 calls
        uint256 bonusUsage = userUsage - MIN_USAGE_FOR_AIRDROP;
        uint256 bonusTokens = (bonusUsage / 10) * 10 * 10**18();

        amount += bonusTokens;
    }

    /**
     * @dev Get user's airdrop eligibility info
     * @param user Address of the user
     * @return eligible Whether user can claim airdrop
     * @return amount Amount available to claim
     * @return timeUntilNext Next claim timestamp
     */
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

    /**
     * @dev Get user's statistics
     * @param user Address of the user
     * @return totalUsage Total API usage count
     * @return active Whether user is considered active
     * @return lastClaim Last airdrop claim timestamp
     */
    function getUserStats(address user) external view returns (
        uint256 totalUsage,
        bool active,
        uint256 lastClaim
    ) {
        return (usageCount[user], isActiveUser[user], lastAirdrop[user]);
    }

    /**
     * @dev Mint new tokens (owner only)
     * @param to Address to mint tokens to
     * @param amount Amount to mint
     */
    function mint(address to, uint256 amount) external onlyOwner {
        _mint(to, amount);
    }

    /**
     * @dev Burn tokens from caller's balance
     * @param amount Amount to burn
     */
    function burn(uint256 amount) external {
        _burn(msg.sender, amount);
    }
}