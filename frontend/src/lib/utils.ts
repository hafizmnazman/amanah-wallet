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

const SMALL_WORDS = new Set(["a", "an", "and", "as", "at", "but", "by", "for", "from", "in", "nor", "of", "on", "or", "per", "the", "to", "via", "vs", "with"]);

/**
 * Title Case for labels that arrive as data, such as the books' programme names: each word starts with a
 * capital, except short joining words inside the title. A word that already holds a capital or a digit, such
 * as a programme code, is left as it is. The data itself never changes, only how it is shown.
 */
export function titleCase(text: string): string {
  const words = text.split(" ");
  return words
    .map((word, i) => {
      if (/[A-Z0-9]/.test(word)) return word;
      const inside = i > 0 && i < words.length - 1 && !words[i - 1].endsWith(":");
      if (inside && SMALL_WORDS.has(word.replace(/[^a-z]/g, ""))) return word;
      return word
        .split("-")
        .map((part) => part.replace(/[a-z]/, (c) => c.toUpperCase()))
        .join("-");
    })
    .join(" ");
}

/** A status value from the API, such as "paid", with its first letter capitalised for a badge. */
export function capitalise(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
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
