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

  function formatNet(net) {
    var rounded = Math.round(net * 10) / 10;
    var text = String(Math.abs(rounded));
    return (rounded < 0 ? "−" : "") + text;
  }

  function timeOf(entry, field) {
    var parsed = Date.parse(entry[field]);
    return isFinite(parsed) ? parsed : 0;
  }

  function sortEntries(entries, sortName) {
    var copy = entries.slice();
    var byNewest = function (a, b) { return timeOf(b, "createdAt") - timeOf(a, "createdAt"); };
    if (sortName === "new") return copy.sort(byNewest);
    if (sortName === "controversial") {
      return copy.sort(function (a, b) {
        var left = voteCounts(a);
        var right = voteCounts(b);
        return (Math.min(right.up, right.down) - Math.min(left.up, left.down))
          || ((right.up + right.down) - (left.up + left.down))
          || byNewest(a, b);
      });
    }
    return copy.sort(function (a, b) { return (voteCounts(b).net - voteCounts(a).net) || byNewest(a, b); });
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

  function provenanceLabel(entry) {
    var mark = STATE_MARKS[entry.state];
    var label = String(entry.label || "");
    if (mark && label.indexOf(mark.word + " \u00b7 ") === 0) return label.slice(mark.word.length + 3);
    return label;
  }

  function hasDecisionLine(entry) {
    return entry.state === "overridden_by_editor" || !!(entry.decision && entry.decision.result);
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
    var decision = entry.decision || {};
    var result = decision.result || decision.state || "";
    var editorPart = result ? "<b>" + escapeHtml(capitalise(result)) + "</b>" : "<b>Decision recorded</b>";
    if (decision.reason) editorPart += ", “" + escapeHtml(decision.reason) + "”";
    var byPart = [decision.by || "Editor", formatDate(decision.at)].filter(Boolean).join(" · ");
    return '<p class="proposals-tier"><span>Community: <b>' + communityText(entry) + "</b></span>"
      + '<span aria-hidden="true">·</span><span>Editor: ' + editorPart + "</span>"
      + '<span aria-hidden="true">·</span><span>' + escapeHtml(byPart) + "</span></p>";
  }

  function voteControlsHtml(entry, voteState) {
    var counts = voteCounts(entry);
    var mine = voteState.mine[entry.id] || 0;
    var baseline = voteState.baseline[entry.id];
    var shownNet = baseline !== undefined ? baseline : counts.net;
    var disabled = voteState.enabled ? "" : " disabled";
    var soon = voteState.enabled ? "" : ' title="' + VOTING_SOON_TEXT + '"';
    var title = escapeHtml(entry.title);
    return '<div class="proposals-vote" role="group" aria-label="Votes on ' + title + '">'
      + '<button type="button" data-proposal-vote="up" data-proposal-id="' + escapeHtml(entry.id) + '" aria-pressed="' + (mine === 1) + '" aria-label="Vote up: ' + title + '"' + disabled + soon + ">" + ICON_UP + "</button>"
      + '<span class="proposals-vote-count" aria-label="Net votes">' + formatNet(shownNet) + "</span>"
      + '<button type="button" data-proposal-vote="down" data-proposal-id="' + escapeHtml(entry.id) + '" aria-pressed="' + (mine === -1) + '" aria-label="Vote down: ' + title + '"' + disabled + soon + ">" + ICON_DOWN + "</button>"
      + "</div>";
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
      + '<div class="proposals-row-body"><div class="proposals-row-tags">' + stateMark(entry.state)
      + '<span class="kicker proposals-row-kind">' + KIND_LABELS[entry.group] + "</span>"
      + (provenanceLabel(entry) ? '<span class="proposals-row-label">' + escapeHtml(provenanceLabel(entry)) + "</span>" : "")
      + '<span class="proposals-row-meta">' + escapeHtml(metaParts.join(" · ")) + "</span></div>"
      + '<p class="proposals-row-title">' + escapeHtml(entry.title) + "</p>"
      + (entry.summary ? '<p class="proposals-row-change">' + escapeHtml(entry.summary) + "</p>" : "")
      + (targets.length ? '<p class="proposals-row-targets">Touches ' + targets.map(function (name) { return "<b>" + escapeHtml(name) + "</b>"; }).join(", ") + "</p>" : "")
      + (evidence ? '<p class="proposals-row-evidence">Evidence · ' + escapeHtml(evidence) + "</p>" : "")
      + decisionLineHtml(entry)
      + '<p class="proposals-vote-note" role="status" aria-live="polite" data-proposal-note="' + escapeHtml(entry.id) + '"></p>'
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
    var counts = voteCounts(entry);
    var title = escapeHtml(entry.title);
    var shownNet = voteState.baseline[entry.id] !== undefined ? voteState.baseline[entry.id] : counts.net;
    var mine = voteState.mine[entry.id] || 0;
    var disabled = voteState.enabled ? "" : " disabled";
    var soon = voteState.enabled ? "" : ' title="' + VOTING_SOON_TEXT + '"';
    return '<li class="front-proposal"><div class="front-vote" role="group" aria-label="Votes on ' + title + '">'
      + '<button type="button" data-proposal-vote="up" data-proposal-id="' + escapeHtml(entry.id) + '" aria-pressed="' + (mine === 1) + '" aria-label="Vote up: ' + title + '"' + disabled + soon + ">" + ICON_UP + "</button>"
      + '<span class="front-vote-count" aria-label="Net votes">' + formatNet(shownNet) + "</span>"
      + '<button type="button" data-proposal-vote="down" data-proposal-id="' + escapeHtml(entry.id) + '" aria-pressed="' + (mine === -1) + '" aria-label="Vote down: ' + title + '"' + disabled + soon + ">" + ICON_DOWN + "</button></div>"
      + '<div class="front-proposal-body"><div class="front-proposal-tags">' + stateMark(entry.state)
      + '<span class="kicker">' + KIND_LABELS[entry.group] + "</span></div>"
      + '<a class="front-proposal-title" href="/proposals/#proposal-' + escapeHtml(entry.id) + '">' + title + "</a>"
      + (entry.summary ? '<span class="front-proposal-change">' + escapeHtml(entry.summary) + "</span>" : "")
      + '<p class="proposals-vote-note" role="status" aria-live="polite" data-proposal-note="' + escapeHtml(entry.id) + '"></p></div></li>';
  }

  function conceptRowHtml(entry, voteState) {
    var counts = voteCounts(entry);
    var shownNet = voteState.baseline[entry.id] !== undefined ? voteState.baseline[entry.id] : counts.net;
    return '<li class="concept-proposal-row">' + voteControlsHtml(entry, voteState)
      + stateMark(entry.state)
      + '<span class="concept-proposal-kind">' + KIND_LABELS[entry.group] + "</span> "
      + '<a href="/proposals/#proposal-' + escapeHtml(entry.id) + '">' + escapeHtml(entry.title) + "</a> "
      + '<span class="concept-note">' + escapeHtml(pluralise(Math.round(shownNet * 10) / 10, "net vote", "net votes")) + "</span>"
      + '<p class="proposals-vote-note" role="status" aria-live="polite" data-proposal-note="' + escapeHtml(entry.id) + '"></p></li>';
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
    return settings.proposalVoting === true;
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
      var button = event.target.closest && event.target.closest("[data-proposal-vote]");
      if (!button || !container.contains(button) || button.disabled || voteState.busy) return;
      var proposalId = button.getAttribute("data-proposal-id");
      var direction = button.getAttribute("data-proposal-vote") === "up" ? 1 : -1;
      var previous = voteState.mine[proposalId] || 0;
      var next = previous === direction ? null : direction;
      voteState.busy = true;
      postVote(scope, proposalId, next).then(function (result) {
        voteState.busy = false;
        if (result.ok) {
          var entry = entriesById[proposalId];
          var base = voteState.baseline[proposalId] !== undefined ? voteState.baseline[proposalId] : voteCounts(entry).net;
          var reported = netFromResponse(result.body);
          voteState.baseline[proposalId] = reported !== null ? reported : base + (next || 0) - previous;
          voteState.mine[proposalId] = next || 0;
          rerender();
          return;
        }
        var failure = voteFailureText(result);
        var note = container.querySelector('[data-proposal-note="' + proposalId.replace(/"/g, "") + '"]');
        if (failure === "unsupported") {
          voteState.enabled = false;
          rerender();
          return;
        }
        if (!note) return;
        if (failure === "signed-out") note.innerHTML = signInNoteHtml();
        else note.textContent = failure;
      }).catch(function () {
        voteState.busy = false;
        var note = container.querySelector('[data-proposal-note="' + proposalId.replace(/"/g, "") + '"]');
        if (note) note.textContent = VOTE_FAILED_TEXT;
      });
    });
  }

  function mountQueue(section, entries, scope, voteState, now) {
    var viewState = { group: "stories", sort: "top" };
    if (!entriesInGroup(entries, "stories").length) {
      var firstFilled = GROUP_ORDER.filter(function (group) { return entriesInGroup(entries, group).length; })[0];
      if (firstFilled) viewState.group = firstFilled;
    }
    var entriesById = {};
    entries.forEach(function (entry) { entriesById[entry.id] = entry; });
    dropPlaceholderMarking(section);
    section.setAttribute("data-proposals-state", "live");
    function render() {
      var focused = scope.document.activeElement;
      var focusSelector = focused && focused.getAttribute && (focused.getAttribute("data-proposals-tab") ? '[data-proposals-tab="' + focused.getAttribute("data-proposals-tab") + '"]'
        : focused.getAttribute("data-proposals-sort") ? '[data-proposals-sort="' + focused.getAttribute("data-proposals-sort") + '"]'
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

  function fetchIndex(scope) {
    var settings = readSettings(scope);
    return scope.fetch(settings.base + INDEX_PATH, { credentials: "omit", cache: "no-cache" })
      .then(function (response) { return response.ok ? response.json() : null; })
      .then(normaliseEntries)
      .catch(function () { return []; });
  }

  function start(scope) {
    var mounts = scope.document.querySelectorAll("[data-proposals-live]");
    if (!mounts.length || typeof scope.fetch !== "function") return Promise.resolve();
    return fetchIndex(scope).then(function (entries) {
      if (!entries.length) return;
      var voteState = { enabled: votingEnabled(scope), mine: {}, baseline: {}, busy: false };
      var now = Date.now();
      Array.prototype.forEach.call(mounts, function (section) {
        var kind = section.getAttribute("data-proposals-live");
        if (kind === "queue") mountQueue(section, entries, scope, voteState, now);
        else if (kind === "home") mountHome(section, entries, scope, voteState);
        else if (kind === "concept") mountConcept(section, entries, scope, voteState);
      });
    });
  }

  return {
    normaliseEntries: normaliseEntries,
    sortEntries: sortEntries,
    entriesInGroup: entriesInGroup,
    steeringLeaders: steeringLeaders,
    touchesConcept: touchesConcept,
    formatNet: formatNet,
    ageText: ageText,
    decisionLineHtml: decisionLineHtml,
    stateMark: stateMark,
    provenanceLabel: provenanceLabel,
    queueHtml: queueHtml,
    start: start
  };
});
