(function (globalScope, buildModule) {
  var moduleApi = buildModule();
  if (typeof module === "object" && module.exports) module.exports = moduleApi;
  if (typeof document !== "undefined") {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { moduleApi.start(globalScope); });
    else moduleApi.start(globalScope);
  }
})(typeof window !== "undefined" ? window : this, function () {
  "use strict";

  var INDEX_PATH = "_data/proposals/index.json";
  var GROUP_ORDER = ["stories", "concepts", "map_changes"];
  var GROUP_LABELS = { stories: "Stories", concepts: "Concepts", map_changes: "Map changes" };
  var KIND_LABELS = { stories: "Story", concepts: "Concept", map_changes: "Map change" };
  var SORT_ORDER = ["top", "new", "controversial"];
  var SORT_LABELS = { top: "Top", new: "New", controversial: "Controversial" };
  var HOME_LIMIT = 3;
  var VOTING_SOON_TEXT = "Proposal voting opens soon";
  var SIGN_IN_TEXT = "Sign in to vote on proposals.";
  var SIGN_IN_PATH = "/sign-in/";
  var VOTE_FAILED_TEXT = "Your vote did not go through. Try again later.";
  var SENDING_TEXT = "Sending\u2026";
  var STEERING_STATES = ["in_steering", "editor_review"];

  var ICON_UP = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" aria-hidden="true"><path d="M8 3l5.5 9h-11z"/></svg>';
  var ICON_DOWN = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" aria-hidden="true"><path d="M8 13l5.5-9h-11z"/></svg>';
  var STATE_MARKS = {
    draft: { word: "Draft", className: "proposals-mark-draft", icon: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M10.5 2.5l3 3-8 8H2.5v-3z"/></svg>' },
    in_steering: { word: "In steering", className: "proposals-mark-steering", icon: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M5 13V3M2.5 5.5L5 3l2.5 2.5"/><path d="M11 3v10M8.5 10.5L11 13l2.5-2.5"/></svg>' },
    editor_review: { word: "Editor review", className: "", icon: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M1.5 8s2.4-4.5 6.5-4.5S14.5 8 14.5 8 12.1 12.5 8 12.5 1.5 8 1.5 8z"/><circle cx="8" cy="8" r="2"/></svg>' },
    approved: { word: "Approved", className: "proposals-mark-approved", icon: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M3 8.5l3.2 3.2L13 4.5"/></svg>' },
    declined: { word: "Declined", className: "proposals-mark-declined", icon: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8"/></svg>' },
    overridden_by_editor: { word: "Overridden by editor", className: "proposals-mark-overridden", icon: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M8 1.8l5.2 2v4.1c0 3.2-2.3 5.4-5.2 6.3-2.9-.9-5.2-3.1-5.2-6.3V3.8z"/></svg>' }
  };
  var EDITOR_MARKS = {
    pinned: { word: "Pinned", icon: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M6 2h4l-.5 4 2.5 2.5H4L6.5 6z"/><path d="M8 8.5V14"/></svg>' },
    held: { word: "On hold", icon: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M5.5 3v10M10.5 3v10"/></svg>' }
  };
  var FIGURE_WIDTH = 560;
  var FIGURE_HEIGHT = 200;
  var FIGURE_PADDING = { top: 14, right: 120, bottom: 28, left: 44 };
  var FIGURE_SERIES_STYLES = [
    { dash: "", marker: "circle" },
    { dash: "7 4", marker: "square" },
    { dash: "1.5 3.5", marker: "triangle" }
  ];
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  function escapeHtml(value) {
    return String(value === undefined || value === null ? "" : value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function numberOrZero(value) {
    var parsed = Number(value);
    return isFinite(parsed) ? parsed : 0;
  }

  function normaliseEntries(payload) {
    var list = Array.isArray(payload) ? payload : payload && (payload.proposals || payload.entries || payload.items);
    if (!Array.isArray(list)) return [];
    return list.filter(function (entry) {
      return entry && typeof entry === "object" && entry.id && entry.title && GROUP_ORDER.indexOf(entry.group) >= 0;
    });
  }

  function voteCounts(entry) {
    var votes = entry.votes || {};
    var up = numberOrZero(votes.up);
    var down = numberOrZero(votes.down);
    var net = votes.net === undefined || votes.net === null ? up - down : numberOrZero(votes.net);
    return { up: up, down: down, net: net };
  }

  function indexGeneratedAt(payload) {
    var parsed = payload && !Array.isArray(payload) ? Date.parse(payload.generatedAt) : NaN;
    return isFinite(parsed) ? parsed : 0;
  }

  function ownVoteAdjustment(entry, voteState) {
    var mine = voteState.mine[entry.id] || 0;
    if (!mine) return 0;
    var castAt = voteState.castAt[entry.id];
    if (castAt !== undefined) return voteState.generatedAt >= castAt ? 0 : mine;
    var counts = voteCounts(entry);
    return counts.up + counts.down === 0 && counts.net === 0 ? mine : 0;
  }

  function shownNetFor(entry, voteState) {
    var baseline = voteState.baseline[entry.id];
    if (baseline !== undefined) return baseline;
    return voteCounts(entry).net + ownVoteAdjustment(entry, voteState);
  }

  function defaultGroup(entries) {
    var best = null;
    var bestCount = 0;
    GROUP_ORDER.forEach(function (group) {
      var count = entriesInGroup(entries, group).filter(function (entry) { return STEERING_STATES.indexOf(entry.state) >= 0; }).length;
      if (count > bestCount) { best = group; bestCount = count; }
    });
    if (best) return best;
    if (entriesInGroup(entries, "stories").length) return "stories";
    return GROUP_ORDER.filter(function (group) { return entriesInGroup(entries, group).length; })[0] || "stories";
  }

  function formatNet(net) {
    var rounded = Math.round(net * 10) / 10;
    var text = String(Math.abs(rounded));
    return (rounded < 0 ? "−" : "") + text;
  }

  function timeOf(entry, field) {
    var parsed = Date.parse(entry[field]);
    return isFinite(parsed) ? parsed : 0;
  }

  function pinnedFirst(compare) {
    return function (a, b) { return ((b.pinned === true) - (a.pinned === true)) || compare(a, b); };
  }

  function sortEntries(entries, sortName) {
    var copy = entries.slice();
    var byNewest = function (a, b) { return timeOf(b, "createdAt") - timeOf(a, "createdAt"); };
    if (sortName === "new") return copy.sort(pinnedFirst(byNewest));
    if (sortName === "controversial") {
      return copy.sort(pinnedFirst(function (a, b) {
        var left = voteCounts(a);
        var right = voteCounts(b);
        return (Math.min(right.up, right.down) - Math.min(left.up, left.down))
          || ((right.up + right.down) - (left.up + left.down))
          || byNewest(a, b);
      }));
    }
    return copy.sort(pinnedFirst(function (a, b) { return (voteCounts(b).net - voteCounts(a).net) || byNewest(a, b); }));
  }

  function entriesInGroup(entries, group) {
    return entries.filter(function (entry) { return entry.group === group; });
  }

  function steeringLeaders(entries, limit) {
    var open = entries.filter(function (entry) { return entry.state === "in_steering" || entry.state === "editor_review"; });
    return sortEntries(open, "top").slice(0, limit);
  }

  function targetNames(entry) {
    var targets = Array.isArray(entry.targets) ? entry.targets : [];
    return targets.map(function (target) {
      if (typeof target === "string") return target;
      return target && (target.name || target.title || target.label || target.key || target.id) || "";
    }).filter(Boolean);
  }

  function targetKeys(entry) {
    var targets = Array.isArray(entry.targets) ? entry.targets : [];
    var keys = [];
    targets.forEach(function (target) {
      if (typeof target === "string") { keys.push(target); return; }
      if (target) [target.name, target.title, target.label, target.key, target.id, target.slug].forEach(function (value) { if (value) keys.push(value); });
    });
    return keys;
  }

  function normaliseKey(value) {
    return String(value).toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  }

  function touchesConcept(entry, conceptName, conceptKey) {
    var wanted = [conceptName, conceptKey].filter(Boolean).map(normaliseKey);
    return targetKeys(entry).some(function (key) { return wanted.indexOf(normaliseKey(key)) >= 0; });
  }

  function evidenceText(entry) {
    var evidence = entry.evidence;
    if (typeof evidence === "number") return evidence + (evidence === 1 ? " signal" : " signals");
    if (typeof evidence === "string") return evidence;
    if (Array.isArray(evidence)) return evidence.length + (evidence.length === 1 ? " signal" : " signals");
    if (evidence && typeof evidence === "object") {
      var parts = [];
      var signals = evidence.signals !== undefined ? evidence.signals : evidence.count;
      if (Array.isArray(signals)) signals = signals.length;
      if (signals !== undefined && signals !== null) parts.push(signals + (Number(signals) === 1 ? " signal" : " signals"));
      var summary = evidence.summary || evidence.source || evidence.text;
      if (summary) parts.push(summary);
      return parts.join(" · ");
    }
    return "";
  }

  function ageText(isoDate, now) {
    var then = Date.parse(isoDate);
    if (!isFinite(then)) return "";
    var seconds = Math.max(0, ((now === undefined ? Date.now() : now) - then) / 1000);
    if (seconds < 3600) return Math.max(1, Math.floor(seconds / 60)) + " min ago";
    if (seconds < 86400) return Math.floor(seconds / 3600) + " h ago";
    if (seconds < 86400 * 30) return Math.floor(seconds / 86400) + " d ago";
    return formatDate(isoDate);
  }

  function formatDate(isoDate) {
    var parsed = new Date(isoDate);
    if (!isFinite(parsed.getTime())) return "";
    return parsed.getUTCDate() + " " + MONTHS[parsed.getUTCMonth()] + " " + parsed.getUTCFullYear();
  }

  function capitalise(text) {
    var spaced = String(text).replace(/_/g, " ").trim();
    return spaced.charAt(0).toUpperCase() + spaced.slice(1);
  }

  function pluralise(count, one, many) {
    return count + " " + (count === 1 ? one : many);
  }

  function stateMark(state) {
    var mark = STATE_MARKS[state] || STATE_MARKS.draft;
    var word = STATE_MARKS[state] ? mark.word : capitalise(state || "draft");
    var label = state === "declined" ? '<span class="proposals-mark-struck">' + escapeHtml(word) + "</span>" : escapeHtml(word);
    return '<span class="proposals-mark ' + mark.className + '">' + mark.icon + label + "</span>";
  }

  function editorMarksHtml(entry) {
    return ["pinned", "held"].filter(function (flag) { return entry[flag] === true; }).map(function (flag) {
      return '<span class="proposals-mark proposals-mark-' + flag + '">' + EDITOR_MARKS[flag].icon + EDITOR_MARKS[flag].word + "</span>";
    }).join("");
  }

  function excludedVotes(entry) {
    return entry.excluded && typeof entry.excluded === "object" ? numberOrZero(entry.excluded.votes) : 0;
  }

  function excludedHtml(entry) {
    var count = excludedVotes(entry);
    if (count <= 0) return "";
    var text = entry.excluded.note || "Excluded " + pluralise(count, "vote", "votes") + ". They no longer count.";
    return '<p class="proposals-excluded">' + escapeHtml(text) + "</p>";
  }

  function editorDecisions(entries) {
    return entries.filter(function (entry) {
      return !!(entry.override && entry.override.result) || excludedVotes(entry) > 0;
    }).sort(function (a, b) {
      return timeOf(b.override || {}, "at") - timeOf(a.override || {}, "at") || timeOf(b, "updatedAt") - timeOf(a, "updatedAt");
    });
  }

  function provenanceLabel(entry) {
    var mark = STATE_MARKS[entry.state];
    var label = String(entry.label || "");
    if (mark && label.indexOf(mark.word + " \u00b7 ") === 0) return label.slice(mark.word.length + 3);
    return label;
  }

  function hasDecisionLine(entry) {
    return entry.state === "overridden_by_editor" || !!(entry.override && entry.override.result) || !!(entry.decision && entry.decision.result);
  }

  function communityText(entry) {
    var counts = voteCounts(entry);
    var community = entry.communityResult;
    var arrow = counts.net < 0 ? "▼ " : "▲ ";
    if (typeof community === "string" && community) return escapeHtml(community) + " (" + arrow + formatNet(Math.abs(counts.net)) + ")";
    if (community && typeof community === "object") {
      var word = community.label || community.result || community.state || "";
      return (word ? escapeHtml(capitalise(word)) + " " : "") + "(" + arrow + formatNet(Math.abs(counts.net)) + ")";
    }
    return arrow + formatNet(Math.abs(counts.net));
  }

  function decisionLineHtml(entry) {
    if (!hasDecisionLine(entry)) return "";
    var decision = (entry.override && entry.override.result ? entry.override : entry.decision) || {};
    var result = decision.result || decision.state || "";
    var editorPart = result ? "<b>" + escapeHtml(capitalise(result)) + "</b>" : "<b>Decision recorded</b>";
    if (decision.reason) editorPart += ", “" + escapeHtml(decision.reason) + "”";
    var byPart = [decision.by || "Editor", formatDate(decision.at)].filter(Boolean).join(" · ");
    return '<p class="proposals-tier"><span>Community: <b>' + communityText(entry) + "</b></span>"
      + '<span aria-hidden="true">·</span><span>Editor: ' + editorPart + "</span>"
      + '<span aria-hidden="true">·</span><span>' + escapeHtml(byPart) + "</span></p>";
  }

  function voteButtonsHtml(entry, voteState, countClass) {
    var mine = voteState.mine[entry.id] || 0;
    var sending = voteState.sending[entry.id] === true;
    var disabled = voteState.enabled && !sending ? "" : " disabled";
    var soon = voteState.enabled ? "" : ' title="' + VOTING_SOON_TEXT + '"';
    var title = escapeHtml(entry.title);
    var identifier = escapeHtml(entry.id);
    return '<button type="button" data-proposal-vote="up" data-proposal-id="' + identifier + '" aria-pressed="' + (mine === 1) + '" aria-label="Vote up: ' + title + '"' + disabled + soon + ">" + ICON_UP + "</button>"
      + '<span class="' + countClass + '" aria-label="Net votes">' + formatNet(shownNetFor(entry, voteState)) + "</span>"
      + '<button type="button" data-proposal-vote="down" data-proposal-id="' + identifier + '" aria-pressed="' + (mine === -1) + '" aria-label="Vote down: ' + title + '"' + disabled + soon + ">" + ICON_DOWN + "</button>";
  }

  function voteControlsHtml(entry, voteState) {
    return '<div class="proposals-vote" role="group" aria-label="Votes on ' + escapeHtml(entry.title) + '">'
      + voteButtonsHtml(entry, voteState, "proposals-vote-count") + "</div>";
  }

  function ownVoteLineHtml(entry, voteState) {
    var mine = voteState.mine[entry.id] || 0;
    if (!mine) return "";
    var disabled = voteState.enabled && voteState.sending[entry.id] !== true ? "" : " disabled";
    return '<p class="proposals-vote-mine">You voted ' + (mine === 1 ? "up" : "down") + " \u00b7 "
      + '<button type="button" class="proposals-undo" data-proposal-undo data-proposal-id="' + escapeHtml(entry.id) + '"' + disabled + ">Undo</button></p>";
  }

  function voteNoteHtml(entry, voteState) {
    var sending = voteState.sending[entry.id] === true;
    var note = voteState.notes[entry.id];
    var content = sending ? escapeHtml(SENDING_TEXT) : note ? note.html : "";
    var alertClass = !sending && note && note.alert ? " is-alert" : "";
    return '<p class="proposals-vote-note' + alertClass + '" role="status" aria-live="polite" data-proposal-note="' + escapeHtml(entry.id) + '">' + content + "</p>";
  }

  function votingNoticeHtml(voteState) {
    return voteState.enabled ? "" : '<p class="proposals-voting-soon">' + VOTING_SOON_TEXT + "</p>";
  }

  function signInNoteHtml() {
    return escapeHtml(SIGN_IN_TEXT) + ' <a href="' + SIGN_IN_PATH + '">Sign in</a>';
  }

  function queueRowHtml(entry, voteState, now) {
    var comments = numberOrZero(entry.comments);
    var evidence = evidenceText(entry);
    var targets = targetNames(entry);
    var metaParts = [ageText(entry.createdAt, now), pluralise(comments, "comment", "comments")].filter(Boolean);
    return '<li class="proposals-row" id="proposal-' + escapeHtml(entry.id) + '">'
      + voteControlsHtml(entry, voteState)
      + '<div class="proposals-row-body"><div class="proposals-row-tags">' + stateMark(entry.state) + editorMarksHtml(entry)
      + '<span class="kicker proposals-row-kind">' + KIND_LABELS[entry.group] + "</span>"
      + (provenanceLabel(entry) ? '<span class="proposals-row-label">' + escapeHtml(provenanceLabel(entry)) + "</span>" : "")
      + '<span class="proposals-row-meta">' + escapeHtml(metaParts.join(" · ")) + "</span></div>"
      + '<p class="proposals-row-title">' + escapeHtml(entry.title) + "</p>"
      + (entry.summary ? '<p class="proposals-row-change">' + escapeHtml(entry.summary) + "</p>" : "")
      + (targets.length ? '<p class="proposals-row-targets">Touches ' + targets.map(function (name) { return "<b>" + escapeHtml(name) + "</b>"; }).join(", ") + "</p>" : "")
      + (evidence ? '<p class="proposals-row-evidence">Evidence · ' + escapeHtml(evidence) + "</p>" : "")
      + figureHtml(entry)
      + decisionLineHtml(entry)
      + excludedHtml(entry)
      + ownVoteLineHtml(entry, voteState)
      + voteNoteHtml(entry, voteState)
      + "</div></li>";
  }

  function queueHtml(entries, viewState, voteState, now) {
    var tabs = GROUP_ORDER.map(function (group) {
      return '<button type="button" data-proposals-tab="' + group + '" aria-pressed="' + (viewState.group === group) + '">'
        + GROUP_LABELS[group] + " <span>" + entriesInGroup(entries, group).length + "</span></button>";
    }).join("");
    var sorts = SORT_ORDER.map(function (sortName) {
      return '<button type="button" data-proposals-sort="' + sortName + '" aria-pressed="' + (viewState.sort === sortName) + '">' + SORT_LABELS[sortName] + "</button>";
    }).join("");
    var visible = sortEntries(entriesInGroup(entries, viewState.group), viewState.sort);
    var rows = visible.length
      ? '<ol class="proposals-list">' + visible.map(function (entry) { return queueRowHtml(entry, voteState, now); }).join("") + "</ol>"
      : '<p class="proposals-empty">No ' + GROUP_LABELS[viewState.group].toLowerCase() + " proposals in the queue yet.</p>";
    return '<h2 id="proposals-queue-h" class="proposals-queue-heading">The queue</h2>'
      + '<div class="proposals-controls"><div class="proposals-tabs" role="group" aria-label="Proposal types">' + tabs + "</div>"
      + '<div class="proposals-sorts"><span class="kicker">Sort</span><div role="group" aria-label="Sort">' + sorts + "</div></div></div>"
      + votingNoticeHtml(voteState) + rows;
  }

  function homeRowHtml(entry, voteState) {
    var title = escapeHtml(entry.title);
    return '<li class="front-proposal"><div class="front-vote" role="group" aria-label="Votes on ' + title + '">'
      + voteButtonsHtml(entry, voteState, "front-vote-count") + "</div>"
      + '<div class="front-proposal-body"><div class="front-proposal-tags">' + stateMark(entry.state)
      + '<span class="kicker">' + KIND_LABELS[entry.group] + "</span></div>"
      + '<a class="front-proposal-title" href="/proposals/#proposal-' + escapeHtml(entry.id) + '">' + title + "</a>"
      + (entry.summary ? '<span class="front-proposal-change">' + escapeHtml(entry.summary) + "</span>" : "")
      + ownVoteLineHtml(entry, voteState)
      + voteNoteHtml(entry, voteState) + "</div></li>";
  }

  function conceptRowHtml(entry, voteState) {
    var shownNet = shownNetFor(entry, voteState);
    return '<li class="concept-proposal-row">' + voteControlsHtml(entry, voteState)
      + stateMark(entry.state)
      + '<span class="concept-proposal-kind">' + KIND_LABELS[entry.group] + "</span> "
      + '<a href="/proposals/#proposal-' + escapeHtml(entry.id) + '">' + escapeHtml(entry.title) + "</a> "
      + '<span class="concept-note">' + escapeHtml(pluralise(Math.round(shownNet * 10) / 10, "net vote", "net votes")) + "</span>"
      + ownVoteLineHtml(entry, voteState)
      + voteNoteHtml(entry, voteState) + "</li>";
  }

  function dropPlaceholderMarking(section) {
    section.classList.remove("is-placeholder");
    var tags = section.querySelectorAll(".placeholder-tag");
    Array.prototype.forEach.call(tags, function (tag) { tag.parentNode.removeChild(tag); });
  }

  function readSettings(scope) {
    return Object.assign({ base: "/", api: "/api/reader" }, (scope && scope.papyrusReader) || {});
  }

  function votingEnabled(scope) {
    var settings = (scope && scope.papyrusReader) || {};
    return settings.proposalVoting === true || (Array.isArray(settings.voteSubjects) && settings.voteSubjects.indexOf("proposal") >= 0);
  }

  function postVote(scope, proposalId, value) {
    var settings = readSettings(scope);
    return scope.fetch(settings.api + "/vote", {
      method: "POST",
      credentials: "same-origin",
      headers: { "content-type": "application/json", accept: "application/json" },
      body: JSON.stringify({ subject: { type: "proposal", id: proposalId }, value: value })
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (body) {
        return { ok: response.ok, status: response.status, body: body };
      });
    });
  }

  function netFromResponse(body) {
    if (!body) return null;
    var votes = body.votes || body;
    var net = votes && votes.net;
    return typeof net === "number" && isFinite(net) ? net : null;
  }

  function voteFailureText(result) {
    if (result.status === 401) return "signed-out";
    if (result.status === 503 && result.body && result.body.error === "reader_identity_unavailable") return "Reader sign-in is not open yet.";
    if (result.status === 404 || result.status === 400 || result.status === 405) return "unsupported";
    if (result.status === 429) return "Too many actions. Try again in a few minutes.";
    return VOTE_FAILED_TEXT;
  }

  function wireVotes(container, scope, voteState, entriesById, rerender) {
    container.addEventListener("click", function (event) {
      var button = event.target.closest && event.target.closest("[data-proposal-vote],[data-proposal-undo]");
      if (!button || !container.contains(button) || button.disabled) return;
      var proposalId = button.getAttribute("data-proposal-id");
      if (voteState.sending[proposalId]) return;
      var isUndo = button.hasAttribute("data-proposal-undo");
      var direction = button.getAttribute("data-proposal-vote") === "up" ? 1 : -1;
      var previous = voteState.mine[proposalId] || 0;
      var next = isUndo || previous === direction ? null : direction;
      var shownBefore = shownNetFor(entriesById[proposalId], voteState);
      voteState.sending[proposalId] = true;
      delete voteState.notes[proposalId];
      rerender();
      postVote(scope, proposalId, next).then(function (result) {
        delete voteState.sending[proposalId];
        if (result.ok) {
          var reported = netFromResponse(result.body);
          voteState.baseline[proposalId] = reported !== null ? reported : shownBefore + (next || 0) - previous;
          voteState.mine[proposalId] = next || 0;
          voteState.castAt[proposalId] = Date.now();
          rerender();
          return;
        }
        var failure = voteFailureText(result);
        if (failure === "unsupported") {
          voteState.enabled = false;
        } else if (failure === "signed-out") {
          voteState.notes[proposalId] = { html: signInNoteHtml(), alert: true };
        } else {
          voteState.notes[proposalId] = { html: escapeHtml(failure), alert: false };
        }
        rerender();
      }).catch(function () {
        delete voteState.sending[proposalId];
        voteState.notes[proposalId] = { html: escapeHtml(VOTE_FAILED_TEXT), alert: false };
        rerender();
      });
    });
  }

  function mountQueue(section, entries, scope, voteState, now) {
    var viewState = { group: defaultGroup(entries), sort: "top" };
    var entriesById = {};
    entries.forEach(function (entry) { entriesById[entry.id] = entry; });
    dropPlaceholderMarking(section);
    section.setAttribute("data-proposals-state", "live");
    function render() {
      var focused = scope.document.activeElement;
      var focusSelector = focused && focused.getAttribute && (focused.getAttribute("data-proposals-tab") ? '[data-proposals-tab="' + focused.getAttribute("data-proposals-tab") + '"]'
        : focused.getAttribute("data-proposals-sort") ? '[data-proposals-sort="' + focused.getAttribute("data-proposals-sort") + '"]'
        : focused.hasAttribute("data-proposal-undo") ? '[data-proposal-undo][data-proposal-id="' + focused.getAttribute("data-proposal-id") + '"]'
        : focused.getAttribute("data-proposal-vote") ? '[data-proposal-vote="' + focused.getAttribute("data-proposal-vote") + '"][data-proposal-id="' + focused.getAttribute("data-proposal-id") + '"]' : "");
      section.innerHTML = queueHtml(entries, viewState, voteState, now);
      var restored = focusSelector ? section.querySelector(focusSelector) : null;
      if (restored) restored.focus();
    }
    section.addEventListener("click", function (event) {
      var tab = event.target.closest && event.target.closest("[data-proposals-tab]");
      var sort = event.target.closest && event.target.closest("[data-proposals-sort]");
      if (tab) { viewState.group = tab.getAttribute("data-proposals-tab"); render(); }
      if (sort) { viewState.sort = sort.getAttribute("data-proposals-sort"); render(); }
    });
    wireVotes(section, scope, voteState, entriesById, render);
    render();
    var hash = scope.location && scope.location.hash;
    if (hash && /^#proposal-/.test(hash)) {
      var target = scope.document.getElementById(hash.slice(1));
      if (!target && entriesById[hash.slice("#proposal-".length)]) {
        viewState.group = entriesById[hash.slice("#proposal-".length)].group;
        render();
        target = scope.document.getElementById(hash.slice(1));
      }
      if (target && target.scrollIntoView) target.scrollIntoView();
    }
  }

  function mountHome(section, entries, scope, voteState) {
    var leaders = steeringLeaders(entries, HOME_LIMIT);
    if (!leaders.length) return;
    var list = section.querySelector(".front-proposal-list");
    if (!list) return;
    var entriesById = {};
    leaders.forEach(function (entry) { entriesById[entry.id] = entry; });
    dropPlaceholderMarking(section);
    section.setAttribute("data-proposals-state", "live");
    var note = section.querySelector(".front-proposals-note");
    function render() {
      list.innerHTML = leaders.map(function (entry) { return homeRowHtml(entry, voteState); }).join("");
      var existing = section.querySelector(".proposals-voting-soon");
      if (existing) existing.parentNode.removeChild(existing);
      if (!voteState.enabled && note) note.insertAdjacentHTML("afterend", votingNoticeHtml(voteState));
    }
    wireVotes(section, scope, voteState, entriesById, render);
    render();
  }

  function mountConcept(section, entries, scope, voteState) {
    var matching = sortEntries(entries.filter(function (entry) {
      return entry.state !== "approved" && entry.state !== "declined"
        && touchesConcept(entry, section.getAttribute("data-concept-name"), section.getAttribute("data-concept-key"));
    }), "top");
    if (!matching.length) {
      section.hidden = true;
      section.setAttribute("data-proposals-state", "none-match");
      return;
    }
    var entriesById = {};
    matching.forEach(function (entry) { entriesById[entry.id] = entry; });
    dropPlaceholderMarking(section);
    section.setAttribute("data-proposals-state", "live");
    var headingBlock = section.querySelector(".section-heading");
    var notice = section.querySelector(".concept-note");
    var list = section.querySelector(".concept-proposal-list");
    function render() {
      if (notice && notice.parentNode === section) notice.parentNode.removeChild(notice);
      notice = null;
      list.innerHTML = matching.map(function (entry) { return conceptRowHtml(entry, voteState); }).join("");
      var existing = section.querySelector(".proposals-voting-soon");
      if (existing) existing.parentNode.removeChild(existing);
      if (!voteState.enabled && headingBlock) headingBlock.insertAdjacentHTML("afterend", votingNoticeHtml(voteState));
    }
    wireVotes(section, scope, voteState, entriesById, render);
    render();
  }

  function figureOf(entry) {
    var figure = entry.evidence && typeof entry.evidence === "object" ? entry.evidence.figure : null;
    if (!figure || figure.type !== "line" || !Array.isArray(figure.x) || figure.x.length < 2 || !Array.isArray(figure.series)) return null;
    var series = figure.series.filter(function (line) {
      return line && Array.isArray(line.values) && line.values.length === figure.x.length;
    }).slice(0, FIGURE_SERIES_STYLES.length);
    return series.length ? { figure: figure, series: series } : null;
  }

  function finiteValue(value) {
    return value !== null && value !== undefined && value !== "" && isFinite(Number(value));
  }

  function markerPath(kind, x, y) {
    if (kind === "square") return "M" + (x - 3) + " " + (y - 3) + "h6v6h-6z";
    if (kind === "triangle") return "M" + x + " " + (y - 3.8) + "l3.8 6.6h-7.6z";
    return "M" + (x - 3.2) + " " + y + "a3.2 3.2 0 1 0 6.4 0a3.2 3.2 0 1 0 -6.4 0";
  }

  function formatFigureValue(value, unit) {
    return formatNet(Number(value)) + (unit ? " " + unit : "");
  }

  function figureHtml(entry) {
    var parsed = figureOf(entry);
    if (!parsed) return "";
    var figure = parsed.figure;
    var values = [];
    parsed.series.forEach(function (line) { line.values.forEach(function (value) { if (finiteValue(value)) values.push(Number(value)); }); });
    if (!values.length) return "";
    var low = Math.min(0, Math.min.apply(null, values));
    var high = Math.max.apply(null, values);
    if (high === low) high = low + 1;
    var plotWidth = FIGURE_WIDTH - FIGURE_PADDING.left - FIGURE_PADDING.right;
    var plotHeight = FIGURE_HEIGHT - FIGURE_PADDING.top - FIGURE_PADDING.bottom;
    var lastIndex = figure.x.length - 1;
    function xAt(index) { return Math.round((FIGURE_PADDING.left + plotWidth * index / lastIndex) * 10) / 10; }
    function yAt(value) { return Math.round((FIGURE_PADDING.top + plotHeight * (1 - (Number(value) - low) / (high - low))) * 10) / 10; }
    var unit = figure.unit ? String(figure.unit) : "";
    var descriptions = [];
    var lines = parsed.series.map(function (line, seriesIndex) {
      var style = FIGURE_SERIES_STYLES[seriesIndex];
      var label = String(line.label || line.signal || "Series " + (seriesIndex + 1));
      var path = "";
      var markers = "";
      var lastPoint = null;
      var firstValue = null;
      line.values.forEach(function (value, index) {
        if (!finiteValue(value)) { path += " "; return; }
        var x = xAt(index);
        var y = yAt(value);
        path += (path === "" || /\s$/.test(path) ? "M" : "L") + x + " " + y;
        markers += markerPath(style.marker, x, y);
        if (firstValue === null) firstValue = value;
        lastPoint = { x: x, y: y, value: value };
      });
      if (!lastPoint) return "";
      descriptions.push(label + " from " + formatFigureValue(firstValue, unit) + " to " + formatFigureValue(lastPoint.value, unit));
      return '<g class="proposals-figure-series">'
        + '<path d="' + path.trim() + '" fill="none" stroke="currentColor" stroke-width="2"' + (style.dash ? ' stroke-dasharray="' + style.dash + '"' : "") + "/>"
        + '<path d="' + markers + '" fill="currentColor"/>'
        + '<text x="' + (lastPoint.x + 8) + '" y="' + (lastPoint.y + 4) + '">' + escapeHtml(label) + "</text></g>";
    }).join("");
    var title = figure.title ? String(figure.title) : "Trend";
    var axis = '<g class="proposals-figure-axis">'
      + '<path d="M' + FIGURE_PADDING.left + " " + FIGURE_PADDING.top + "V" + (FIGURE_HEIGHT - FIGURE_PADDING.bottom) + "H" + (FIGURE_WIDTH - FIGURE_PADDING.right) + '" fill="none" stroke="currentColor" stroke-width="1"/>'
      + '<text x="' + (FIGURE_PADDING.left - 6) + '" y="' + (FIGURE_PADDING.top + 4) + '" text-anchor="end">' + escapeHtml(formatNet(high)) + "</text>"
      + '<text x="' + (FIGURE_PADDING.left - 6) + '" y="' + (FIGURE_HEIGHT - FIGURE_PADDING.bottom) + '" text-anchor="end">' + escapeHtml(formatNet(low)) + "</text>"
      + '<text x="' + FIGURE_PADDING.left + '" y="' + (FIGURE_HEIGHT - 8) + '">' + escapeHtml(formatDate(figure.x[0])) + "</text>"
      + '<text x="' + (FIGURE_WIDTH - FIGURE_PADDING.right) + '" y="' + (FIGURE_HEIGHT - 8) + '" text-anchor="end">' + escapeHtml(formatDate(figure.x[lastIndex])) + "</text></g>";
    var summary = title + ", weekly" + (unit ? ", in " + unit : "") + ": " + descriptions.join("; ") + ".";
    var footer = [figure.caption, figure.source ? "Source: " + figure.source : ""].filter(Boolean).map(function (text) { return escapeHtml(String(text)); }).join(" · ");
    return '<figure class="proposals-figure"><p class="proposals-figure-title">' + escapeHtml(title) + (unit ? ' <span class="proposals-figure-unit">' + escapeHtml(unit) + "</span>" : "") + "</p>"
      + '<svg viewBox="0 0 ' + FIGURE_WIDTH + " " + FIGURE_HEIGHT + '" role="img" aria-label="' + escapeHtml(summary) + '">' + axis + lines + "</svg>"
      + (footer ? "<figcaption>" + footer + "</figcaption>" : "") + "</figure>";
  }

  function tiersRowHtml(entry) {
    return '<li class="proposals-card"><div class="proposals-row-tags">' + stateMark(entry.state) + editorMarksHtml(entry)
      + '<span class="kicker proposals-row-kind">' + KIND_LABELS[entry.group] + "</span></div>"
      + '<a class="proposals-row-title" href="/proposals/#proposal-' + escapeHtml(entry.id) + '">' + escapeHtml(entry.title) + "</a>"
      + decisionLineHtml(entry) + excludedHtml(entry) + "</li>";
  }

  function mountTiers(section, entries) {
    var list = section.querySelector("[data-proposals-tiers-list]");
    var decided = editorDecisions(entries);
    if (!list || !decided.length) return;
    list.innerHTML = decided.map(tiersRowHtml).join("");
    section.setAttribute("data-proposals-state", "live");
  }

  function fetchIndex(scope) {
    var settings = readSettings(scope);
    return scope.fetch(settings.base + INDEX_PATH, { credentials: "omit", cache: "no-cache" })
      .then(function (response) { return response.ok ? response.json() : null; })
      .then(function (payload) { return { entries: normaliseEntries(payload), generatedAt: indexGeneratedAt(payload) }; })
      .catch(function () { return { entries: [], generatedAt: 0 }; });
  }

  function loadOwnProposalVotes(scope, entries, voteState) {
    if (!voteState.enabled) return Promise.resolve();
    var subjectKeys = entries.map(function (entry) { return "proposal:" + entry.id; });
    var settings = readSettings(scope);
    var url = settings.api + "/me?subjects=" + subjectKeys.map(encodeURIComponent).join(",");
    return scope.fetch(url, { credentials: "same-origin", headers: { accept: "application/json" } }).then(function (response) {
      if (!response.ok) return null;
      return response.json().catch(function () { return null; });
    }).then(function (body) {
      var subjectVotes = (body && body.subjectVotes) || {};
      entries.forEach(function (entry) {
        var value = subjectVotes["proposal:" + entry.id];
        if (value === 1 || value === -1) voteState.mine[entry.id] = value;
      });
    }).catch(function () {});
  }

  function newVoteState(enabled, generatedAt) {
    return { enabled: enabled, generatedAt: generatedAt || 0, mine: {}, baseline: {}, castAt: {}, sending: {}, notes: {} };
  }

  function start(scope) {
    var mounts = scope.document.querySelectorAll("[data-proposals-live]");
    if (!mounts.length || typeof scope.fetch !== "function") return Promise.resolve();
    return fetchIndex(scope).then(function (index) {
      var entries = index.entries;
      if (!entries.length) return;
      var voteState = newVoteState(votingEnabled(scope), index.generatedAt);
      return loadOwnProposalVotes(scope, entries, voteState).then(function () {
        var now = Date.now();
        Array.prototype.forEach.call(mounts, function (section) {
          var kind = section.getAttribute("data-proposals-live");
          if (kind === "queue") mountQueue(section, entries, scope, voteState, now);
          else if (kind === "home") mountHome(section, entries, scope, voteState);
          else if (kind === "concept") mountConcept(section, entries, scope, voteState);
          else if (kind === "tiers") mountTiers(section, entries);
        });
      });
    });
  }

  return {
    loadOwnProposalVotes: loadOwnProposalVotes,
    normaliseEntries: normaliseEntries,
    indexGeneratedAt: indexGeneratedAt,
    newVoteState: newVoteState,
    shownNetFor: shownNetFor,
    defaultGroup: defaultGroup,
    voteNoteHtml: voteNoteHtml,
    sortEntries: sortEntries,
    entriesInGroup: entriesInGroup,
    steeringLeaders: steeringLeaders,
    touchesConcept: touchesConcept,
    formatNet: formatNet,
    ageText: ageText,
    decisionLineHtml: decisionLineHtml,
    excludedHtml: excludedHtml,
    figureHtml: figureHtml,
    editorDecisions: editorDecisions,
    votingEnabled: votingEnabled,
    stateMark: stateMark,
    provenanceLabel: provenanceLabel,
    queueHtml: queueHtml,
    start: start
  };
});
