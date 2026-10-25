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
assert.ok(script.queueHtml(entries, { group: "stories", sort: "top" }, script.newVoteState(false, 0), 0).includes("proposals-figure"));

["draft", "in_steering", "editor_review", "approved", "declined", "overridden_by_editor"].forEach((state) => {
  const mark = script.stateMark(state);
  assert.ok(mark.includes("<svg"), state);
  assert.ok(/[A-Za-z]{5}/.test(mark.replace(/<[^>]*>/g, "")), state);
});

const voteState = script.newVoteState(false, 0);
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


const storyOne = entries.find((entry) => entry.id === "fixture-story-one");
const generatedMiddle = Date.parse("2026-10-22T12:00:00Z");
const adjustedState = script.newVoteState(true, generatedMiddle);
assert.strictEqual(script.shownNetFor(storyOne, adjustedState), 12);
adjustedState.mine[storyOne.id] = 1;
assert.strictEqual(script.shownNetFor(storyOne, adjustedState), 12);
adjustedState.castAt[storyOne.id] = generatedMiddle + 1000;
assert.strictEqual(script.shownNetFor(storyOne, adjustedState), 13);
adjustedState.castAt[storyOne.id] = generatedMiddle - 1000;
assert.strictEqual(script.shownNetFor(storyOne, adjustedState), 12);
const silentEntry = { id: "silent", group: "stories", title: "Silent", state: "draft", votes: { up: 0, down: 0, net: 0 } };
const silentState = script.newVoteState(true, generatedMiddle);
silentState.mine.silent = -1;
assert.strictEqual(script.shownNetFor(silentEntry, silentState), -1);
silentState.baseline.silent = 4;
assert.strictEqual(script.shownNetFor(silentEntry, silentState), 4);
assert.strictEqual(script.indexGeneratedAt({ generatedAt: "2026-10-22T12:00:00Z", proposals: [] }), generatedMiddle);
assert.strictEqual(script.indexGeneratedAt([]), 0);

const pressedState = script.newVoteState(true, 0);
pressedState.mine["fixture-story-one"] = 1;
pressedState.mine["fixture-story-two"] = -1;
const pressedHtml = script.queueHtml(entries, { group: "stories", sort: "top" }, pressedState, 0);
assert.ok(pressedHtml.includes("You voted up · "));
assert.ok(pressedHtml.includes("You voted down · "));
assert.ok(pressedHtml.includes('data-proposal-undo data-proposal-id="fixture-story-one"'));
assert.strictEqual((pressedHtml.match(/aria-pressed="true"/g) || []).length, 2 + 1 + 1);
assert.ok(!script.queueHtml(entries, { group: "stories", sort: "top" }, script.newVoteState(true, 0), 0).includes("You voted"));

const sendingState = script.newVoteState(true, 0);
sendingState.sending["fixture-story-one"] = true;
const sendingHtml = script.queueHtml(entries, { group: "stories", sort: "top" }, sendingState, 0);
assert.ok(sendingHtml.includes('data-proposal-note="fixture-story-one">Sending…</p>'));
assert.strictEqual((sendingHtml.match(/data-proposal-id="fixture-story-one"[^>]*disabled/g) || []).length, 2);
const alertState = script.newVoteState(true, 0);
alertState.notes["fixture-story-one"] = { html: "Sign in to vote on proposals. <a href=\"/sign-in/\">Sign in</a>", alert: true };
assert.ok(script.voteNoteHtml(storyOne, alertState).includes("proposals-vote-note is-alert"));

assert.strictEqual(script.defaultGroup(entries), "stories");
const conceptHeavy = [
  { id: "a", group: "stories", title: "A", state: "in_steering" },
  { id: "b", group: "concepts", title: "B", state: "in_steering" },
  { id: "c", group: "concepts", title: "C", state: "editor_review" },
  { id: "d", group: "concepts", title: "D", state: "approved" },
];
assert.strictEqual(script.defaultGroup(conceptHeavy), "concepts");
assert.strictEqual(script.defaultGroup(conceptHeavy.filter((entry) => entry.id === "d")), "concepts");
assert.strictEqual(script.defaultGroup(entries.filter((entry) => entry.group === "stories" && entry.state === "draft")), "stories");
assert.strictEqual(script.defaultGroup(entries.filter((entry) => entry.group === "map_changes")), "map_changes");
assert.strictEqual(script.defaultGroup([]), "stories");
assert.ok(script.queueHtml(conceptHeavy, { group: script.defaultGroup(conceptHeavy), sort: "top" }, script.newVoteState(true, 0), 0).includes('data-proposals-tab="concepts" aria-pressed="true"'));

function buildFakeSection() {
  const listeners = {};
  return {
    innerHTML: "",
    classList: { remove() {} },
    getAttribute: (name) => (name === "data-proposals-live" ? "queue" : null),
    setAttribute() {},
    querySelectorAll: () => [],
    querySelector: () => null,
    addEventListener: (name, handler) => { listeners[name] = handler; },
    contains: () => true,
    click(selector, attributes) {
      const button = { disabled: false, getAttribute: (name) => attributes[name] === undefined ? null : attributes[name], hasAttribute: (name) => attributes[name] !== undefined };
      listeners.click({ target: { closest: (query) => (query.includes(selector) ? button : null) } });
    },
  };
}

async function runVoteFlow() {
  const section = buildFakeSection();
  const postedBodies = [];
  let releasePost;
  const flowScope = {
    papyrusReader: { api: "/api/reader", proposalVoting: true },
    location: { hash: "" },
    document: { querySelectorAll: () => [section], activeElement: null, getElementById: () => null },
    fetch: (url, options) => {
      if (url.endsWith("_data/proposals/index.json")) return Promise.resolve({ ok: true, json: () => Promise.resolve({ generatedAt: "2026-10-22T12:00:00Z", proposals: JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "proposals", "_data", "proposals", "index.json"), "utf8")) }) });
      if (url.includes("/me?")) return Promise.resolve({ ok: true, json: () => Promise.resolve({ subjectVotes: { "proposal:fixture-story-one": 1 } }) });
      postedBodies.push(JSON.parse(options.body));
      return new Promise((resolve) => { releasePost = () => resolve({ ok: true, status: 200, json: () => Promise.resolve({}) }); });
    },
  };
  await script.start(flowScope);
  assert.ok(section.innerHTML.includes('data-proposals-tab="stories" aria-pressed="true"'));
  assert.ok(section.innerHTML.includes("You voted up · "));
  const conceptOneNet = entries.find((entry) => entry.id === "fixture-story-one").votes.net;
  section.click("[data-proposal-undo]", { "data-proposal-id": "fixture-story-one", "data-proposal-undo": "" });
  assert.ok(section.innerHTML.includes("Sending…"));
  assert.ok(/data-proposal-id="fixture-story-one"[^>]*disabled/.test(section.innerHTML));
  assert.deepStrictEqual(plain(postedBodies), [{ subject: { type: "proposal", id: "fixture-story-one" }, value: null }]);
  releasePost();
  await new Promise((resolve) => setTimeout(resolve, 0));
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.ok(!section.innerHTML.includes("Sending…"));
  assert.ok(!section.innerHTML.includes("You voted"));
  assert.ok(section.innerHTML.includes('<span class="proposals-vote-count" aria-label="Net votes">' + script.formatNet(conceptOneNet - 1) + "</span>") || conceptOneNet === 0);
}

async function runSignedOutFlow() {
  const section = buildFakeSection();
  const flowScope = {
    papyrusReader: { api: "/api/reader", proposalVoting: true },
    location: { hash: "" },
    document: { querySelectorAll: () => [section], activeElement: null, getElementById: () => null },
    fetch: (url) => {
      if (url.endsWith("_data/proposals/index.json")) return Promise.resolve({ ok: true, json: () => Promise.resolve(JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "proposals", "_data", "proposals", "index.json"), "utf8"))) });
      return Promise.resolve({ ok: false, status: 401, json: () => Promise.resolve({}) });
    },
  };
  await script.start(flowScope);
  section.click("[data-proposal-vote]", { "data-proposal-id": "fixture-story-one", "data-proposal-vote": "up" });
  await new Promise((resolve) => setTimeout(resolve, 0));
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.ok(section.innerHTML.includes("proposals-vote-note is-alert"));
  assert.ok(section.innerHTML.includes('href="/sign-in/"'));
}

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
const signedInVoteState = script.newVoteState(true, 0);
const disabledVoteState = script.newVoteState(false, 0);
const signedOutVoteState = script.newVoteState(true, 0);
const signedOutScope = Object.assign({}, signedInScope, { fetch: () => Promise.resolve({ ok: false, status: 401, json: () => Promise.resolve({}) }) });
Promise.all([
  script.start(missingScope),
  script.start(emptyScope),
  script.loadOwnProposalVotes(signedInScope, entries, signedInVoteState),
  script.loadOwnProposalVotes(signedInScope, entries, disabledVoteState),
  script.loadOwnProposalVotes(signedOutScope, entries, signedOutVoteState),
  runVoteFlow(),
  runSignedOutFlow(),
]).then(() => {
  assert.strictEqual(untouchedMount.innerHTML, "PLACEHOLDER");
  assert.deepStrictEqual(plain(signedInVoteState.mine), { "fixture-story-one": 1, "fixture-concept-one": -1 });
  assert.strictEqual(requestedUrls.length, 1);
  assert.ok(requestedUrls[0].startsWith("/api/reader/me?subjects=proposal%3Afixture-"));
  assert.deepStrictEqual(plain(disabledVoteState.mine), {});
  assert.deepStrictEqual(plain(signedOutVoteState.mine), {});
  console.log("proposals script checks passed");
});
