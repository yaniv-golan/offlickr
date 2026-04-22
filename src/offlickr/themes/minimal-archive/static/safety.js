/* Client-side safe-only mode toggle for offlickr archives. */
(function () {
  var KEY = 'offlickr_safe_only';
  var safeOnly = localStorage.getItem(KEY) === '1';

  function applyMode() {
    document.body.classList.toggle('safe-only-mode', safeOnly);
    var btn = document.getElementById('safety-toggle');
    if (btn) {
      btn.textContent = safeOnly ? 'Show all' : 'Safe only';
      btn.setAttribute('aria-pressed', safeOnly ? 'true' : 'false');
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    applyMode();

    var btn = document.getElementById('safety-toggle');
    if (btn) {
      btn.addEventListener('click', function () {
        safeOnly = !safeOnly;
        localStorage.setItem(KEY, safeOnly ? '1' : '0');
        applyMode();
      });
    }

    /* Reveal individual veiled tiles on tombstone click */
    document.querySelectorAll('.tombstone').forEach(function (tombstone) {
      tombstone.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        var tile = tombstone.closest('.safety-veiled');
        if (tile) tile.classList.add('revealed');
      });
    });
  });
})();
