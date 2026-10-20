// The voiced cut's drawings (docs/video/cut.py --dialogue), drawn as HTML and screenshotted by Playwright.
//
//   NODE_PATH=frontend/node_modules node docs/video/band.cjs SPEC.json
//
// SPEC.json is written by the cut: {"out": DIR, "bands": [...], "stamps": [...]}. A band is the 1920 by 120 strip
// under the picture: the two speakers at its ends, the speaking one bright and the other dimmed, and the line being
// said in the middle, its stressed words (**word**) in gold, with where the shot was made above it. The space under
// each name is left empty for the cut's waveform of that voice. A stamp is the chip that slides over an attack when
// it is refused, transparent around its edges.

const { chromium } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

const spec = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const GOLD = "#D8A521", CORAL = "#F0716B", NAVY = "#0B1F4B";
// The signers' colours in the app (frontend/src/index.css)
const COLOURS = { planner: "#D9643A", auditor: "#7A5AF0", sentinel: "#0F9AA8", reader: "#4F7FE8" };

const esc = (t) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const stressed = (t) => esc(t).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');

const KEY = `<svg viewBox="0 0 24 24" width="38" height="38" fill="none" stroke="${GOLD}" stroke-width="2.4"
  stroke-linecap="round"><circle cx="8" cy="15.5" r="4.6"/><path d="M11.4 12.1 20 3.5M16.8 6.7l2.6 2.6M14.3 9.2l2 2"/></svg>`;
const LENS = `<svg viewBox="0 0 24 24" width="38" height="38" fill="none" stroke="#fff" stroke-width="2.6"
  stroke-linecap="round"><circle cx="10.4" cy="10.4" r="6.4"/><path d="M15.3 15.3 21 21"/></svg>`;
const SHIELD = (c) => `<svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="${c}" stroke-width="2.4"
  stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 4.5 6v5.6c0 4.6 3.2 8.2 7.5 9.4 4.3-1.2 7.5-4.8 7.5-9.4V6z"/>
  <path d="m8.6 12.2 2.4 2.4 4.6-4.8"/></svg>`;

const FONTS = `<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700;800&family=Noto+Sans+SC:wght@500;700&display=swap">`;

function band(b) {
  const who = (id, name, role, colour, art, right) => `<div class="who ${right ? "r" : "l"} ${b.speaker === id ? "on" : ""}">
      <div class="av ${id}">${art}</div><div class="names"><div class="name">${name}</div>
      <div class="role" style="color:${colour}">${role}</div></div></div>`;
  const rows = (b.rows || []).map((r) => `<div class="row">${stressed(r)}</div>`).join("");
  const bar = b.speaker ? (b.speaker === "H" ? GOLD : CORAL) : "transparent";
  return `<!doctype html><html><head><meta charset="utf-8">${FONTS}<style>
    html,body{margin:0;width:1920px;height:120px;overflow:hidden;background:${NAVY};font-family:Inter,'Noto Sans SC',sans-serif}
    .top{position:absolute;left:0;top:0;width:1920px;height:3px;background:${GOLD}}
    .who{position:absolute;top:18px;display:flex;align-items:flex-start;gap:16px;opacity:.4;transition:none}
    .who.on{opacity:1}.who.l{left:26px}.who.r{right:26px;flex-direction:row-reverse;text-align:right}
    .av{width:76px;height:76px;display:flex;align-items:center;justify-content:center;box-sizing:border-box}
    .av.H{border-radius:50%;background:#13285C;border:4px solid ${GOLD}}
    .av.K{border-radius:20px;background:${CORAL}}
    .name{color:#fff;font-weight:800;font-size:24px;line-height:28px;margin-top:2px}
    .role{font-weight:700;font-size:16px;line-height:20px;letter-spacing:.02em}
    .cap{position:absolute;left:330px;width:1260px;top:0;height:120px;display:flex;flex-direction:column;
         justify-content:center;align-items:center}
    .bar{position:absolute;left:-18px;top:${b.tag ? 30 : 22}px;bottom:${b.tag ? 12 : 22}px;width:6px;border-radius:3px;background:${bar}}
    .tag{color:#8FA0C8;font-weight:700;font-size:14px;letter-spacing:.14em;text-transform:uppercase;height:18px;margin-bottom:4px}
    .row{color:#fff;font-weight:600;font-size:32px;line-height:41px;white-space:nowrap}
    .row b{color:${GOLD};font-weight:800}
  </style></head><body><div class="top"></div>
  ${who("H", "Hafiz", "builds it", GOLD, KEY, false)}
  <div class="cap"><div class="bar"></div>${b.tag ? `<div class="tag">${esc(b.tag)}</div>` : ""}${rows}</div>
  ${who("K", "Khaidhir", "tries to break it", CORAL, LENS, true)}
  </body></html>`;
}

function stamp(s) {
  const c = COLOURS[s.who] || GOLD;
  return `<!doctype html><html><head><meta charset="utf-8">${FONTS}<style>
    html,body{margin:0;background:transparent;font-family:Inter,sans-serif}
    .chip{display:inline-flex;align-items:center;gap:14px;padding:14px 30px 14px 22px;border-radius:999px;
          background:rgba(11,31,75,.94);border:3px solid ${c};box-shadow:0 14px 34px rgba(0,0,0,.35);margin:20px}
    .t{color:#fff;font-weight:800;font-size:30px;letter-spacing:.01em;white-space:nowrap}
  </style></head><body><div class="chip" id="c">${SHIELD(c)}<span class="t">${esc(s.text)}</span></div></body></html>`;
}

(async () => {
  fs.mkdirSync(spec.out, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 120 } });
  let fontsReady = false;
  for (const b of spec.bands || []) {
    await page.setContent(band(b), { waitUntil: fontsReady ? "load" : "networkidle" });
    await page.evaluate(() => document.fonts.ready);
    fontsReady = true;
    // A line too long for the band is a fault in the cut's split, not something to shrink here
    const wide = await page.evaluate(() => Math.max(0, ...[...document.querySelectorAll(".row")].map((r) => r.scrollWidth)));
    if (wide > 1260) console.warn(`${b.name}: a row is ${wide}px wide, over the band's 1260px`);
    await page.screenshot({ path: path.join(spec.out, b.name), clip: { x: 0, y: 0, width: 1920, height: 120 } });
  }
  const chip = await browser.newPage({ viewport: { width: 1200, height: 140 } });
  for (const s of spec.stamps || []) {
    await chip.setContent(stamp(s), { waitUntil: "networkidle" });
    await chip.evaluate(() => document.fonts.ready);
    await chip.locator("#c").screenshot({ path: path.join(spec.out, s.name), omitBackground: true });
  }
  await browser.close();
  console.log(`${(spec.bands || []).length} bands, ${(spec.stamps || []).length} stamps in ${spec.out}`);
})().catch((e) => { console.error(e); process.exit(1); });
