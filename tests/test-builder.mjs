// Test the standalone public builder (builder.html): schema skeletons, client-side validation
// (using a locally-served js-yaml so it doesn't depend on the CDN), and download.
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const STATIC = process.env.RT_STATIC || path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../src/ui/web/static");
// deterministic js-yaml if vendored next to this test; otherwise the page loads it from the CDN
let JSYAML = null;
try { JSYAML = fs.readFileSync(path.resolve(path.dirname(fileURLToPath(import.meta.url)), "js-yaml.umd.min.js"), "utf8"); } catch (e) {}
const srv = http.createServer((req, res) => {
  const p = new URL(req.url, "http://x").pathname;
  if (p === "/") { res.writeHead(200, { "Content-Type": "text/html" }); return res.end(fs.readFileSync(STATIC + "/builder.html")); }
  res.writeHead(404); res.end();
});
await new Promise((r) => srv.listen(8142, r));

const errors = [];
const ok = (n, c, e = "") => { console.log((c ? "ok  : " : "FAIL: ") + n + (e ? " -> " + e : "")); if (!c) errors.push(n + " " + e); };
const browser = await chromium.launch({ headless: true });
const page = await browser.newContext({ viewport: { width: 1280, height: 900 }, acceptDownloads: true }).then((c) => c.newPage());
page.on("pageerror", (e) => errors.push("pageerror: " + e.message));
// serve js-yaml locally (deterministic) and skip Google Fonts
if (JSYAML) await page.route("**/js-yaml*", (r) => r.fulfill({ contentType: "application/javascript", body: JSYAML }));
await page.route("**/fonts.googleapis.com/**", (r) => r.abort());
await page.route("**/fonts.gstatic.com/**", (r) => r.abort());
await page.goto("http://127.0.0.1:8142", { waitUntil: "networkidle" });

const val = () => page.evaluate(() => document.getElementById("ed").value);
const setEd = (v) => page.evaluate((t) => { document.getElementById("ed").value = t; }, v);
const msg = () => page.evaluate(() => ({ text: document.getElementById("msg").textContent, cls: document.getElementById("msg").className }));

ok("js-yaml loaded", await page.evaluate(() => !!window.jsyaml), "");
ok("mode buttons rendered (workout + stage + 9 jobs)", (await page.$$("[data-skel]")).length === 11, String((await page.$$("[data-skel]")).length));

// ── skeleton insert: tabata → required active, optionals blank, exercise reps filled
await page.click('[data-skel="job:tabata"]');
let v = await val();
ok("insert tabata → mode + blank optional + reps filled", /mode: tabata/.test(v) && /\n {8}rest_time_in_seconds:\n/.test(v) && /\n {12}reps: 10/.test(v), JSON.stringify(v.slice(0, 60)));

// ── compose Workout → Job(custom_sets), then validate OK (custom_sets fills required rounds)
await setEd("");
await page.click('[data-skel="workout"]');
await page.click('[data-skel="job:custom_sets"]');
v = await val();
ok("compose → single stages:, custom_sets rounds filled (no dup stages)", /^name:/m.test(v) && (v.match(/^stages:/mg) || []).length === 1 && /\n {8}rounds: 3/.test(v), JSON.stringify(v));
await page.click("#btnValidate");
let m = await msg();
ok("check valid workout → ok", /\bok\b/.test(m.cls) && /Looks good/.test(m.text), JSON.stringify(m));

// ── invalid: tabata job with no exercises → error names it
await setEd("name: W\nstages:\n  - name: S\n    jobs:\n      - name: J\n        mode: tabata\n");
await page.click("#btnValidate");
m = await msg();
ok("check missing exercises → err", /\berr\b/.test(m.cls) && /exercises/.test(m.text), JSON.stringify(m));

// ── invalid: emom without rounds (req_skel via if/then/else) → error names rounds
await setEd("name: W\nstages:\n  - name: S\n    jobs:\n      - name: J\n        mode: emom\n        exercises:\n          - name: x\n            reps: 5\n");
await page.click("#btnValidate");
m = await msg();
ok("check emom missing rounds → err names rounds", /\berr\b/.test(m.cls) && /rounds/.test(m.text), JSON.stringify(m));

// ── unknown mode → error
await setEd("name: W\nstages:\n  - name: S\n    jobs:\n      - name: J\n        mode: bogus\n        exercises:\n          - name: x\n");
await page.click("#btnValidate");
m = await msg();
ok("check unknown mode → err", /\berr\b/.test(m.cls) && /unknown mode/.test(m.text), JSON.stringify(m));

// ── download: filename from name, blank optional lines stripped from the file
await setEd('name: My Test WOD\ndescription: ""\nstages:\n  - name: S\n    jobs:\n      - name: J\n        mode: tabata\n        rounds: 8\n        tags:\n        exercises:\n          - name: Burpees\n            reps: 10\n');
const [dl] = await Promise.all([page.waitForEvent("download"), page.click("#btnDl")]);
const fn = dl.suggestedFilename();
const body = fs.readFileSync(await dl.path(), "utf8");
ok("download filename from workout name", fn === "My_Test_WOD.yaml", fn);
ok("download strips blank optional lines (no 'tags:')", /rounds: 8/.test(body) && !/^\s*tags:\s*$/m.test(body) && body.endsWith("\n"), JSON.stringify(body));

// ── ES toggle relabels the buttons
await page.click('[data-lang="es"]');
ok("ES toggle relabels download button", /DESCARGAR/.test(await page.textContent("#btnDl")), await page.textContent("#btnDl"));

await browser.close(); srv.close();
console.log("\n=== errors: " + errors.length + " ===");
errors.forEach((e) => console.log(" • " + e));
process.exit(errors.length ? 1 : 0);
