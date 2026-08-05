// Fake-clock test for the timestamp-based player clock. Overrides Date.now() so we can
// step time deterministically and assert: no drift, auto-advance at the boundary, catch-up
// after backgrounding, and pause/resume excluding paused time. render() is stubbed to a
// no-op so we test the timing state machine in isolation (S.si / left / up / elapsed / paused).
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const STATIC = process.env.RT_STATIC || path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../src/ui/web/static");
const seg = (kind, dur, label, ri, tr) => ({
  type: "seg", stage_index: 1, job_index: 1, stage_name: "S", jobs_in_stage: 1, job: { name: "J" },
  seg: { kind, duration_seconds: dur, label, round_index: ri, total_rounds: tr, items: [] },
});
const TIMELINE = [ seg("work", 20, "Work 1", 1, 2), seg("rest", 10, "Rest", 1, 2), seg("work", 20, "Work 2", 2, 2) ];
const WK = { name: "Test", description: "", n_stages: 1, n_jobs: 1, stages: [{ name: "S", description: "", jobs: [{ name: "J", mode: "tabata" }] }] };
const json = (res, o) => { res.writeHead(200, { "Content-Type": "application/json" }); res.end(JSON.stringify(o)); };
const srv = http.createServer((req, res) => {
  const p = new URL(req.url, "http://x").pathname;
  if (p === "/api/schema") return json(res, { modes: [], job: { byMode: {} } });
  if (p === "/api/library") return json(res, []);
  if (p === "/api/stats") return json(res, { sessions: 0, total_seconds: 0, by_workout: [], prs: [] });
  if (/^\/api\/workouts\/.+\/timeline/.test(p)) return json(res, { workout: WK, timeline: TIMELINE, driven: true });
  if (p === "/api/runs") { let b = ""; req.on("data", (c) => (b += c)); req.on("end", () => json(res, { saved: "ok" })); return; }
  if (p === "/sw.js") { res.writeHead(404); return res.end(); }
  if (p === "/") { res.writeHead(200, { "Content-Type": "text/html" }); return res.end(fs.readFileSync(STATIC + "/index.html")); }
  res.writeHead(404); res.end();
});
await new Promise((r) => srv.listen(8141, r));

const errors = [];
const ok = (n, c, e = "") => { console.log((c ? "ok  : " : "FAIL: ") + n + (e ? " -> " + e : "")); if (!c) errors.push(n + " " + e); };
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
// pin Date.now() to a controllable value BEFORE any page script runs
await ctx.addInitScript(() => { window.__now = 1_700_000_000_000; Date.now = () => window.__now; });
const page = await ctx.newPage();
page.on("pageerror", (e) => errors.push("pageerror: " + e.message));
await page.goto("http://127.0.0.1:8141", { waitUntil: "networkidle" });
await page.evaluate(() => { window.render = () => { window.__r = (window.__r || 0) + 1; }; });   // isolate timing from DOM

const S = () => page.evaluate(() => ({ si: S.si, left: S.left, up: S.up, elapsed: S.elapsed, paused: S.paused }));
const setNow = (ms) => page.evaluate((m) => { window.__now = m; }, ms);
const tick = () => page.evaluate(() => tick());
const T0 = 1_700_000_000_000;

// ── start the run (fetches timeline, enter(0))
await page.evaluate(async () => { S.wid = "X"; await startRun(true); });
let s = await S();
ok("start → seg 0, 20s, running", s.si === 0 && s.left === 20 && s.paused === false, JSON.stringify(s));

// ── no drift: step 5s then 3s, countdown + elapsed are exact
await setNow(T0 + 5000); await tick(); s = await S();
ok("+5s → left 15, elapsed 5 (no drift)", s.left === 15 && s.elapsed === 5, JSON.stringify(s));
await setNow(T0 + 8000); await tick(); s = await S();
ok("+8s → left 12, elapsed 8", s.left === 12 && s.elapsed === 8, JSON.stringify(s));

// ── auto-advance exactly at the boundary (t=20s → seg 1, the 10s rest)
await setNow(T0 + 20000); await tick(); s = await S();
ok("t=20s → auto-advance to seg 1 (rest 10s), elapsed 20", s.si === 1 && s.left === 10 && s.elapsed === 20, JSON.stringify(s));

// ── background catch-up: jump to t=45s (past the rest's 30s end) → land mid seg 2 with 5s left
await setNow(T0 + 45000); await tick(); s = await S();
ok("t=45s (returned from background) → seg 2, left 5, elapsed 45", s.si === 2 && s.left === 5 && s.elapsed === 45, JSON.stringify(s));

// ── pause/resume excludes paused time — fresh run
await page.evaluate(async () => { window.__now = 1_700_000_000_000; S.wid = "X"; await startRun(true); });
await setNow(T0 + 5000); await tick();                 // 5s in: left 15
await page.evaluate(() => setPaused(true));            // pause at t=5
await setNow(T0 + 15000); await tick();                // 10s pass while paused (tick no-ops)
let sp = await S();
ok("paused 10s → clock frozen (left 15, still paused)", sp.left === 15 && sp.paused === true, JSON.stringify(sp));
await page.evaluate(() => setPaused(false));           // resume at t=15
await setNow(T0 + 20000); await tick();                // 5s after resume
sp = await S();
ok("after resume +5s → left 10, elapsed 10 (paused time excluded)", sp.left === 10 && sp.elapsed === 10, JSON.stringify(sp));

await browser.close(); srv.close();
console.log("\n=== errors: " + errors.length + " ===");
errors.forEach((e) => console.log(" • " + e));
process.exit(errors.length ? 1 : 0);
