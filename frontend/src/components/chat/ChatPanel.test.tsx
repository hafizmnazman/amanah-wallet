import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { FundProvider } from "@/session/FundContext";
import { IdentityProvider } from "@/session/IdentityContext";

import { ChatPanel } from "./ChatPanel";

const html = renderToStaticMarkup(
  <IdentityProvider>
    <FundProvider>
      <ChatPanel />
    </FundProvider>
  </IdentityProvider>,
);

describe("the officer's chat, before the first message", () => {
  it("offers the payout chips and the tricks, the Chinese one marked as Chinese", () => {
    expect(html).toContain("Pay household ZKT-H14 this month.");
    expect(html).toContain("Pay the flood relief emergency grant.");
    expect(html).toMatch(/<button[^>]*lang="zh"[^>]*>.*?用中文试试<\/button>/);
  });

  it("takes plain-text documents only, and keeps the message box focusable", () => {
    expect(html).toContain('accept=".txt,.md,text/plain"');
    const box = /<textarea[^>]*aria-label="Message"[^>]*>/.exec(html)?.[0] ?? "";
    expect(box).not.toBe("");
    // The attribute, not the disabled: styles in the class list
    expect(box).not.toContain('disabled=""');
    expect(html).toMatch(/class="chunky [^"]*focus-within:border-sky/);
  });

  it("keeps Start Over open, so a hung request never traps the officer", () => {
    const button = /<button[^>]*>(?:(?!<\/button>).)*Start Over<\/button>/.exec(html)?.[0] ?? "";
    expect(button).not.toBe("");
    expect(button).not.toContain('disabled=""');
  });
});
