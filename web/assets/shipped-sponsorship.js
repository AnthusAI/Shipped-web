(function () {
  var VISIBLE_RATIO = 0.5;
  var VISIBLE_MILLISECONDS = 1000;
  var UNIT_SELECTOR = '[data-sponsor-unit]';
  var LINK_SELECTOR = 'a[data-sponsor-action]';

  function sendEvent(eventName, fields) {
    if (typeof window.gtag === 'function') {
      window.gtag('event', eventName, fields);
    }
  }

  function promotionFields(unit) {
    return {
      promotion_id: unit.getAttribute('data-sponsor-id'),
      promotion_name: unit.getAttribute('data-sponsor-name'),
      creative_name: unit.getAttribute('data-sponsor-unit'),
      creative_slot: unit.getAttribute('data-sponsor-slot'),
      page_type: unit.getAttribute('data-sponsor-page-type'),
      sponsor_topic: unit.getAttribute('data-sponsor-topic'),
      match_kind: unit.getAttribute('data-sponsor-match')
    };
  }

  function isMostlyVisible(entry) {
    return entry.isIntersecting && entry.intersectionRatio >= VISIBLE_RATIO;
  }

  function watchViews(units) {
    if (typeof window.IntersectionObserver !== 'function') {
      return;
    }
    var pendingTimers = new Map();
    var observer = new window.IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          var unit = entry.target;
          if (isMostlyVisible(entry)) {
            if (!pendingTimers.has(unit)) {
              pendingTimers.set(
                unit,
                window.setTimeout(function () {
                  pendingTimers.delete(unit);
                  observer.unobserve(unit);
                  sendEvent('view_promotion', promotionFields(unit));
                }, VISIBLE_MILLISECONDS)
              );
            }
          } else if (pendingTimers.has(unit)) {
            window.clearTimeout(pendingTimers.get(unit));
            pendingTimers.delete(unit);
          }
        });
      },
      { threshold: [0, VISIBLE_RATIO, 1] }
    );
    units.forEach(function (unit) {
      observer.observe(unit);
    });
  }

  function watchClicks() {
    document.addEventListener('click', function (event) {
      var link = event.target instanceof Element ? event.target.closest(LINK_SELECTOR) : null;
      var unit = link ? link.closest(UNIT_SELECTOR) : null;
      if (!unit) {
        return;
      }
      var fields = promotionFields(unit);
      fields.sponsor_action = link.getAttribute('data-sponsor-action');
      sendEvent('select_promotion', fields);
    });
  }

  function start() {
    watchViews(Array.prototype.slice.call(document.querySelectorAll(UNIT_SELECTOR)));
    watchClicks();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
