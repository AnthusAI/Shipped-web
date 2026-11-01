(function (globalScope, buildModule) {
  var moduleApi = buildModule();
  if (typeof module === "object" && module.exports) module.exports = moduleApi;
  if (typeof document !== "undefined") {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { moduleApi.start(globalScope); });
    else moduleApi.start(globalScope);
  }
})(typeof window !== "undefined" ? window : this, function () {
  "use strict";

  var STORAGE_KEY = "shipped-own-submissions";
  var REMEMBERED_LIMIT = 5;
  var SUBMITTED_EVENT = "papyrus-reader:submitted";
  var SUBJECT_PATTERN = /^sub-[0-9a-f]{24}$/;
  var FIELD_MAXIMUM_LENGTH = 120;
  var FIELDS = [
    { key: "model", label: "Model", chip: "model" },
    { key: "maker", label: "Maker", chip: "maker" },
    { key: "task", label: "Task", chip: "task" }
  ];
  var FAILURE_WORDS = {
    http_4xx: "the page answered with an error",
    not_public: "the page is not public",
    unreadable: "the page could not be read",
    dns: "the site's address did not resolve",
    tls: "the site's certificate failed",
    blocked: "the site blocked the reader",
    too_large: "the page is too large",
    no_text: "the page has no text to read",
    empty_answer: "it found no model, maker or task"
  };
  var ERROR_WORDS = {
    extraction_not_ready: "AI has not read this link yet. Try again after it has.",
    nothing_to_confirm: "There is nothing to confirm. Use Fix to fill it in.",
    reader_limited: "Your account can't confirm right now.",
    reader_banned: "Your account can't confirm.",
    unknown_submission: "That submission is no longer yours to confirm, or it was hidden."
  };

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function validSubject(subject) {
    return typeof subject === "string" && SUBJECT_PATTERN.test(subject);
  }

  function readSettings(scope) {
    return Object.assign({ api: "/api/reader" }, (scope && scope.papyrusReader) || {});
  }

  function readRemembered(scope) {
    try {
      var stored = JSON.parse(scope.localStorage.getItem(STORAGE_KEY) || "[]");
      return Array.isArray(stored) ? stored.filter(function (entry) { return entry && validSubject(entry.subject); }) : [];
    } catch (error) {
      return [];
    }
  }

  function writeRemembered(scope, entries) {
    try {
      scope.localStorage.setItem(STORAGE_KEY, JSON.stringify(entries.slice(0, REMEMBERED_LIMIT)));
    } catch (error) {
      return;
    }
  }

  function remember(entries, submission) {
    if (!submission || !validSubject(submission.subject)) return entries;
    var kept = entries.filter(function (entry) { return entry.subject !== submission.subject; });
    return [{ subject: submission.subject, title: String(submission.title || "") }].concat(kept).slice(0, REMEMBERED_LIMIT);
  }

  function forget(entries, subject) {
    return entries.filter(function (entry) { return entry.subject !== subject; });
  }

  function failureText(reason) {
    return FAILURE_WORDS[reason] || "the page could not be read";
  }

  function errorText(answer) {
    var code = answer && answer.body && answer.body.error;
    if (ERROR_WORDS[code]) return ERROR_WORDS[code];
    if (answer && answer.status === 401) return "Sign in again to confirm.";
    if (answer && answer.status === 429) return "Too many answers this hour. Try again later.";
    if (answer && answer.status === 422) return "Each name can be at most " + FIELD_MAXIMUM_LENGTH + " characters, with no email address.";
    return "That didn't save. Try again.";
  }

  function dateText(stamp) {
    var parsed = new Date(stamp);
    if (isNaN(parsed.getTime())) return "";
    var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    return parsed.getUTCDate() + " " + months[parsed.getUTCMonth()] + " " + parsed.getUTCFullYear();
  }

  function shownValues(record) {
    var source = record.confirmation || (record.extraction && record.extraction.state === "extracted" ? record.extraction : null);
    var values = {};
    FIELDS.forEach(function (field) { values[field.key] = source ? source[field.key] || null : null; });
    return values;
  }

  function chipHtml(field, value) {
    if (!value || !value.name) return '<span class="extraction-none">None found</span>';
    if (value.match) {
      return '<span class="entity-chip entity-chip-confirmed"><i>' + field.chip + "</i>" + escapeHtml(value.name) + "</span>";
    }
    return '<span class="entity-chip entity-chip-proposed"><i>' + field.chip + "</i>" + escapeHtml(value.name) + " · new to the map</span>";
  }

  function statusHtml(record) {
    var extraction = record.extraction || {};
    if (record.confirmation) {
      var word = record.confirmation.status === "corrected" ? "You fixed this" : "You confirmed this";
      var on = dateText(record.confirmation.at);
      return '<p class="extraction-status"><span class="extraction-mark" aria-hidden="true">&#10003;</span>' + word + (on ? " on " + escapeHtml(on) : "") + ". You can change it.</p>";
    }
    if (extraction.state === "pending") {
      return '<p class="extraction-status"><span class="extraction-mark" aria-hidden="true">&#8987;</span>Waiting for AI to read this link. This page shows what it finds.</p>';
    }
    if (extraction.state === "failed") {
      return '<p class="extraction-status"><span class="extraction-mark" aria-hidden="true">&#33;</span>AI couldn’t read this link: ' + escapeHtml(failureText(extraction.reason)) + ". Use Fix to fill in what you know.</p>";
    }
    var known = extraction.knownReference ? " This link is already among the sources the map reads." : "";
    return '<p class="extraction-status"><span class="extraction-mark" aria-hidden="true">?</span>Is this right?' + known + "</p>";
  }

  function actionsHtml(record) {
    var extraction = record.extraction || {};
    if (extraction.state === "pending") return "";
    var confirm = extraction.state === "extracted" && !(record.confirmation && record.confirmation.status === "confirmed")
      ? '<button type="button" class="tag-action" data-extraction-confirm>Looks right</button>' : "";
    return '<div class="extraction-actions">' + confirm + '<button type="button" class="tag-action" data-extraction-fix aria-expanded="false">Fix</button></div>';
  }

  function fixFormHtml(record, values) {
    var inputs = FIELDS.map(function (field) {
      var id = "extraction-" + record.subject + "-" + field.key;
      var current = values[field.key] && values[field.key].name ? values[field.key].name : "";
      return '<label class="extraction-field" for="' + id + '"><span class="kicker">' + field.label + "</span>" +
        '<input id="' + id + '" name="' + field.key + '" type="text" maxlength="' + FIELD_MAXIMUM_LENGTH + '" value="' + escapeHtml(current) + '"></label>';
    }).join("");
    return '<form class="extraction-fix" data-extraction-form hidden>' + inputs +
      '<p class="field-hint">Leave a box empty if the link has none.</p>' +
      '<button type="submit" class="tag-action">Save fix</button></form>';
  }

  function recordHtml(record) {
    var values = shownValues(record);
    var extraction = record.extraction || {};
    var rows = extraction.state === "pending" && !record.confirmation ? "" : '<div class="tag-table">' + FIELDS.map(function (field) {
      return '<div class="tag-row"><span class="kicker">' + field.label + '</span><span class="tag-chips">' + chipHtml(field, values[field.key]) + "</span></div>";
    }).join("") + "</div>";
    var title = record.title || record.url || "Your link";
    return '<article class="extraction-record" data-extraction-subject="' + escapeHtml(record.subject) + '">' +
      '<p class="extraction-title"><b>' + escapeHtml(title) + "</b></p>" + statusHtml(record) + rows + actionsHtml(record) +
      (extraction.state === "pending" ? "" : fixFormHtml(record, values)) + '<p class="extraction-note" role="status"></p></article>';
  }

  function correctionBody(subject, formValues) {
    var body = { subject: subject, decision: "correct" };
    FIELDS.forEach(function (field) {
      var value = String(formValues[field.key] == null ? "" : formValues[field.key]).trim();
      body[field.key] = value ? value.slice(0, FIELD_MAXIMUM_LENGTH) : null;
    });
    return body;
  }

  function request(scope, path, options) {
    return scope.fetch(readSettings(scope).api + path, Object.assign({ credentials: "same-origin", cache: "no-store" }, options || {}))
      .then(function (response) {
        return response.json().catch(function () { return {}; }).then(function (body) {
          return { ok: response.ok, status: response.status, body: body };
        });
      });
  }

  function readExtraction(scope, subject) {
    return request(scope, "/extraction?subject=" + encodeURIComponent(subject), { headers: { accept: "application/json" } });
  }

  function sendConfirmation(scope, body) {
    return request(scope, "/extraction/confirm", {
      method: "POST",
      headers: { "content-type": "application/json", accept: "application/json" },
      body: JSON.stringify(body)
    });
  }

  function dropPlaceholderMarking(section) {
    section.classList.remove("is-placeholder");
    Array.prototype.forEach.call(section.querySelectorAll(".placeholder-tag"), function (tag) { tag.parentNode.removeChild(tag); });
  }

  function liveIntroHtml() {
    return '<p class="field-hint">After you send a link, AI reads it and pulls out the model, the maker and the task. Confirm them or fix them. ' +
      "Only you see this. A name marked “new to the map” is one the map doesn’t know yet.</p>";
  }

  function bindRecord(scope, container, record) {
    var article = container.querySelector('[data-extraction-subject="' + record.subject + '"]');
    if (!article) return;
    var note = article.querySelector(".extraction-note");
    var form = article.querySelector("[data-extraction-form]");
    var fix = article.querySelector("[data-extraction-fix]");
    var confirm = article.querySelector("[data-extraction-confirm]");
    function settle(answer) {
      if (answer.ok && answer.body && answer.body.subject === record.subject) {
        var updated = answer.body;
        article.outerHTML = recordHtml(updated);
        bindRecord(scope, container, updated);
        var fresh = container.querySelector('[data-extraction-subject="' + record.subject + '"] .extraction-note');
        if (fresh) fresh.textContent = "Saved. Thank you.";
      } else {
        note.textContent = errorText(answer);
      }
    }
    if (confirm) {
      confirm.addEventListener("click", function () {
        confirm.disabled = true;
        sendConfirmation(scope, { subject: record.subject, decision: "confirm" }).then(settle)
          .catch(function () { note.textContent = errorText(null); })
          .then(function () { confirm.disabled = false; });
      });
    }
    if (fix && form) {
      fix.addEventListener("click", function () {
        var opening = form.hidden;
        form.hidden = !opening;
        fix.setAttribute("aria-expanded", opening ? "true" : "false");
        if (opening) {
          var first = form.querySelector("input");
          if (first) first.focus();
        }
      });
      form.addEventListener("submit", function (event) {
        event.preventDefault();
        var formValues = {};
        FIELDS.forEach(function (field) { formValues[field.key] = form.elements[field.key].value; });
        sendConfirmation(scope, correctionBody(record.subject, formValues)).then(settle)
          .catch(function () { note.textContent = errorText(null); });
      });
    }
  }

  function render(scope, section, records) {
    var container = section.querySelector("[data-extraction-records]");
    if (!records.length || !container) return;
    dropPlaceholderMarking(section);
    Array.prototype.forEach.call(section.querySelectorAll("[data-extraction-sample]"), function (sample) { sample.parentNode.removeChild(sample); });
    container.innerHTML = liveIntroHtml() + records.map(recordHtml).join("");
    records.forEach(function (record) { bindRecord(scope, container, record); });
  }

  function load(scope, section) {
    var remembered = readRemembered(scope);
    if (!remembered.length) return Promise.resolve([]);
    return Promise.all(remembered.map(function (entry) {
      return readExtraction(scope, entry.subject).then(function (answer) {
        return { entry: entry, answer: answer };
      }).catch(function () { return { entry: entry, answer: null }; });
    })).then(function (results) {
      var kept = remembered;
      var records = [];
      results.forEach(function (result) {
        if (result.answer && result.answer.status === 404) kept = forget(kept, result.entry.subject);
        else if (result.answer && result.answer.ok && result.answer.body && result.answer.body.subject === result.entry.subject) records.push(result.answer.body);
      });
      if (kept.length !== remembered.length) writeRemembered(scope, kept);
      render(scope, section, records);
      return records;
    });
  }

  function start(scope) {
    var section = scope.document && scope.document.querySelector("[data-extraction-live]");
    if (!section || typeof scope.fetch !== "function") return Promise.resolve([]);
    scope.document.addEventListener(SUBMITTED_EVENT, function (event) {
      writeRemembered(scope, remember(readRemembered(scope), event && event.detail));
      load(scope, section);
    });
    return load(scope, section);
  }

  return {
    STORAGE_KEY: STORAGE_KEY,
    SUBMITTED_EVENT: SUBMITTED_EVENT,
    validSubject: validSubject,
    remember: remember,
    forget: forget,
    failureText: failureText,
    errorText: errorText,
    shownValues: shownValues,
    recordHtml: recordHtml,
    correctionBody: correctionBody,
    load: load,
    start: start
  };
});
