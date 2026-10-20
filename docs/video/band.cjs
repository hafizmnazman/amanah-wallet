// The voiced cut's drawings (docs/video/cut.py --dialogue), drawn as HTML and screenshotted by Playwright.
//
//   NODE_PATH=frontend/node_modules node docs/video/band.cjs SPEC.json
//
// SPEC.json is written by the cut: {"out": DIR, "bands": [...], "stamps": [...]}. A band is the 1920 by 120 strip
// under the picture, drawn flat and bold like an explainer: the two speakers at its ends as mascots in round badges
// (Hafiz as Sang Kancil with the vault's key, Khaidhir as Sang Buaya, the crocodile Kancil outwits in the folk
// tale), the speaking one bright with its mouth open on each word ("open") and the other dimmed, and the line being
// said in the middle in a rounded caption box, its stressed words (**word**) in gold, with where the shot was made
// above it. The space under each name is left empty for the cut's waveform of that voice. A stamp is the chip that
// slides over an attack when it is refused, transparent around its edges.

const { chromium } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

const spec = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const GOLD = "#D8A521", CORAL = "#F0716B", NAVY = "#0B1F4B", STRESS = "#FFD34E";
// The signers' colours in the app (frontend/src/index.css)
const COLOURS = { planner: "#D9643A", auditor: "#7A5AF0", sentinel: "#0F9AA8", reader: "#4F7FE8" };

const esc = (t) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const stressed = (t) => esc(t).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');

// Sang Kancil's head and shoulders, after frontend/src/components/mascot/Kancil.tsx, with a gold neckerchief and key
const KANCIL = (open) => `<svg viewBox="22 16 156 156" width="96" height="96">
  <ellipse cx="56" cy="50" rx="15" ry="30" transform="rotate(-38 56 50)" fill="#4f7fe8"/>
  <ellipse cx="58" cy="52" rx="7.5" ry="19" transform="rotate(-38 58 52)" fill="#f7b8cb"/>
  <ellipse cx="144" cy="50" rx="15" ry="30" transform="rotate(38 144 50)" fill="#4f7fe8"/>
  <ellipse cx="142" cy="52" rx="7.5" ry="19" transform="rotate(38 142 52)" fill="#f7b8cb"/>
  <ellipse cx="100" cy="166" rx="44" ry="34" fill="#2f5bc0"/>
  <ellipse cx="100" cy="88" rx="55" ry="49" fill="#4f7fe8"/>
  <path d="M60 118 Q100 146 140 118 Q132 136 100 137 Q68 136 60 118Z" fill="#3f6fd8"/>
  <path d="M86 43 Q100 36 114 43 Q100 52 86 43Z" fill="#2f5bc0"/>
  <ellipse cx="84" cy="60" rx="17" ry="9" fill="#fff" opacity="0.16"/>
  <ellipse cx="100" cy="111" rx="31" ry="21" fill="#eef4ff"/>
  <ellipse cx="63" cy="106" rx="9" ry="6" fill="#f59ab4" opacity="0.5"/>
  <ellipse cx="137" cy="106" rx="9" ry="6" fill="#f59ab4" opacity="0.5"/>
  <ellipse cx="78" cy="85" rx="10.5" ry="12.5" fill="#0f1b33"/><circle cx="74.5" cy="79.5" r="4.2" fill="#fff"/>
  <circle cx="81" cy="90" r="2" fill="#fff" opacity="0.85"/>
  <ellipse cx="122" cy="85" rx="10.5" ry="12.5" fill="#0f1b33"/><circle cx="118.5" cy="79.5" r="4.2" fill="#fff"/>
  <circle cx="125" cy="90" r="2" fill="#fff" opacity="0.85"/>
  <path d="M92 101 Q100 96 108 101 Q107 107 100 109 Q93 107 92 101Z" fill="#1b2a52"/>
  <ellipse cx="97" cy="101" rx="2.6" ry="1.6" fill="#fff" opacity="0.7"/>
  ${open
    ? `<path d="M88 113 Q100 134 112 113 Q100 117 88 113Z" fill="#5b1f33"/><path d="M93 123 Q100 130 107 123 Q100 119 93 123Z" fill="#f07c95"/>`
    : `<path d="M91 115 Q100 123 109 115" stroke="#1b2a52" stroke-width="3.5" stroke-linecap="round" fill="none"/>`}
  <g transform="translate(84 156) rotate(-24)">
    <circle cx="0" cy="0" r="10" fill="none" stroke="#a87c0c" stroke-width="8"/>
    <circle cx="0" cy="0" r="10" fill="none" stroke="${GOLD}" stroke-width="5"/>
    <rect x="8" y="-4" width="32" height="8" rx="4" fill="${GOLD}"/>
    <rect x="29" y="2" width="6" height="9" rx="2.5" fill="${GOLD}"/><rect x="19" y="2" width="6" height="7" rx="2.5" fill="${GOLD}"/>
  </g>
  <ellipse cx="121" cy="140" rx="8.5" ry="7" fill="#4472dc"/>
</svg>`;

// Sang Buaya, the crocodile of the tale, side on and facing the caption: long round snout, eyes on top, a coral
// bandana, no teeth
const BUAYA = (open) => `<svg viewBox="22 16 156 156" width="96" height="96">
  <ellipse cx="122" cy="172" rx="58" ry="36" fill="#2f8a47"/>
  <ellipse cx="106" cy="180" rx="36" ry="22" fill="#bdebb0"/>
  <path d="M74 140 Q114 160 160 128 L164 146 Q116 178 78 158Z" fill="${CORAL}"/>
  <path d="M78 158 Q116 178 164 146 L163 153 Q116 186 80 165Z" fill="#c94f4a"/>
  <path d="M146 150 L168 170 L140 168Z" fill="${CORAL}"/>
  <circle cx="134" cy="62" r="16" fill="#2f8a47"/>
  <circle cx="152" cy="76" r="6" fill="#2f8a47"/><circle cx="162" cy="92" r="5.5" fill="#2f8a47"/>
  <ellipse cx="120" cy="102" rx="48" ry="42" fill="#2f8a47"/>
  <ellipse cx="118" cy="97" rx="46" ry="40" fill="#4cb35e"/>
  ${open
    ? `<path d="M44 114 L132 108 L132 134 L46 138Z" fill="#5b1f33"/><ellipse cx="84" cy="130" rx="26" ry="5" fill="#f07c95"/>
       <rect x="42" y="125" width="90" height="20" rx="10" fill="#7ed07a" transform="rotate(-4 132 125)"/>`
    : `<rect x="42" y="112" width="86" height="21" rx="10.5" fill="#7ed07a"/>`}
  <rect x="36" y="92" width="94" height="30" rx="15" fill="#4cb35e"/>
  <ellipse cx="70" cy="100" rx="18" ry="5" fill="#fff" opacity="0.18"/>
  <circle cx="47" cy="94" r="9" fill="#4cb35e"/><ellipse cx="45" cy="92" rx="3.4" ry="2.6" fill="#2f6b3a"/>
  ${open ? "" : `<path d="M46 122 Q88 127 124 119 Q131 117 133 111" stroke="#1f5a32" stroke-width="4" stroke-linecap="round" fill="none"/>`}
  <circle cx="106" cy="64" r="21" fill="#4cb35e"/>
  <ellipse cx="100" cy="55" rx="8" ry="4.5" fill="#fff" opacity="0.2"/>
  <ellipse cx="102" cy="66" rx="9.5" ry="11" fill="#0f1b33"/><circle cx="98.5" cy="61" r="3.9" fill="#fff"/>
  <circle cx="105" cy="71" r="1.8" fill="#fff" opacity="0.85"/>
  <ellipse cx="128" cy="108" rx="9" ry="5.5" fill="#ff9bb0" opacity="0.75"/>
</svg>`;

// A Kancil's shield: a gold shield with the mouse-deer's ears and a tick, on the signer's colour
const KSHIELD = (c) => `<svg viewBox="0 0 60 60" width="54" height="54"><circle cx="30" cy="30" r="30" fill="${c}"/>
  <ellipse cx="19" cy="16" rx="5" ry="10" transform="rotate(-32 19 16)" fill="#a87c0c"/>
  <ellipse cx="41" cy="16" rx="5" ry="10" transform="rotate(32 41 16)" fill="#a87c0c"/>
  <path d="M30 13 L45 19 L43.5 34 Q40 44 30 49 Q20 44 16.5 34 L15 19Z" fill="${GOLD}"/>
  <path d="M30 13 L45 19 L43.5 34 Q40 44 30 49Z" fill="${STRESS}" opacity="0.6"/>
  <path d="M23 31 L28 36 L38 25" stroke="#fff" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>`;

const FONTS = `<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Nunito:wght@700;800;900&family=Noto+Sans+SC:wght@700;900&display=swap">`;

function band(b) {
  const who = (id, name, role, colour, art, right) => `<div class="who ${right ? "r" : "l"} ${b.speaker === id ? "on" : ""} ${b.speaker === id && b.open ? "open" : ""}">
      <div class="badge" style="border-color:${colour}">${art(b.speaker === id && b.open)}</div>
      <div class="names"><div class="pill" style="background:${colour}">${name}</div>
      <div class="role" style="color:${colour}">${role}</div></div></div>`;
  const rows = (b.rows || []).map((r) => `<div class="row">${stressed(r)}</div>`).join("");
  const bar = b.speaker ? (b.speaker === "H" ? GOLD : CORAL) : "transparent";
  return `<!doctype html><html><head><meta charset="utf-8">${FONTS}<style>
    html,body{margin:0;width:1920px;height:120px;overflow:hidden;background:${NAVY};font-family:Nunito,'Noto Sans SC',sans-serif}
    .top{position:absolute;left:0;top:0;width:1920px;height:3px;background:${GOLD}}
    .who{position:absolute;top:8px;display:flex;align-items:flex-start;gap:14px;opacity:.45}
    .who.on{opacity:1}.who.l{left:14px}.who.r{right:14px;flex-direction:row-reverse;text-align:right}
    .badge{width:104px;height:104px;border-radius:50%;border:4px solid;box-sizing:border-box;overflow:hidden;
           background:#17336F;display:flex;align-items:center;justify-content:center}
    .who.open .badge{transform:translateY(-4px)}
    .names{display:flex;flex-direction:column;align-items:flex-start;padding-top:6px}
    .who.r .names{align-items:flex-end}
    .pill{color:${NAVY};font-weight:900;font-size:24px;line-height:30px;padding:0 14px;border-radius:999px}
    .role{font-weight:800;font-size:17px;line-height:20px;margin-top:5px;padding:0 4px}
    .cap{position:absolute;left:330px;width:1260px;top:0;height:120px;display:flex;flex-direction:column;
         justify-content:center;align-items:center}
    .tag{color:#8FA0C8;font-weight:800;font-size:14px;letter-spacing:.14em;text-transform:uppercase;line-height:16px;margin-bottom:5px}
    .box{position:relative;overflow:hidden;background:rgba(6,18,46,.85);border-radius:16px;padding:5px 28px 6px 34px;
         max-width:1260px;box-sizing:border-box}
    .box i{position:absolute;left:0;top:0;bottom:0;width:6px;background:${bar}}
    .row{color:#fff;font-weight:800;font-size:32px;line-height:38px;white-space:nowrap;text-align:center}
    .row b{color:${STRESS};font-weight:900}
  </style></head><body><div class="top"></div>
  ${who("H", "Hafiz", "Builds it", GOLD, KANCIL, false)}
  <div class="cap">${b.tag ? `<div class="tag">${esc(b.tag)}</div>` : ""}${rows ? `<div class="box"><i></i>${rows}</div>` : ""}</div>
  ${who("K", "Khaidhir", "Tries to break it", CORAL, BUAYA, true)}
  </body></html>`;
}

function stamp(s) {
  const c = COLOURS[s.who] || GOLD;
  return `<!doctype html><html><head><meta charset="utf-8">${FONTS}<style>
    html,body{margin:0;background:transparent;font-family:Nunito,'Noto Sans SC',sans-serif}
    .chip{position:relative;overflow:hidden;display:inline-flex;align-items:center;gap:16px;padding:10px 32px 10px 18px;
          border-radius:22px;background:rgba(6,18,46,.94);border:4px solid ${c};box-shadow:0 7px 0 rgba(0,0,0,.35);margin:20px}
    .t{color:#fff;font-weight:900;font-size:31px;letter-spacing:.01em;white-space:nowrap}
  </style></head><body><div class="chip" id="c">${KSHIELD(c)}<span class="t">${esc(s.text)}</span></div></body></html>`;
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
    const wide = await page.evaluate(() => Math.max(0, ...[...document.querySelectorAll(".row")].map((r) => r.scrollWidth + 62)));
    if (wide > 1260) console.warn(`${b.name}: a caption is ${wide}px wide, over the band's 1260px`);
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
