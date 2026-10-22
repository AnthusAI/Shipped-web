const assert = require("assert");
const path = require("path");
const fs = require("fs");
const vm = require("vm");
const scriptSource = fs.readFileSync(path.join(__dirname, "..", "web", "assets", "shipped-proposals.js"), "utf8");
const loadedModule = { exports: {} };
vm.runInNewContext(scriptSource, { module: loadedModule, Promise, Date, Math, Number, String, Array, JSON, isFinite, Object });
const script = loadedModule.exports;
const plain = (value) => JSON.parse(JSON.stringify(value));
const entries = script.normaliseEntries(JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "proposals", "_data", "proposals", "index.json"), "utf8")));

assert.strictEqual(entries.length, 9);
assert.deepStrictEqual(plain(script.normaliseEntries({ message: "nope" })), []);
assert.deepStrictEqual(plain(script.normaliseEntries(null)), []);

const stories = script.entriesInGroup(entries, "stories");
assert.deepStrictEqual(plain(script.sortEntries(stories, "top").map((entry) => entry.votes.net)), [19, 12, 1.4, 1]);
assert.strictEqual(script.sortEntries(stories, "new")[0].id, "fixture-story-two");
assert.strictEqual(script.sortEntries(stories, "controversial")[0].id, "fixture-story-three");

const leaders = script.steeringLeaders(entries, 3);
assert.deepStrictEqual(plain(leaders.map((entry) => entry.id)), ["fixture-story-one", "fixture-concept-one", "fixture-change-one"]);

const touching = entries.filter((entry) => script.touchesConcept(entry, "Open TTS", "open-tts")).map((entry) => entry.id);
assert.deepStrictEqual(plain(touching.sort()), ["fixture-change-two", "fixture-concept-one", "fixture-story-two"]);
assert.ok(script.touchesConcept(entries.find((entry) => entry.id === "fixture-concept-two"), "Decision models", "decision-models"));

assert.strictEqual(script.formatNet(1.4), "1.4");
assert.strictEqual(script.formatNet(12), "12");
assert.strictEqual(script.formatNet(-3), "−3");
assert.strictEqual(script.formatNet(1.449), "1.4");

const overridden = entries.find((entry) => entry.state === "overridden_by_editor");
const line = script.decisionLineHtml(overridden);
assert.ok(line.includes("Approved by readers") && line.includes("Declined") && line.includes("Coordinated votes from new accounts."));
assert.strictEqual(script.decisionLineHtml(entries.find((entry) => entry.state === "draft")), "");

["draft", "in_steering", "editor_review", "approved", "declined", "overridden_by_editor"].forEach((state) => {
  const mark = script.stateMark(state);
  assert.ok(mark.includes("<svg"), state);
  assert.ok(/[A-Za-z]{5}/.test(mark.replace(/<[^>]*>/g, "")), state);
});

const voteState = { enabled: false, mine: {}, baseline: {}, busy: false };
const html = script.queueHtml(entries, { group: "stories", sort: "top" }, voteState, Date.parse("2026-10-22T12:00:00Z"));
assert.ok(html.includes("Proposal voting opens soon"));
assert.ok(html.includes("disabled"));
assert.ok(!html.includes("[n]"));

const hostile = [{ id: "x", group: "stories", title: "<img src=x onerror=alert(1)>", state: "draft", votes: { up: 0, down: 0, net: 0 } }];
assert.ok(!script.queueHtml(hostile, { group: "stories", sort: "top" }, voteState, 0).includes("<img"));

const untouchedMount = { getAttribute: () => "queue", innerHTML: "PLACEHOLDER" };
const missingScope = {
  document: { querySelectorAll: () => [untouchedMount] },
  fetch: () => Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) }),
};
const emptyScope = Object.assign({}, missingScope, { fetch: () => Promise.resolve({ ok: true, json: () => Promise.resolve([]) }) });
Promise.all([script.start(missingScope), script.start(emptyScope)]).then(() => {
  assert.strictEqual(untouchedMount.innerHTML, "PLACEHOLDER");
  console.log("proposals script checks passed");
});
