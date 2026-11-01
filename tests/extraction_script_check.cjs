const assert = require("assert");
const path = require("path");
const fs = require("fs");
const vm = require("vm");
const scriptSource = fs.readFileSync(path.join(__dirname, "..", "web", "assets", "shipped-extraction.js"), "utf8");
const loadedModule = { exports: {} };
vm.runInNewContext(scriptSource, { module: loadedModule, Promise, Date, Math, Number, String, Array, JSON, Object, isNaN, encodeURIComponent });
const script = loadedModule.exports;
const plain = (value) => JSON.parse(JSON.stringify(value));
const subject = "sub-0123456789abcdef01234567";
const other = "sub-abcdefabcdefabcdefabcdef";

assert.ok(script.validSubject(subject));
assert.ok(!script.validSubject("sub-XYZ"));
assert.ok(!script.validSubject("item-one"));

let remembered = script.remember([], { subject, title: "A tool" });
remembered = script.remember(remembered, { subject: other, title: "Another" });
remembered = script.remember(remembered, { subject, title: "A tool" });
assert.deepStrictEqual(plain(remembered.map((entry) => entry.subject)), [subject, other]);
assert.deepStrictEqual(plain(script.remember(remembered, { subject: "bad" })), plain(remembered));
assert.deepStrictEqual(plain(script.forget(remembered, subject).map((entry) => entry.subject)), [other]);
let many = [];
for (let index = 0; index < 7; index += 1) many = script.remember(many, { subject: "sub-" + String(index).repeat(24), title: "" });
assert.strictEqual(many.length, 5);

const extracted = {
  subject, url: "https://example.com/tool", title: "A <tool>", state: "pending",
  extraction: { state: "extracted", knownReference: true, model: { name: "Quillon 27B", match: { key: "quillon", name: "Quillon 27B", kind: "model" } }, maker: { name: "Quill Labs", match: null }, task: null },
  confirmation: null
};
const extractedHtml = script.recordHtml(extracted);
assert.ok(extractedHtml.includes("A &lt;tool&gt;") && !extractedHtml.includes("<tool>"));
assert.ok(extractedHtml.includes('<span class="entity-chip entity-chip-confirmed"><i>model</i>Quillon 27B</span>'));
assert.ok(extractedHtml.includes("Quill Labs · new to the map"));
assert.ok(extractedHtml.includes('<span class="extraction-none">None found</span>'));
assert.ok(extractedHtml.includes("Is this right?") && extractedHtml.includes("already among the sources the map reads"));
assert.ok(extractedHtml.includes("data-extraction-confirm>Looks right") && extractedHtml.includes("data-extraction-fix"));
assert.ok(extractedHtml.includes('value="Quillon 27B"'));

const pending = Object.assign({}, extracted, { extraction: { state: "pending" } });
const pendingHtml = script.recordHtml(pending);
assert.ok(pendingHtml.includes("Waiting for AI to read this link."));
assert.ok(!pendingHtml.includes("tag-table") && !pendingHtml.includes("Looks right") && !pendingHtml.includes("data-extraction-form"));

const failed = Object.assign({}, extracted, { extraction: { state: "failed", reason: "not_public" } });
const failedHtml = script.recordHtml(failed);
assert.ok(failedHtml.includes("AI couldn’t read this link: the page is not public."));
assert.ok(!failedHtml.includes("Looks right") && failedHtml.includes("data-extraction-fix"));
assert.strictEqual(script.failureText("something_new"), "the page could not be read");

const confirmed = Object.assign({}, extracted, { confirmation: { status: "confirmed", at: "2026-11-01T10:00:00Z", model: extracted.extraction.model, maker: extracted.extraction.maker, task: null } });
const confirmedHtml = script.recordHtml(confirmed);
assert.ok(confirmedHtml.includes("You confirmed this on 1 Nov 2026"));
assert.ok(!confirmedHtml.includes("Looks right") && confirmedHtml.includes("data-extraction-fix"));
const corrected = Object.assign({}, extracted, { confirmation: { status: "corrected", at: "2026-11-01T10:00:00Z", model: { name: "Quillon 30B", match: null }, maker: null, task: { name: "Speech", match: null } } });
const correctedValues = script.shownValues(corrected);
assert.strictEqual(correctedValues.model.name, "Quillon 30B");
assert.strictEqual(correctedValues.maker, null);
assert.ok(script.recordHtml(corrected).includes("You fixed this on 1 Nov 2026") && script.recordHtml(corrected).includes("Looks right"));

assert.deepStrictEqual(plain(script.correctionBody(subject, { model: "  Quillon 30B ", maker: "", task: "x".repeat(200) })), {
  subject, decision: "correct", model: "Quillon 30B", maker: null, task: "x".repeat(120)
});

assert.strictEqual(script.errorText({ status: 409, body: { error: "extraction_not_ready" } }), "AI has not read this link yet. Try again after it has.");
assert.strictEqual(script.errorText({ status: 401, body: {} }), "Sign in again to confirm.");
assert.strictEqual(script.errorText({ status: 429, body: {} }), "Too many answers this hour. Try again later.");
assert.strictEqual(script.errorText(null), "That didn't save. Try again.");

function fakeScope(stored, answers) {
  const storage = { value: JSON.stringify(stored) };
  const calls = [];
  return {
    calls, storage,
    papyrusReader: { api: "/api/reader" },
    localStorage: { getItem: () => storage.value, setItem: (key, value) => { storage.value = value; } },
    fetch: (url, options) => {
      calls.push({ url, options });
      const answer = answers[url] || { status: 404, body: { error: "unknown_submission" } };
      return Promise.resolve({ ok: answer.status < 300, status: answer.status, json: () => Promise.resolve(answer.body) });
    }
  };
}

function fakeSection() {
  const removed = [];
  const container = { innerHTML: "", querySelector: () => null };
  return {
    removed, container,
    classList: { values: new Set(["on-the-map", "is-placeholder"]), remove(name) { this.values.delete(name); } },
    querySelector: (selector) => (selector === "[data-extraction-records]" ? container : null),
    querySelectorAll: (selector) => (selector === ".placeholder-tag" || selector === "[data-extraction-sample]"
      ? [{ parentNode: { removeChild: () => removed.push(selector) } }] : [])
  };
}

(async () => {
  const emptyScope = fakeScope([], {});
  const emptySection = fakeSection();
  assert.deepStrictEqual(plain(await script.load(emptyScope, emptySection)), []);
  assert.strictEqual(emptyScope.calls.length, 0);
  assert.ok(emptySection.classList.values.has("is-placeholder"));

  const scope = fakeScope([{ subject, title: "A tool" }, { subject: other, title: "Gone" }], {
    ["/api/reader/extraction?subject=" + subject]: { status: 200, body: extracted }
  });
  const section = fakeSection();
  const records = await script.load(scope, section);
  assert.strictEqual(records.length, 1);
  assert.strictEqual(scope.calls[0].options.cache, "no-store");
  assert.strictEqual(scope.calls[0].options.credentials, "same-origin");
  assert.ok(!section.classList.values.has("is-placeholder"));
  assert.deepStrictEqual(section.removed, [".placeholder-tag", "[data-extraction-sample]"]);
  assert.ok(section.container.innerHTML.includes("Only you see this."));
  assert.deepStrictEqual(JSON.parse(scope.storage.value).map((entry) => entry.subject), [subject]);

  const signedOut = fakeScope([{ subject, title: "A tool" }], { ["/api/reader/extraction?subject=" + subject]: { status: 401, body: {} } });
  const signedOutSection = fakeSection();
  assert.deepStrictEqual(plain(await script.load(signedOut, signedOutSection)), []);
  assert.ok(signedOutSection.classList.values.has("is-placeholder"));
  assert.deepStrictEqual(JSON.parse(signedOut.storage.value).map((entry) => entry.subject), [subject]);

  console.log("extraction script checks passed");
})().catch((error) => { console.error(error); process.exit(1); });
