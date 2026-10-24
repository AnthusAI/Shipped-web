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
assert.deepStrictEqual(plain(leaders.map((entry) => entry.id)), ["fixture-concept-one", "fixture-story-one", "fixture-change-one"]);
const concepts = script.entriesInGroup(entries, "concepts");
["top", "new", "controversial"].forEach((sortName) => assert.strictEqual(script.sortEntries(concepts, sortName)[0].id, "fixture-concept-one", sortName));

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
const overrideOnly = { id: "o", group: "concepts", title: "T", state: "in_steering", votes: { up: 5, down: 0, net: 5 }, communityResult: null, decision: null, override: { result: "approved", reason: "Well sourced.", by: "Ryan", at: "2026-10-24T10:00:00Z" } };
assert.ok(script.decisionLineHtml(overrideOnly).includes("Approved") && script.decisionLineHtml(overrideOnly).includes("Well sourced.") && script.decisionLineHtml(overrideOnly).includes("Ryan"));
assert.ok(script.excludedHtml(overridden).includes("Excluded 18 votes"));
assert.strictEqual(script.excludedHtml(entries.find((entry) => entry.state === "draft")), "");
assert.deepStrictEqual(plain(script.editorDecisions(entries).map((entry) => entry.id)), ["fixture-change-two"]);
assert.ok(script.votingEnabled({ papyrusReader: { voteSubjects: ["item", "proposal"] } }));
assert.ok(script.votingEnabled({ papyrusReader: { proposalVoting: true } }));
assert.ok(!script.votingEnabled({ papyrusReader: { voteSubjects: ["item"] } }));
assert.ok(!script.votingEnabled({}));
const trend = entries.find((entry) => entry.id === "fixture-story-three");
const figure = script.figureHtml(trend);
assert.ok(figure.startsWith('<figure class="proposals-figure">'));
assert.ok(figure.includes("Cluster A") && figure.includes("Cluster B") && figure.includes("Source: Shipped knowledge snapshot"));
assert.ok(figure.includes('stroke-dasharray="7 4"'));
assert.ok(figure.includes("Cluster A from 1 signals to 9 signals; Cluster B from 5 signals to 2 signals"));
assert.ok(figure.includes("21 Sep 2026") && figure.includes("19 Oct 2026"));
assert.ok(!/NaN/.test(figure));
assert.strictEqual(script.figureHtml(entries.find((entry) => entry.state === "draft")), "");
assert.strictEqual(script.figureHtml({ evidence: { figure: { type: "bar", x: ["a", "b"], series: [{ values: [1, 2] }] } } }), "");
assert.strictEqual(script.figureHtml({ evidence: { figure: { type: "line", x: ["a", "b"], series: [{ values: [1] }] } } }), "");
assert.ok(!script.figureHtml({ evidence: { figure: { type: "line", title: "<script>x</script>", x: ["2026-10-05", "2026-10-12"], series: [{ label: "<b>", values: [1, 2] }] } } }).includes("<script>"));
assert.ok(script.queueHtml(entries, { group: "stories", sort: "top" }, { enabled: false, mine: {}, baseline: {}, busy: false }, 0).includes("proposals-figure"));

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
const conceptHtml = script.queueHtml(entries, { group: "concepts", sort: "top" }, voteState, Date.parse("2026-10-22T12:00:00Z"));
assert.ok(conceptHtml.includes("proposals-mark-pinned") && conceptHtml.includes("Pinned"));
const changeHtml = script.queueHtml(entries, { group: "map_changes", sort: "top" }, voteState, Date.parse("2026-10-22T12:00:00Z"));
assert.ok(changeHtml.includes("Excluded 18 votes from accounts under 24 h."));

const hostile = [{ id: "x", group: "stories", title: "<img src=x onerror=alert(1)>", state: "draft", votes: { up: 0, down: 0, net: 0 } }];
assert.ok(!script.queueHtml(hostile, { group: "stories", sort: "top" }, voteState, 0).includes("<img"));

const untouchedMount = { getAttribute: () => "queue", innerHTML: "PLACEHOLDER" };
const missingScope = {
  document: { querySelectorAll: () => [untouchedMount] },
  fetch: () => Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) }),
};
const emptyScope = Object.assign({}, missingScope, { fetch: () => Promise.resolve({ ok: true, json: () => Promise.resolve([]) }) });
const requestedUrls = [];
const signedInScope = {
  papyrusReader: { api: "/api/reader", proposalVoting: true },
  fetch: (url) => { requestedUrls.push(url); return Promise.resolve({ ok: true, json: () => Promise.resolve({ subjectVotes: { "proposal:fixture-story-one": 1, "proposal:fixture-concept-one": -1, "proposal:fixture-change-one": 7 } }) }); },
};
const signedInVoteState = { enabled: true, mine: {}, baseline: {}, busy: false };
const disabledVoteState = { enabled: false, mine: {}, baseline: {}, busy: false };
const signedOutVoteState = { enabled: true, mine: {}, baseline: {}, busy: false };
const signedOutScope = Object.assign({}, signedInScope, { fetch: () => Promise.resolve({ ok: false, status: 401, json: () => Promise.resolve({}) }) });
Promise.all([
  script.start(missingScope),
  script.start(emptyScope),
  script.loadOwnProposalVotes(signedInScope, entries, signedInVoteState),
  script.loadOwnProposalVotes(signedInScope, entries, disabledVoteState),
  script.loadOwnProposalVotes(signedOutScope, entries, signedOutVoteState),
]).then(() => {
  assert.strictEqual(untouchedMount.innerHTML, "PLACEHOLDER");
  assert.deepStrictEqual(plain(signedInVoteState.mine), { "fixture-story-one": 1, "fixture-concept-one": -1 });
  assert.strictEqual(requestedUrls.length, 1);
  assert.ok(requestedUrls[0].startsWith("/api/reader/me?subjects=proposal%3Afixture-"));
  assert.deepStrictEqual(plain(disabledVoteState.mine), {});
  assert.deepStrictEqual(plain(signedOutVoteState.mine), {});
  console.log("proposals script checks passed");
});
