// test-editor.mjs — browser regression test for the workout-builder editor ("Load a workout"
// screen + ASSIST/REUSE/MODES side panel). Serves the real static index.html with a small stub
// schema, drives it headless via Playwright, and asserts the editor behaves: key-autocomplete
// narrows to the caret's mode, the three panel tabs are mutually exclusive, clicking a KEY
// inserts it, MODES cards expand with the right detail, and the + skeleton buttons drop valid
// scaffolds (required keys active, optional keys commented). JS-side counterpart to the pytest
// suite. Run:  npm i playwright  (once)  then  node tests/test-editor.mjs
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

// App static dir, resolved relative to this file (repo: tests/ → ../src/ui/web/static). Override
// with RT_STATIC to point at a copy elsewhere (e.g. RT_STATIC=$HOME/rt/web/static).
const STATIC = process.env.RT_STATIC || path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../src/ui/web/static");
const HINTS = {
  workout: { keys: ["name", "description", "tags", "stages"], required: ["name", "stages"] },
  stage: { keys: ["name", "description", "tags", "jobs"], required: ["name", "jobs"] },
  exercise: { keys: ["name", "reps", "work_time_in_seconds", "weight", "percent_1rm", "rpe", "distance_in_meters"], required: ["name"] },
  modes: ["custom_sets", "tabata", "emom", "amrap"],
  job: { byMode: {
    tabata: { keys: ["mode", "name", "description", "tags", "rounds", "rest_time_in_seconds", "work_time_in_seconds", "exercises"], required: ["exercises", "mode", "name"], label: "Tabata", description: "TABATA: Intervalos cortos de alta intensidad, típicamente 20s ON / 10s OFF por varias rondas.", exercise: { keys: ["name", "reps", "weight"], required: ["name", "reps"] } },
    amrap: { keys: ["name", "mode", "description", "tags", "work_time_in_minutes", "work_time_in_seconds", "exercises"], required: ["exercises", "mode", "name"], label: "AMRAP", description: "AMRAP: Tantas rondas/reps como puedas dentro de una ventana de tiempo fija.", exercise: { keys: ["name", "reps", "weight"], required: ["name", "reps"] } },
    custom_sets: { keys: ["name", "mode", "description", "tags", "rounds", "cadence", "tempo", "exercises"], required: ["exercises", "mode", "name", "rounds"], label: "Custom Sets", description: "CUSTOM: Series clásicas con rondas, cadencia y tempo que tú defines.", exercise: { keys: ["name", "reps", "work_time_in_seconds", "weight", "percent_1rm", "rpe", "sets", "intra_set"], required: ["name"] } },
    emom: { keys: ["name", "mode", "rounds", "interval_in_seconds", "exercises"], required: ["exercises", "mode", "name"], label: "EMOM", description: "EMOM: Cada minuto (o intervalo) empiezas un bloque de trabajo; descansas lo que sobre.", exercise: { keys: ["name", "reps", "weight"], required: ["name", "reps"] } },
  } },
};
const json = (res, o) => { res.writeHead(200, { "Content-Type": "application/json" }); res.end(JSON.stringify(o)); };
const srv = http.createServer((req, res) => {
  const p = new URL(req.url, "http://x").pathname;
  if (p === "/api/schema") return json(res, HINTS);
  if (p === "/api/library") return json(res, []);
  if (p === "/api/stats") return json(res, { sessions: 0, total_seconds: 0, by_workout: [], prs: [] });
  if (p === "/sw.js") { res.writeHead(404); return res.end(); }
  if (p === "/") { res.writeHead(200, { "Content-Type": "text/html" }); return res.end(fs.readFileSync(STATIC + "/index.html")); }
  res.writeHead(404); res.end();
});
await new Promise((r) => srv.listen(8138, r));
const BASE = "http://127.0.0.1:8138";
const errors = [];
const browser = await chromium.launch({ headless: true });
const page = await browser.newContext({ viewport: { width: 1280, height: 900 } }).then((c) => c.newPage());
page.on("pageerror", (e) => errors.push("pageerror: " + e.message));
function ok(n, c, e = "") { console.log((c ? "ok  : " : "FAIL: ") + n + (e ? " -> " + e : "")); if (!c) errors.push(n + " " + e); }
const setEditor = (val, pos) => page.evaluate((a) => { const ta = document.querySelector("[data-paste]"); ta.value = a[0]; ta.setSelectionRange(a[1], a[1]); ta.dispatchEvent(new Event("input", { bubbles: true })); }, [val, pos == null ? val.length : pos]);
const editorVal = () => page.evaluate(() => document.querySelector("[data-paste]").value);
const acText = () => page.evaluate(() => document.getElementById("ac").textContent);

await page.goto(BASE, { waitUntil: "networkidle" });
await page.waitForSelector(".actions");
await page.click('[data-go="load"]');
await page.waitForSelector("[data-paste]");
await page.waitForTimeout(300);

// ── three-tab side panel: ASSIST (default) / REUSE / MODES, mutually exclusive in one box
ok("default panel = ASSIST (skeleton visible)", (await acText()).includes("＋ Workout"), "");
ok("ASSIST tab pressed by default", (await page.getAttribute('[data-panel="assist"]', "aria-pressed")) === "true", "");
await page.click('[data-panel="reuse"]');
await page.waitForTimeout(40);
ok("REUSE tab switches + is exclusive with ASSIST", (await page.getAttribute('[data-panel="reuse"]', "aria-pressed")) === "true" && (await page.getAttribute('[data-panel="assist"]', "aria-pressed")) === "false", "");
ok("REUSE empty-state when no library", (await acText()).toLowerCase().includes("nothing stored") || (await acText()).toLowerCase().includes("nada guardado"), await acText());
await page.click('[data-panel="assist"]'); // back to ASSIST for the key/skeleton tests below
await page.waitForTimeout(40);

// ── key autocomplete (context + mode narrowing)
const DOC = ["name: My Workout", "stages:", "  - name: WU", "    jobs:", "      - name: Warm-up", "        mode: tabata", "        r", "        exercises:", "          - name: Jax", "            w", ""].join("\n");
await setEditor(DOC, DOC.indexOf("        mode: tabata\n        r") + "        mode: tabata\n        r".length);
let ac = await acText();
ok("job(tabata): narrowed keys", ac.includes("rounds") && ac.includes("rest_time_in_seconds") && !ac.includes("work_time_in_minutes"), "");
await setEditor(DOC, DOC.indexOf("          - name: Jax\n            w") + "          - name: Jax\n            w".length);
ac = await acText();
// tabata exercises take only name/reps/weight — narrowing must hide work_time_in_seconds
// (which IS in the global union and also matches the "w" prefix, so its absence proves narrowing)
ok("exercise(tabata): narrowed — weight yes, work_time_in_seconds no", /KEYS · EXERCISE/i.test(ac) && ac.includes("weight") && !ac.includes("work_time_in_seconds"), ac);

// custom_sets exercises DO allow work_time_in_seconds + percent_1rm — the same caret/prefix, different mode
const DOCC = ["name: W", "stages:", "  - name: S", "    jobs:", "      - name: J", "        mode: custom_sets", "        exercises:", "          - name: Squat", "            w", ""].join("\n");
await setEditor(DOCC, DOCC.indexOf("            w") + "            w".length);
ac = await acText();
ok("exercise(custom_sets): offers work_time_in_seconds (mode-specific)", /KEYS · EXERCISE/i.test(ac) && ac.includes("work_time_in_seconds") && ac.includes("weight"), ac);

// ── NEW skeleton section renders
await setEditor("", 0);
ok("NEW section shows skeleton buttons", (await acText()).includes("＋ Workout") && (await acText()).includes("＋ Job · tabata"), "");

// ── skeleton: ＋Job·custom_sets into empty editor → full valid scaffold with required keys
await setEditor("", 0);
await page.click('[data-skel="job:custom_sets"]');
let v = await editorVal();
ok("＋Job(custom_sets)/empty → scaffold: required filled, optionals blank, exercise reps filled", /^name:/m.test(v) && /^stages:/m.test(v) && /\n        rounds: 3/.test(v) && /\n        tempo:\n/.test(v) && !/# tempo/.test(v) && /\n            reps: 10/.test(v), JSON.stringify(v));

// ── blank = "not defined": stripBlankKeys drops empty scalars, keeps structural keys + filled values
const stripped = await page.evaluate(() => stripBlankKeys([
  "name: W", "stages:", "  - name: S", "    jobs:", "      - name: J", "        mode: tabata",
  "        rounds: 8", "        rest_time_in_seconds:", "        tags:", "        exercises:",
  "          - name: x", "            reps: 10", "            weight:",
].join("\n")));
ok("stripBlankKeys keeps filled values + structural keys", /rounds: 8/.test(stripped) && /reps: 10/.test(stripped) && /^stages:/m.test(stripped) && /jobs:/.test(stripped) && /exercises:/.test(stripped), JSON.stringify(stripped));
ok("stripBlankKeys drops empty scalars (rest_time/tags/weight)", !/rest_time_in_seconds/.test(stripped) && !/tags:/.test(stripped) && !/weight:/.test(stripped), JSON.stringify(stripped));

// ── regression: ＋Workout (empty stages:) then ＋Job must NOT duplicate the stages: key
await setEditor("", 0);
await page.click('[data-skel="workout"]');
await page.click('[data-skel="job:tabata"]');
v = await editorVal();
ok("＋Workout then ＋Job → single stages: (no dup)", (v.match(/^stages:/mg) || []).length === 1 && /mode: tabata/.test(v) && /\n {6}- name: New job/.test(v), JSON.stringify(v));

// ── smart insert: ＋Stage into a doc that has stages: but NO name (the user's case)
await setEditor("stages:\n  - name: A\n    jobs:\n      - name: J\n        mode: tabata\n        exercises:\n          - name: x\n            reps: 1\n");
await page.click('[data-skel="stage"]');
v = await editorVal();
ok("＋Stage into no-name doc → prepends name (user case)", /^name: /m.test(v) && (v.match(/^  - name:/mg) || []).length === 2, JSON.stringify(v.split("\n").slice(0,2)));

// ── clicking a KEY still inserts
await setEditor(DOC, DOC.indexOf("        mode: tabata\n        r") + "        mode: tabata\n        r".length);
await page.waitForTimeout(40);
await page.click('[data-key="rounds"]');
ok("clicking KEY 'rounds' inserts", /\n        rounds: /.test(await editorVal()), "");

// ── MODES reference helper: tab shows expandable cards with purpose + required/uses; ＋ inserts a valid skeleton
await setEditor("", 0);
await page.click('[data-panel="modes"]');
await page.waitForTimeout(60);
let mtxt = await acText();
ok("MODES tab → cards with labels + purpose", /MODES · 4/.test(mtxt) && /Tabata/.test(mtxt) && /AMRAP/.test(mtxt) && /Intervalos cortos/.test(mtxt), JSON.stringify(mtxt.slice(0, 120)));
ok("MODES collapsed → no detail yet", !/Requiere/.test(mtxt), "");
ok("MODES on → ASSIST tab switched off (exclusive)", (await page.getAttribute('[data-panel="assist"]', "aria-pressed")) === "false" && (await page.getAttribute('[data-panel="modes"]', "aria-pressed")) === "true", "");
// expand the Tabata card
await page.click('[data-modeexp="tabata"]');
await page.waitForTimeout(60);
mtxt = await acText();
ok("MODES card expands → shows required/uses detail", /Requires|Requiere/.test(mtxt) && /Uses|Usa/.test(mtxt) && /rest_time_in_seconds/.test(mtxt), JSON.stringify(mtxt.slice(0, 260)));
// the card now also carries a per-mode EXERCISE block: tabata exercises need reps and can add weight
// (neither key exists at the tabata job level, so their presence proves the exercise block rendered)
ok("MODES card → EXERCISE block (tabata needs reps, uses weight)", /Each exercise|Cada ejercicio/i.test(mtxt) && mtxt.includes("reps") && mtxt.includes("weight"), JSON.stringify(mtxt.slice(0, 400)));
// ＋ Insert from the expanded card drops a valid skeleton (S.panel="modes" persists across setEditor→refreshAC)
await setEditor("", 0);
await page.waitForTimeout(40);
ok("card still expanded after clearing editor", (await acText()).includes("rest_time_in_seconds"), "");
await page.click('[data-skel="job:tabata"]');
v = await editorVal();
ok("MODES ＋Insert(tabata) → scaffold: optionals blank, reps filled, rounds blank (not filled)", /^name:/m.test(v) && /mode: tabata/.test(v) && /\n        rest_time_in_seconds:\n/.test(v) && !/# rest_time/.test(v) && /\n            reps: 10/.test(v) && /\n        rounds:\n/.test(v) && !/\n        rounds: \d/.test(v), JSON.stringify(v));

await browser.close(); srv.close();
console.log("\n=== errors: " + errors.length + " ===");
errors.forEach((e) => console.log(" • " + e));
process.exit(errors.length ? 1 : 0);
