// Prints each built HTML page to an A4 PDF with Playwright's Chromium, once Mermaid, KaTeX and the fonts are ready.
// NODE_PATH=frontend/node_modules node scripts/docs_pdf.js HTML_DIR OUT_DIR, after scripts/docs_pdf.py has built the HTML
const { chromium } = require("@playwright/test");
const path = require("path");

const [htmlDir, outDir] = process.argv.slice(2);
const docs = {
  "technical-documentation": "Technical documentation",
  "security-self-assessment": "Security self-assessment",
};

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  for (const [name, label] of Object.entries(docs)) {
    await page.goto("file://" + path.resolve(htmlDir, name + ".html"), { waitUntil: "networkidle" });
    await page.waitForFunction(() => window.__ready === true, null, { timeout: 90000 });
    const error = await page.getAttribute("body", "data-error");
    if (error) throw new Error(name + ": " + error);
    const footer = `<div style="font-family: Arial, sans-serif; font-size: 7pt; color: #5b6577; width: 100%; padding: 0 16mm; display: flex; justify-content: space-between;">`
      + `<span>Amanah &middot; ${label} &middot; 20 October 2026</span><span><span class="pageNumber"></span> of <span class="totalPages"></span></span></div>`;
    await page.pdf({
      path: path.resolve(outDir, name + ".pdf"), format: "A4", printBackground: true,
      displayHeaderFooter: true, headerTemplate: "<div></div>", footerTemplate: footer,
      margin: { top: "16mm", bottom: "18mm", left: "16mm", right: "16mm" },
    });
    console.log("printed " + name + ".pdf");
  }
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
