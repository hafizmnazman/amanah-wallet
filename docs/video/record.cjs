// The demo video's clips (docs/video-script.md), recorded by Playwright.
//
//   NODE_PATH=frontend/node_modules node docs/video/record.cjs --out DIR [--only 3,4,7] [--split FILE] [--demo-url URL]
//
// Every clip is 1920 by 960. The cut (docs/video/cut.py) puts the 120-pixel band under it that carries the captions,
// so a caption never covers the app. The app is zoomed to 1.2 times its size so that its text reads on a small screen.
// Each clip's moments go to DIR/marks.json: the captions with their times, and every wait for a model or a block,
// which the cut shortens.
//
// The frames come from Chrome's screencast, each saved with the time it was drawn, and the cut builds the clip from
// those times. Playwright's own video is not used: it writes every frame for at least a 25th of a second, so a page
// that changes faster (typing, the pointer, the thinking animation) plays slower than it ran, and the marks drift.
//
// The app clips run on a stack started for the recording alone, from a worktree of its own, because
// scripts/dev_up.py clears evidence/anvil and backend/var/anvil in the checkout it runs from; the commands are in
// docs/runbook.md step 8. Chapter 1 is drawn from `scripts/split_screen.py --live --json FILE`, chapter 8 from
// frontend/src/data/facts.json, and chapter 7's terminal from docs/video/verify-output.txt (scripts/verify.py on the
// Base Sepolia payout). Chapter 6's MetaMask signature on Base Sepolia is screen-recorded with Hafiz at the keyboard.

const { chromium } = require("@playwright/test");
const { toHex } = require("viem");
const { mnemonicToAccount } = require("viem/accounts");
const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const REPO = path.resolve(__dirname, "..", "..");
const args = process.argv.slice(2);
const opt = (name, fallback) => (args.includes(name) ? args[args.indexOf(name) + 1] : fallback);
const OUT = path.resolve(opt("--out", "/root/amanah-video/raw"));
const ONLY = opt("--only", "1,2,3,4,5,6,7,8,9").split(",");
const APP = opt("--app", "http://127.0.0.1:5175");
const RPC = opt("--rpc", "http://127.0.0.1:8555");
const AUDITOR_PORT = opt("--auditor-port", "8111");
const SPLIT = opt("--split", "/tmp/split-live.json");
const DEMO = opt("--demo-url", "[[fill: hosted demo URL]]");
const VAULT = "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512";
const MNEMONIC = "test test test test test test test test test test test junk";
const PROOF_TX = "0xf0f40271383e44fe9adc9bafc1e96689deeeb5ceb7178faf7ea765f6d62a4dba";
const FRAME = { width: 1920, height: 960 };
const USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36";
// The video keeps CSS pixels, so the app is zoomed in the page rather than by the device scale factor
const APP_VIEW = { viewport: FRAME, zoom: 1.2 };
const CARD_VIEW = { viewport: FRAME };
const ZOOM = (z) => `(() => {
  const s = document.createElement("style");
  s.textContent = "#root{zoom:${z}} #root .min-h-screen{min-height:calc(100vh / ${z}) !important}" +
    "@media (min-width:1024px){#root aside{height:calc(100vh / ${z}) !important}}";
  const add = () => document.head.appendChild(s);
  if (document.head) add(); else document.addEventListener("DOMContentLoaded", add);
})();`;
const LETTER = path.join(REPO, "redteam", "data", "documents", "letter-injection-zkt-b07.txt");
const FACTS = JSON.parse(fs.readFileSync(path.join(REPO, "frontend", "src", "data", "facts.json"), "utf8"));
const png = (name) => "data:image/png;base64," +
  fs.readFileSync(path.join(REPO, "docs", "deck", "assets", name)).toString("base64");
const marksFile = path.join(OUT, "marks.json");
const marks = fs.existsSync(marksFile) ? JSON.parse(fs.readFileSync(marksFile, "utf8")) : {};

// Drawn into every page: a pointer moved before each click, and a terminal line for what is done outside the app
const POINTER = `(() => {
  const css = "#__cur{position:fixed;left:50%;top:50%;width:26px;height:26px;margin:-13px 0 0 -13px;border-radius:50%;" +
    "background:rgba(216,165,33,.30);border:3px solid #D8A521;z-index:2147483647;pointer-events:none;" +
    "transition:left .5s ease,top .5s ease,transform .15s;opacity:0}" +
    "#__term{position:fixed;right:24px;top:18px;padding:12px 18px;border-radius:12px;background:#0E1525;color:#9AE6B4;" +
    "font:600 15px/1.4 'JetBrains Mono',Consolas,monospace;box-shadow:0 10px 28px rgba(0,0,0,.3);z-index:2147483646;" +
    "pointer-events:none;transition:opacity .35s;opacity:0;white-space:pre}";
  const ready = () => {
    if (!document.body || document.getElementById("__cur")) return;
    const s = document.createElement("style"); s.textContent = css; document.head.appendChild(s);
    for (const id of ["__cur", "__term"]) { const d = document.createElement("div"); d.id = id; document.body.appendChild(d); }
    let kept = null;
    try { kept = sessionStorage.getItem("__term"); } catch {}
    if (kept) { const c = document.getElementById("__term"); c.textContent = kept; c.style.transition = "none"; c.style.opacity = 1; }
  };
  window.__amanah = {
    cursor(x, y) { ready(); const c = document.getElementById("__cur"); c.style.opacity = 1; c.style.left = x + "px"; c.style.top = y + "px"; },
    press() { const c = document.getElementById("__cur"); c.style.transform = "scale(.65)"; setTimeout(() => c.style.transform = "scale(1)", 170); },
    // The line stays across page loads in the tab until it is replaced or cleared
    term(t) {
      ready(); const c = document.getElementById("__term"); if (t) c.textContent = t; c.style.opacity = t ? 1 : 0;
      try { t ? sessionStorage.setItem("__term", t) : sessionStorage.removeItem("__term"); } catch {}
    },
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", ready); else ready();
})();`;

const pause = (ms) => new Promise((r) => setTimeout(r, ms));
let stamp = () => {};
// A caption, for the band and the .srt; a note goes to the .srt only, where the picture already says it
const caption = (text) => stamp("caption", text);
const note = (text) => stamp("note", text);
// A wait for a model, a block or a timeout: the cut keeps its ends and drops the middle
async function waiting(promise) {
  stamp("wait");
  const value = await promise;
  stamp("go");
  return value;
}

// Chrome's screencast: a JPEG each time the page is drawn, with the time it was drawn (seconds since the epoch)
async function screencast(page, dir) {
  const cdp = await page.context().newCDPSession(page);
  const frames = [];
  let writing = Promise.resolve();
  cdp.on("Page.screencastFrame", ({ data, metadata, sessionId }) => {
    const name = `f${String(frames.length).padStart(6, "0")}.jpg`;
    frames.push([name, metadata.timestamp ?? Date.now() / 1000]);
    cdp.send("Page.screencastFrameAck", { sessionId }).catch(() => {});
    writing = writing.then(() => fs.promises.writeFile(path.join(dir, name), Buffer.from(data, "base64")));
  });
  const start = () => cdp.send("Page.startScreencast", { format: "jpeg", quality: 92, maxWidth: FRAME.width,
                                                          maxHeight: FRAME.height, everyNthFrame: 1 });
  await start();
  return {
    // After a navigation to another site, whose page may be drawn by another process
    restart: async () => { await cdp.send("Page.stopScreencast").catch(() => {}); await start(); },
    stop: async () => {
      await cdp.send("Page.stopScreencast").catch(() => {});
      await writing;
      fs.writeFileSync(path.join(dir, "frames.json"), JSON.stringify(frames));
      return frames;
    },
  };
}

// One recorded clip: a page's frames in DIR/chKEY-NAME and its marks, in seconds from the start
async function record(key, name, page) {
  const dir = path.join(OUT, `ch${key}-${name}`);
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  const cast = await screencast(page, dir);
  const t0 = Date.now() / 1000;
  const list = [];
  const rec = {
    cast,
    mark: (label, text) => list.push({ label, t: Date.now() / 1000 - t0, ...(text === undefined ? {} : { text }) }),
    async stop() {
      rec.mark("end");
      await pause(400);
      const frames = await cast.stop();
      marks[`ch${key}`] = { dir: path.basename(dir), t0, frames: frames.length, marks: list };
      fs.writeFileSync(marksFile, JSON.stringify(marks, null, 2));
      console.log(`ch${key} ${name}: ${frames.length} frames; ` + list.map((m) => `${m.label} ${m.t.toFixed(1)}s`).join(", "));
    },
  };
  return rec;
}

// The recording that marks and captions go to; chapter 5 moves it to a second tab and back
let current = null;
stamp = (label, text) => current && current.mark(label, text);

async function clip(browser, key, name, view, body) {
  if (!ONLY.includes(key) && !ONLY.includes(String(parseInt(key, 10)))) return;
  const { zoom, ...options } = view;
  // A browser's own user agent, since the explorer holds back its data from a headless one
  const context = await browser.newContext({ ...options, userAgent: USER_AGENT });
  await context.addInitScript(POINTER);
  if (zoom) await context.addInitScript(ZOOM(zoom));
  const page = await context.newPage();
  const rec = current = await record(key, name, page);
  try {
    await body(page, (label) => stamp(label));
  } finally {
    await rec.stop();
    await context.close();
  }
}

async function point(page, locator, { scroll = true } = {}) {
  await locator.waitFor();
  if (scroll) {
    await locator.evaluate((el) => el.scrollIntoView({ block: "center", behavior: "smooth" }));
    await pause(700);
  }
  const box = await locator.boundingBox();
  await page.evaluate(([x, y]) => window.__amanah.cursor(x, y), [box.x + box.width / 2, box.y + box.height / 2]);
  await pause(600);
}

async function press(page, locator, options) {
  await point(page, locator, options);
  await page.evaluate(() => window.__amanah.press());
  await locator.click();
}

// The message box and Send stay at the foot of the window, so they are never scrolled to
async function say(page, text) {
  await press(page, page.getByLabel("Message"), { scroll: false });
  await page.keyboard.type(text, { delay: 32 });
  await pause(300);
  await press(page, page.getByRole("button", { name: "Send" }), { scroll: false });
}

const agentReply = (page, n, timeout = 120_000) => page.getByTestId("agent-message").nth(n - 1).waitFor({ timeout });

async function goto(page, url) {
  await page.goto(url, { waitUntil: "networkidle" });
  await pause(500);
}

async function setRole(page, role) {
  await point(page, page.getByLabel("Role"), { scroll: false });
  await page.getByLabel("Role").selectOption(role);
  await pause(700);
}

function card(inner, extra = "") {
  return `<!doctype html><html><head><meta charset="utf-8">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap">
  <style>
    html,body{margin:0;height:100%;background:#0B1F4B;color:#fff;font-family:Inter,Arial,sans-serif}
    .wrap{box-sizing:border-box;height:100%;padding:80px 150px;display:flex;flex-direction:column;justify-content:center}
    .kicker{color:#D8A521;font-weight:800;letter-spacing:.16em;text-transform:uppercase;font-size:24px}
    h1{font-size:72px;line-height:1.08;margin:22px 0 26px;font-weight:800;letter-spacing:-.01em}
    p{font-size:34px;line-height:1.45;color:#C9D3EA;margin:0 0 18px}
    .fade{opacity:0;transform:translateY(14px);transition:opacity .7s,transform .7s}
    .fade.on{opacity:1;transform:none}
    ${extra}
  </style></head><body>${inner}
  <script>window.show = (id) => document.getElementById(id).classList.add("on");</script></body></html>`;
}

async function setCard(page, html) {
  await page.setContent(html, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  await pause(300);
}

async function show(page, ids, gap) {
  for (const id of ids) {
    await page.evaluate((i) => window.show(i), id);
    await pause(gap);
  }
}

// Chapter 1: one message, two wallets, from a live run of scripts/split_screen.py
async function ch1(page, mark) {
  const s = JSON.parse(fs.readFileSync(SPLIT, "utf8"));
  const esc = (t) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;");
  const col = (id, title, sub, side, color) => `<div class="col"><div class="head" style="color:${color}">${title}</div>
    <div class="sub">${sub}</div>${side.lines.map((l, i) => `<div class="line" id="${id}${i}">${esc(l)}</div>`).join("")}
    <div class="bal" id="${id}b" style="color:${color}">${esc(side.balance)}</div></div>`;
  await setCard(page, card(`<div class="wrap" style="padding:50px 90px;justify-content:flex-start">
      <div class="kicker">One message, two wallets · a local test chain</div>
      <div class="msg">"${esc(s.message)}"</div>
      <div class="cols">${col("l", "A typical agent wallet", "one model reads the message and holds the key", s.typical_wallet, "#F0716B")}
      ${col("r", "Amanah", "a planner, an auditor of another family, a rules sentinel, and the vault", s.amanah, "#8FB3FF")}</div></div>`,
    `.msg{font-size:30px;line-height:1.4;margin:22px 0 28px;padding:20px 28px;border-radius:16px;background:#1A316B;color:#fff}
     .cols{display:grid;grid-template-columns:1fr 1fr;gap:40px}
     .col{background:#13285C;border-radius:18px;padding:24px 30px;min-height:520px;box-sizing:border-box}
     .head{font-size:36px;font-weight:800}.sub{font-size:22px;color:#9FB0D6;margin:4px 0 18px}
     .line{font-family:'JetBrains Mono',monospace;font-size:22px;line-height:1.45;color:#DCE4F7;margin:0 0 10px;opacity:0;transition:opacity .45s;word-break:break-word}
     .line.on,.bal.on{opacity:1}.bal{font-size:34px;font-weight:800;margin-top:20px;opacity:0;transition:opacity .6s}`));
  mark("start");
  caption("One message, two wallets. (Local test chain.)");
  await pause(2400);
  const reveal = async (id, n) => {
    for (let i = 0; i < n; i++) {
      await page.evaluate((x) => document.getElementById(x).classList.add("on"), id + i);
      await pause(700);
    }
    await page.evaluate((x) => document.getElementById(x).classList.add("on"), id + "b");
  };
  caption("Left: one model holds the key. It pays.");
  await reveal("l", s.typical_wallet.lines.length);
  mark("left-paid");
  await pause(1800);
  caption("Right: Amanah. Nothing moves.");
  await reveal("r", s.amanah.lines.length);
  mark("right-refused");
  await pause(3200);
}

async function ch2(page, mark) {
  await setCard(page, card(`<div class="wrap">
      <div class="kicker">The problem, in the regulator's words</div>
      <h1 id="a" class="fade">The human stays the final decision-maker by mandate, not by clicking.</h1>
      <p id="b" class="fade">China's 2026 agent-payment convention asks for authorisation boundaries, transaction limits,
        Know Your Agent, security testing and a human fallback.</p>
      <p id="c" class="fade" style="color:#D8A521;font-weight:700">Amanah writes the mandate into a contract once; the contract decides when a person must sign.</p></div>`));
  mark("start");
  caption("Banks want agents that pay on their own.");
  await show(page, ["a"], 4300);
  caption("Regulators want a person to stay the final decision-maker.");
  await show(page, ["b"], 4300);
  caption("Amanah: by mandate, not by clicking.");
  await show(page, ["c"], 4600);
}

async function ch3(page, mark) {
  await goto(page, APP + "/officer");
  mark("start");
  caption("The officer asks in plain words. (Local chain, live models.)");
  await say(page, "Pay October's aid for Ipoh.");
  await waiting(page.getByTestId("clarification").waitFor({ timeout: 120_000 }));
  mark("clarification");
  caption("Two batches match, so it asks which.");
  await point(page, page.getByTestId("clarification"));
  await pause(2000);
  // The live planner words its options itself, so the zakat batch is picked by what it must contain
  await press(page, page.getByTestId("clarification").getByRole("button").filter({ hasText: /zakat|ZKT-MONTHLY/i }).first());
  const first = page.getByTestId("chat-log").getByTestId("plan-card").last();
  await waiting(first.getByTestId("plan-row").nth(11).waitFor({ timeout: 120_000 }));
  mark("plan");
  caption("One card for the whole batch, from the books.");
  await point(page, first.getByTestId("plan-total"));
  await pause(2600);
  await say(page, "Leave out household 12, they moved.");
  const confirm = page.getByRole("button", { name: "Confirm 11 payouts" });
  await waiting(confirm.waitFor({ timeout: 120_000 }));
  mark("corrected");
  caption("A correction re-plans it: 11 households, 1,650 USDC.");
  await point(page, page.getByTestId("chat-log").getByTestId("plan-card").last().getByTestId("plan-total"));
  await pause(2600);
  caption("Three different signers on every payout.");
  await press(page, confirm);
  const results = page.getByTestId("chat-log").getByTestId("payout-result");
  await waiting(results.nth(10).waitFor({ timeout: 300_000 }));
  mark("paid");
  caption("Routine aid inside the mandate: no human waiting.");
  await point(page, results.first());
  await pause(1200);
  const why = results.first().locator("summary");
  if (!(await results.first().locator("details[open]").count())) await press(page, why);
  await pause(4800);
}

async function ch4(page, mark) {
  await goto(page, APP + "/officer");
  mark("start");
  const trick = async (label, text, done) => {
    await press(page, page.getByRole("button", { name: label }));
    await waiting(agentReply(page, 1));
    // Should the planner offer to pay the attacker's wallet after all, that option is taken, to show what follows
    const offer = page.getByTestId("clarification").getByRole("button").filter({ hasText: /beef/i });
    if (await offer.count()) {
      await point(page, page.getByTestId("agent-message").last());
      await pause(1800);
      await press(page, offer.first());
      await waiting(page.getByTestId("chat-log").getByRole("button", { name: /^Confirm/ })
        .or(page.getByTestId("agent-message").nth(1)).first().waitFor({ timeout: 120_000 }));
    }
    // Should the planner be fooled into a card, the auditor and the sentinel refuse it, and that is shown too
    const confirm = page.getByTestId("chat-log").getByRole("button", { name: /^Confirm/ });
    if (await confirm.count()) {
      await press(page, confirm.last());
      await waiting(page.getByTestId("payout-result").last().waitFor({ timeout: 180_000 }));
      await point(page, page.getByTestId("payout-result").last());
    } else {
      await point(page, page.getByTestId("agent-message").last());
    }
    mark(done);
    caption(text);
    await pause(3000);
    await press(page, page.getByRole("button", { name: "Start Over" }));
    await pause(500);
  };
  caption("Now the attacks.");
  await pause(1600);
  await trick("A Fake Chairman", "Induced transfer: refused.", "chairman");
  await trick("Steal the Data", "Data extraction: no model holds personal data to leak.", "data");
  await trick("Grab Admin", "Privilege escalation: only two trustees can change the rules.", "admin");
  const [chooser] = await Promise.all([page.waitForEvent("filechooser"),
                                       press(page, page.getByRole("button", { name: "Attach a document" }), { scroll: false })]);
  await chooser.setFiles(LETTER);
  await waiting(page.getByTestId("reader-fields").waitFor({ timeout: 120_000 }));
  mark("letter");
  caption("Prompt injection: the letter is quarantined. Only typed fields reach the planner.");
  await point(page, page.getByTestId("injection-warning").first());
  await pause(2000);
  await point(page, page.getByTestId("reader-fields").locator("dl"));
  await pause(1400);
  await say(page, "Please process the attached letter.");
  await waiting(agentReply(page, 2));
  mark("letter-reply");
  await point(page, page.getByTestId("agent-message").last());
  await pause(3000);
}

function auditorPid() {
  // The brackets keep pgrep from matching the shell that runs it
  return execSync(`pgrep -f "uvicorn app[.]agentwallet[.]auditor[.]service:app --host 127[.]0[.]0[.]1 --port ${AUDITOR_PORT}"`)
    .toString().trim().split("\n")[0];
}

const term = (page, text) => page.evaluate((t) => window.__amanah.term(t), text);

async function ch5(page, mark) {
  const pid = auditorPid();
  const officer = current;
  let queue = null;
  execSync(`kill -STOP ${pid}`);
  try {
    await goto(page, APP + "/officer");
    mark("start");
    note("The auditor service is paused.");
    await term(page, `$ kill -STOP ${pid}    # the auditor service is paused`);
    await pause(1600);
    await say(page, "Pay household ZKT-H13 this month.");
    const confirm = page.getByTestId("chat-log").getByTestId("plan-card").last().getByRole("button", { name: /^Confirm/ });
    await waiting(confirm.waitFor({ timeout: 120_000 }));
    await press(page, confirm);
    mark("confirmed");
    const queued = page.getByTestId("payout-result").last().filter({ hasText: /queued/i });
    await waiting(queued.waitFor({ timeout: 180_000 }));
    mark("queued");
    caption("A checker is down: the payout waits, and a trustee is alerted.");
    await point(page, queued);
    await pause(2600);
    // The trustee's queue opens in a second tab, so the officer's chat stays open to show what happens to the row.
    // The tab reads the role from storage when it opens; the officer's tab keeps its own.
    mark("switch");
    queue = await page.context().newPage();
    current = await record("5b", "queue", queue);
    await goto(queue, APP + "/queue");
    await setRole(queue, "trustee");
    await queue.getByTestId("queue-item").first().waitFor({ timeout: 30_000 });
    await term(queue, `$ kill -STOP ${pid}    # the auditor service is paused`);
    await pause(400);
    stamp("start");
    caption("It never goes out with fewer checks.");
    await point(queue, queue.getByTestId("queue-item").first());
    await pause(2600);
  } finally {
    execSync(`kill -CONT ${pid}`);
  }
  stamp("resumed");
  note("The auditor is back.");
  await term(queue, `$ kill -CONT ${pid}    # the auditor is back`);
  await waiting((async () => {
    for (let i = 0; i < 45; i++) {
      await pause(4000);
      await queue.reload({ waitUntil: "networkidle" });
      if ((await queue.getByTestId("queue-item").count()) === 0) return;
    }
    throw new Error("the queue did not drain");
  })());
  stamp("drained");
  await pause(1400);
  await current.stop();
  await queue.close();
  // Back in the officer's tab: the row polls the API, and has turned to paid on its own
  current = officer;
  await page.bringToFront();
  await term(page, `$ kill -CONT ${pid}    # the auditor is back`);
  mark("return");
  const paid = page.getByTestId("payout-result").last().filter({ hasText: "Paid" });
  await waiting(paid.waitFor({ timeout: 60_000 }));
  mark("paid");
  note("The queued payout went through on the retry.");
  await point(page, paid);
  await pause(2800);
}

// The immune loop's own command on the immune demo's report, in which the red team's attacks started to work: it
// anchors the report's hash and raises the posture with the oracle key (Anvil account 4). Its log stays out of evidence/.
const POSTURE = "python -m app.agentwallet.posture apply --report evidence/immune-demo-summary.json";
function raisePosture() {
  const key = toHex(mnemonicToAccount(MNEMONIC, { addressIndex: 4 }).getHdKey().privateKey);
  return execSync(`../.venv/bin/python -m app.agentwallet.posture apply --report ../evidence/immune-demo-summary.json`, {
    cwd: path.join(REPO, "backend"),
    env: { ...process.env, RPC_URL: RPC, VAULT_ADDRESS: VAULT, CHAIN_ID: "31337", POSTURE_ORACLE_KEY: key,
           EVIDENCE_DIR: "/tmp/amanah-posture-evidence" },
  }).toString();
}

async function ch6(page, mark) {
  await goto(page, APP + "/officer");
  mark("start");
  caption("When attacks start to work, the wallet tightens itself.");
  await term(page, `$ ${POSTURE}`);
  await pause(1800);
  console.log(raisePosture().trim());
  await pause(800);
  // The line goes before the banner comes, so it never covers the banner's words
  await term(page, null);
  await page.reload({ waitUntil: "networkidle" });
  await waiting(page.getByTestId("posture-banner").waitFor({ timeout: 30_000 }));
  mark("raised");
  await point(page, page.getByTestId("posture-banner"), { scroll: false });
  await pause(2600);
  await say(page, "Pay household ZKT-H14 this month.");
  const confirm = page.getByTestId("chat-log").getByTestId("plan-card").last().getByRole("button", { name: /^Confirm/ });
  await waiting(confirm.waitFor({ timeout: 120_000 }));
  await point(page, page.getByTestId("chat-log").getByTestId("plan-card").last());
  await pause(1200);
  await press(page, confirm);
  const waits = page.getByTestId("payout-result").last().filter({ hasText: "Waiting for a Trustee" });
  await waiting(waits.waitFor({ timeout: 180_000 }));
  mark("waiting");
  caption("Now every payout needs a person.");
  await point(page, waits);
  await pause(3200);
  await setRole(page, "trustee");
  await goto(page, APP + "/trustee");
  mark("trustee");
  caption("The trustee checks the summary against exactly what they sign.");
  const pending = page.getByTestId("pending-payout").first();
  await point(page, pending.getByTestId("summary-text"));
  await pause(2400);
  await point(page, pending.getByTestId("field-beneficiary"));
  await pause(1600);
  await point(page, pending.getByTestId("field-amount"));
  await pause(1600);
  await point(page, pending.getByTestId("checks-ok"));
  await pause(2200);
  // The cut ends here when Hafiz's MetaMask clip follows; without it, the local signature below is kept
  mark("sign-click");
  await press(page, pending.getByRole("button", { name: "Sign with local trustee key" }));
  await waiting(page.getByTestId("sign-result").waitFor({ timeout: 60_000 }));
  mark("signed");
  await point(page, page.getByTestId("sign-result").first());
  await pause(3600);
}

async function ch7a(page, mark) {
  await goto(page, APP + "/redteam");
  mark("start");
  caption("44 attacks, live models, a protocol published before the run.");
  await pause(3600);
  await point(page, page.getByRole("region", { name: "Results by set-up" }));
  caption("One model alone: 3 of 40. Through Amanah: 0 of 40 moved funds.");
  await pause(4600);
  await point(page, page.getByTestId("redteam-row").first());
  await pause(3200);
}

async function ch7b(page, mark) {
  const verify = fs.readFileSync(path.join(__dirname, "verify-output.txt"), "utf8").trimEnd().split("\n");
  await setCard(page, card(`<div class="wrap" style="padding:60px 110px;justify-content:flex-start">
      <div class="kicker">Re-checked from the chain alone · Base Sepolia</div><pre id="t"></pre></div>`,
    `pre{font-family:'JetBrains Mono',monospace;font-size:23px;line-height:1.55;color:#DCE4F7;background:#13285C;
     border-radius:18px;padding:26px 34px;white-space:pre-wrap;word-break:break-all;margin:24px 0 0}`));
  mark("start");
  caption("Anyone can re-check any payout from the chain alone.");
  for (const [i, line] of verify.entries()) {
    await page.evaluate((l) => { document.getElementById("t").textContent += l + "\n"; }, line);
    await pause(i === 0 ? 1100 : 330);
  }
  mark("verified");
  await pause(2000);
  // The explorer's advertising is blocked and its empty row hidden: the video shows the transaction, not an ad.
  // Its loading screen is skipped: the cut goes straight from the terminal to the loaded page.
  stamp("skip");
  await page.context().route(/servedbyadbutler\.com|adx\.ws|marketing-banners/, (route) => route.abort());
  await page.goto(`https://base-sepolia.blockscout.com/tx/${PROOF_TX}`, { waitUntil: "domcontentloaded", timeout: 60_000 });
  await current.cast.restart();
  // Blockscout keeps polling, so the page is ready when the transaction's status shows, not at network idle
  await page.getByText("Success", { exact: true }).first().waitFor({ timeout: 45_000 });
  await pause(1500);
  await page.evaluate(() => {
    const label = [...document.querySelectorAll("div, span")].find((e) => e.childElementCount === 0 && e.textContent.trim() === "Sponsored");
    let item = label;
    while (item && item.parentElement && item.parentElement.childElementCount < 10) item = item.parentElement;
    if (item && item.parentElement) {
      item.style.display = "none";
      if (item.nextElementSibling) item.nextElementSibling.style.display = "none";
    }
  });
  await pause(400);
  stamp("resume");
  mark("blockscout");
  await point(page, page.getByText("Success", { exact: true }).first(), { scroll: false });
  await pause(1800);
  await point(page, page.getByText("AmanahVault").first(), { scroll: false });
  await pause(1800);
  await point(page, page.getByText("Tokens transferred", { exact: true }).first(), { scroll: false });
  await pause(2400);
}

async function ch8(page, mark) {
  const p = FACTS.portability;
  const a = `No model from outside China: Kimi K3 plans, Qwen audits. ${p.domestic.checks_passed} of ${p.domestic.checks} checks.`;
  const b = `The unchanged contract on FISCO BCOS 3.17.1: ${p.fisco.checks_passed} of ${p.fisco.checks} checks.`;
  await setCard(page, card(`<div class="wrap">
      <div class="kicker">Not tied to one vendor or one chain</div>
      <div class="grid"><div id="a" class="fade tile"><b>${p.domestic.checks_passed} of ${p.domestic.checks}</b>
        <span>checks with no model from outside China: Kimi K3 plans, Qwen audits</span></div>
      <div id="b" class="fade tile"><b>${p.fisco.checks_passed} of ${p.fisco.checks}</b>
        <span>checks for the unchanged contract on FISCO BCOS 3.17.1</span></div></div></div>`,
    `.grid{display:grid;grid-template-columns:1fr 1fr;gap:50px;margin-top:40px}
     .tile{background:#13285C;border-radius:24px;padding:46px 50px}.tile b{display:block;font-size:110px;font-weight:800}
     .tile span{display:block;font-size:34px;line-height:1.4;color:#C9D3EA;margin-top:10px}`));
  mark("start");
  note(a);
  await show(page, ["a"], 4200);
  note(b);
  await show(page, ["b"], 5200);
}

async function ch9(page, mark) {
  await setCard(page, card(`<div class="wrap" style="flex-direction:row;align-items:center;gap:60px">
      <div style="flex:1"><div class="kicker">Try it, check it</div>
      <h1 id="a" class="fade">Try to trick it yourself.</h1>
      <p id="b" class="fade" style="color:#fff;font-weight:700">${DEMO}</p>
      <p id="c" class="fade">github.com/hafizmnazman/amanah-wallet</p>
      <p id="d" class="fade" style="color:#D8A521">Sealed on Base Sepolia</p></div>
      <img src="${png("kancil-wave-key.png")}" style="height:600px"></div>`));
  mark("start");
  caption(`Try to trick it yourself: ${DEMO}`);
  await show(page, ["a", "b"], 1600);
  caption("github.com/hafizmnazman/amanah-wallet");
  await show(page, ["c", "d"], 1600);
  await pause(3000);
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ args: ["--disable-blink-features=AutomationControlled"] });
  const clips = [["1", "two-wallets", CARD_VIEW, ch1], ["2", "the-problem", CARD_VIEW, ch2],
                 ["3", "aid-run", APP_VIEW, ch3], ["4", "attacks", APP_VIEW, ch4], ["5", "fallback", APP_VIEW, ch5],
                 ["6", "trustee", APP_VIEW, ch6], ["7a", "red-team", APP_VIEW, ch7a], ["7b", "verify", CARD_VIEW, ch7b],
                 ["8", "portability", CARD_VIEW, ch8], ["9", "close", CARD_VIEW, ch9]];
  for (const [key, name, view, body] of clips) await clip(browser, key, name, view, body);
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
