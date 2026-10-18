/** Ports and addresses of the stack that playwright.stack.config.ts starts. */
export const ANVIL_PORT = 8845;
export const API_PORT = 8400;
export const WEB_PORT = 5176;
export const STACK_RPC = `http://127.0.0.1:${ANVIL_PORT}`;
// Anvil's default mnemonic; the fixture registers its accounts (docs/PATHS.md)
export const MNEMONIC = "test test test test test test test test test test test junk";
// A fresh Anvil with the fixture always deploys the vault at this address (docs/PATHS.md)
export const STACK_VAULT = "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512";
