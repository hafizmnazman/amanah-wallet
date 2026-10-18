import { config } from "@/config";

export function txUrl(hash: string): string {
  return `${config.explorerUrl}/tx/${hash}`;
}

export function addressUrl(address: string): string {
  return `${config.explorerUrl}/address/${address}`;
}
