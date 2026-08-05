// Test admin.html against a stub of the admin API: the admin gate, user listing, library
// load, send-to-library (payload + refresh), and the non-admin 403 path.
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const STATIC = process.env.RT_STATIC || path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../src/ui/web/static");
let ME = { email: "boss@x.com", access: true, is_admin: true };
let LIB = [{ id: "murph", file: "murph.yaml", name: "Murph", valid: true, n_stages: 1, n_jobs: 3 }];
const USERS = [{ key: "k1", email: "tester@example.com", n_workouts: 2 }, { key: "k2", email: null, n_workouts: 1 }];
let lastPush = null, lastLibEmail = null, pushFails = false;
const json = (res, o, code = 200) => { res.writeHead(code, { "Content-Type": "application/json" }); res.end(JSON.stringify(o)); };
const srv = http.createServer((req, res) => {
  const u = new URL(req.url, "http://x");
  const p = u.pathname;
  if (p === "/api/me") return json(res, ME);
  if (p === "/api/admin/users") return json(res, USERS);
  if (p === "/api/admin/library") { lastLibEmail = u.searchParams.get("email"); return json(res, LIB); }
  if (p === "/api/admin/push") { let b = ""; req.on("data", (c) => (b += c)); req.on("end", () => {
      lastPush = JSON.parse(b || "{}");
      if (pushFails) return json(res, { detail: "invalid workout — line 3: bad" }, 422);
      LIB = LIB.concat([{ id: "new", file: (lastPush.filename || "workout.yaml"), name: "New", valid: true, n_stages: 1, n_jobs: 1 }]);
      return json(res, { email: lastPush.email, file: lastPush.filename || "workout.yaml", replaced: false, workout: { name: "Sent WOD", n_stages: 1, n_jobs: 2 } });
    }); return; }
  if (p === "/" || p === "/admin") { res.writeHead(200, { "Content-Type": "text/html" }); return res.end(fs.readFileSync(STATIC + "/admin.html")); }
  res.writeHead(404); res.end();
});
await new Promise((r) => srv.listen(8144, r));

const errors = [];
const ok = (n, c, e = "") => { console.log((c ? "ok  : " : "FAIL: ") + n + (e ? " -> " + e : "")); if (!c) errors.push(n + " " + e); };
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1100, height: 900 } });
await ctx.route("**/fonts.g*/**", (r) => r.abort());
const page = await ctx.newPage();
page.on("pageerror", (e) => errors.push("pageerror: " + e.message));

// ── admin path
await page.goto("http://127.0.0.1:8144/admin", { waitUntil: "networkidle" });
await page.waitForTimeout(150);
ok("admin → console visible, gate hidden", await page.isHidden("#gate") && await page.isVisible("#console"), "");
ok("who shows admin email", (await page.textContent("#who")).includes("boss@x.com"), await page.textContent("#who"));
ok("users datalist populated (known email only)", (await page.$$("#users option")).length === 1, String((await page.$$("#users option")).length));
ok("users hint mentions unlabelled", /not yet labelled/.test(await page.textContent("#usersHint")), await page.textContent("#usersHint"));

// load a user's library
await page.fill("#email", "tester@example.com");
await page.click("#btnLoad");
await page.waitForTimeout(120);
ok("library loads for typed email", lastLibEmail === "tester@example.com" && /murph\.yaml/.test(await page.textContent("#lib")), await page.textContent("#lib"));

// send a workout
await page.fill("#yaml", "name: Sent WOD\nstages:\n  - name: S\n    jobs: []\n");
await page.fill("#fname", "sent");
await page.click("#btnSend");
await page.waitForTimeout(150);
ok("push sends email + text + filename", lastPush && lastPush.email === "tester@example.com" && /Sent WOD/.test(lastPush.text) && lastPush.filename === "sent", JSON.stringify(lastPush));
ok("success message shown", /\bok\b/.test(await page.getAttribute("#msg", "class")) && /Sent WOD/.test(await page.textContent("#msg")), await page.textContent("#msg"));
ok("library refreshed after push (new file present)", /sent/.test(await page.textContent("#lib")), await page.textContent("#lib"));

// push error surfaces the server message
pushFails = true;
await page.click("#btnSend");
await page.waitForTimeout(150);
ok("push 422 → error message shown", /\berr\b/.test(await page.getAttribute("#msg", "class")) && /line 3/.test(await page.textContent("#msg")), await page.textContent("#msg"));

// ── non-admin 403 path
ME = { email: "nobody@x.com", access: true, is_admin: false };
await page.goto("http://127.0.0.1:8144/admin", { waitUntil: "networkidle" });
await page.waitForTimeout(120);
ok("non-admin → gate shows 403, console hidden", await page.isVisible("#gate") && await page.isHidden("#console") && /admins only/.test(await page.textContent("#gate")), await page.textContent("#gate"));

await browser.close(); srv.close();
console.log("\n=== errors: " + errors.length + " ===");
errors.forEach((e) => console.log(" • " + e));
process.exit(errors.length ? 1 : 0);
