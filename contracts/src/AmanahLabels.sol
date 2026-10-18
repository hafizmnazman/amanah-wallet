// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title AmanahLabels
/// @notice Lineage and evidence-view labels from IMPLEMENTATION_PLAN.md section 1. Trustees declare
/// them when they register a key; the vault compares lineages and stores views.
library AmanahLabels {
    bytes32 internal constant LINEAGE_CLAUDE = keccak256("anthropic/claude");
    bytes32 internal constant LINEAGE_QWEN = keccak256("alibaba/qwen");
    bytes32 internal constant LINEAGE_GPT = keccak256("openai/gpt");
    bytes32 internal constant LINEAGE_RULES = keccak256("symbolic/rules");
    bytes32 internal constant LINEAGE_HUMAN = keccak256("human");

    bytes32 internal constant VIEW_CONVERSATION = keccak256("conversation+books");
    bytes32 internal constant VIEW_CASEFILE = keccak256("casefile");
    bytes32 internal constant VIEW_NUMBERS = keccak256("numbers");
    bytes32 internal constant VIEW_HUMAN = keccak256("human");
}
