// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/// @title TestUSDC
/// @notice The Base Sepolia demo's stand-in for USDC (decision A-12): 6 decimals, as USDC has, and only the owner
/// mints. Circle's testnet faucet gives about 20 USDC a request, and the demo deposits 5,000. The vault takes its
/// token's address at deployment, so a production vault takes Circle's USDC with no change. This token has no value.
contract TestUSDC is ERC20, Ownable {
    constructor(address owner_) ERC20("Amanah Test USDC", "tUSDC") Ownable(owner_) {}

    function decimals() public pure override returns (uint8) {
        return 6;
    }

    function mint(address to, uint256 amount) external onlyOwner {
        _mint(to, amount);
    }
}
