/* map.js — place dots on the inlined world SVG, cluster dense areas */
(function () {
  'use strict';
  var tooltip = document.getElementById('map-tooltip');
  var dotsLayer = document.getElementById('photo-dots');
  if (!dotsLayer || !tooltip || !window.MAP_PHOTOS) return;

  var W = 960, H = 480;
  var CLUSTER_RADIUS = 16;  // SVG units — dots within this distance are clustered
  var CLUSTER_MIN = 15;     // minimum photos to form a cluster pill

  function project(lat, lng) {
    return {
      x: (lng + 180) / 360 * W,
      y: (90 - lat) / 180 * H
    };
  }

  function dist(a, b) {
    var dx = a.x - b.x, dy = a.y - b.y;
    return Math.sqrt(dx * dx + dy * dy);
  }

  // Project all photos
  var items = MAP_PHOTOS.map(function (p) {
    var pos = project(p.lat, p.lng);
    return { id: p.id, title: p.title, lat: p.lat, lng: p.lng, x: pos.x, y: pos.y, used: false };
  });

  // Greedy clustering
  var clusters = [];
  for (var i = 0; i < items.length; i++) {
    if (items[i].used) continue;
    var seed = items[i];
    var members = [seed];
    seed.used = true;
    for (var j = i + 1; j < items.length; j++) {
      if (!items[j].used && dist(seed, items[j]) < CLUSTER_RADIUS) {
        members.push(items[j]);
        items[j].used = true;
      }
    }
    var cx = members.reduce(function (s, m) { return s + m.x; }, 0) / members.length;
    var cy = members.reduce(function (s, m) { return s + m.y; }, 0) / members.length;
    clusters.push({ members: members, x: cx, y: cy });
  }

  var ns = 'http://www.w3.org/2000/svg';

  clusters.forEach(function (cl) {
    if (cl.members.length >= CLUSTER_MIN) {
      // Cluster pill
      var g = document.createElementNS(ns, 'g');
      g.setAttribute('style', 'cursor:pointer');
      var label = String(cl.members.length);
      var rx = 10, ry = 7;
      var pill = document.createElementNS(ns, 'rect');
      pill.setAttribute('x', (cl.x - rx).toFixed(1));
      pill.setAttribute('y', (cl.y - ry).toFixed(1));
      pill.setAttribute('width', (rx * 2).toFixed(1));
      pill.setAttribute('height', (ry * 2).toFixed(1));
      pill.setAttribute('rx', ry.toFixed(1));
      pill.setAttribute('fill', 'var(--fg, #111)');
      var txt = document.createElementNS(ns, 'text');
      txt.setAttribute('x', cl.x.toFixed(1));
      txt.setAttribute('y', (cl.y + 3.5).toFixed(1));
      txt.setAttribute('text-anchor', 'middle');
      txt.setAttribute('font-size', '9');
      txt.setAttribute('font-family', 'ui-monospace,monospace');
      txt.setAttribute('fill', 'var(--bg, #fff)');
      txt.setAttribute('pointer-events', 'none');
      txt.textContent = label;
      g.appendChild(pill);
      g.appendChild(txt);
      g.addEventListener('mouseenter', function (ev) {
        var titles = cl.members.slice(0, 5).map(function (m) { return m.title; });
        if (cl.members.length > 5) titles.push('…');
        tooltip.textContent = cl.members.length + ' photos — ' + titles.join(', ');
        tooltip.hidden = false;
        tooltip.style.left = (ev.clientX + 12) + 'px';
        tooltip.style.top = (ev.clientY - 28) + 'px';
      });
      g.addEventListener('mouseleave', function () { tooltip.hidden = true; });
      dotsLayer.appendChild(g);
    } else {
      // Individual dots
      cl.members.forEach(function (p) {
        var circle = document.createElementNS(ns, 'circle');
        circle.setAttribute('cx', p.x.toFixed(2));
        circle.setAttribute('cy', p.y.toFixed(2));
        circle.setAttribute('r', '3');
        circle.setAttribute('fill', 'var(--fg, #111)');
        circle.setAttribute('fill-opacity', '1');
        circle.setAttribute('style', 'cursor:pointer');
        circle.addEventListener('mouseenter', function (ev) {
          tooltip.textContent = p.title;
          tooltip.hidden = false;
          tooltip.style.left = (ev.clientX + 12) + 'px';
          tooltip.style.top = (ev.clientY - 28) + 'px';
        });
        circle.addEventListener('mouseleave', function () { tooltip.hidden = true; });
        circle.addEventListener('click', function () {
          window.location.href = MAP_BASE + 'photo/' + p.id + '.html';
        });
        dotsLayer.appendChild(circle);
      });
    }
  });
}());
