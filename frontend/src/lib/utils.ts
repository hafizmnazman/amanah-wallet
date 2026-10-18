import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** 0x1234abcd...ef56 style shortening for hashes and addresses. */
export function shortHex(value: string, head = 6, tail = 4): string {
  if (!value || value.length <= head + tail + 2) return value;
  return `${value.slice(0, head + 2)}...${value.slice(-tail)}`;
}

/** localStorage that never throws: private windows and previews can block it. */
export const safeStorage = {
  get(key: string): string | null {
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set(key: string, value: string): void {
    try {
      window.localStorage.setItem(key, value);
    } catch {
      // The setting simply does not persist.
    }
  },
};
