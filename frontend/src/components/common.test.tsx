import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ApiError } from "@/api/http";
import { NOT_REACHABLE } from "@/lib/errors";
import { IdentityProvider } from "@/session/IdentityContext";

import { ErrorNote, LoadingLine, RoleHint, statusLabel } from "./common";
import { SignerChip } from "./signers";

describe("shared pieces", () => {
  it("renders the role hint with its Act as Trustee button", () => {
    const html = renderToStaticMarkup(
      <IdentityProvider>
        <RoleHint expected={false} label="trustees" role="trustee" />
      </IdentityProvider>,
    );
    expect(html).toContain("This page is for trustees.");
    expect(html).toMatch(/<button[^>]*>Act as Trustee<\/button>/);
  });

  it("renders no role hint for the expected role", () => {
    const html = renderToStaticMarkup(
      <IdentityProvider>
        <RoleHint expected label="trustees" role="trustee" />
      </IdentityProvider>,
    );
    expect(html).toBe("");
  });

  it("shows errors in plain words, never the browser's or the status code's", () => {
    expect(renderToStaticMarkup(<ErrorNote error={new TypeError("Failed to fetch")} />)).toContain(NOT_REACHABLE.replace("'", "&#x27;"));
    const html = renderToStaticMarkup(<ErrorNote error={new ApiError(413, "Documents over 1 MB are not read.")} />);
    expect(html).toContain(">Documents over 1 MB are not read.<");
  });

  it("has one loading line, and status labels as the badges write them", () => {
    expect(renderToStaticMarkup(<LoadingLine />)).toContain("Checking the vault...");
    expect(statusLabel("elevated_pending")).toBe("Waiting for a Trustee");
    expect(statusLabel("something_new")).toBe("Something new");
  });

  it("gives a signer chip its verdict in words for a screen reader", () => {
    const html = renderToStaticMarkup(<SignerChip signer="auditor" verdict="UNAVAILABLE" signed={false} />);
    expect(html).toContain('<span class="sr-only">Auditor (Qwen): did not answer, not signed</span>');
  });
});
