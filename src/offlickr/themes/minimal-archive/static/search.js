/* search.js — vanilla debounced client-side search */
(function () {
  'use strict';
  var input = document.getElementById('search-input');
  var results = document.getElementById('search-results');
  if (!input || !results) return;

  var index = null;
  var timer = null;

  function fold(s) {
    return s.normalize('NFC').toLowerCase();
  }

  function loadIndex() {
    if (index) return Promise.resolve(index);
    if (window.OFFLICKR_INDEX && window.OFFLICKR_INDEX.length) {
      index = window.OFFLICKR_INDEX;
      return Promise.resolve(index);
    }
    return fetch(OFFLICKR_BASE + 'assets/search.json')
      .then(function (r) { return r.json(); })
      .then(function (data) { index = data; return index; });
  }

  function doSearch(query) {
    var q = fold(query.trim());
    if (!q) { results.hidden = true; results.innerHTML = ''; return; }
    loadIndex().then(function (idx) {
      var hits = idx.filter(function (e) {
        return e.t.indexOf(q) >= 0
          || e.d.indexOf(q) >= 0
          || e.g.some(function (g) { return g.indexOf(q) >= 0; })
          || e.a.some(function (a) { return a.indexOf(q) >= 0; });
      }).slice(0, 12);
      results.innerHTML = '';
      hits.forEach(function (e) {
        var li = document.createElement('li');
        var a = document.createElement('a');
        a.href = OFFLICKR_BASE + (e.u || 'photo/' + e.id + '.html');
        a.textContent = e.t || '(untitled)';
        li.appendChild(a);
        results.appendChild(li);
      });
      results.hidden = hits.length === 0;
    });
  }

  input.addEventListener('input', function () {
    clearTimeout(timer);
    var val = this.value;
    timer = setTimeout(function () { doSearch(val); }, 180);
  });

  document.addEventListener('click', function (ev) {
    if (!results.contains(ev.target) && ev.target !== input) {
      results.hidden = true;
    }
  });
}());
