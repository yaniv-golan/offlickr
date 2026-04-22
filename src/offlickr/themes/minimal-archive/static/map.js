/* map.js — place dots on the inlined world SVG and handle hover/click */
(function () {
  'use strict';
  var tooltip = document.getElementById('map-tooltip');
  var dotsLayer = document.getElementById('photo-dots');
  if (!dotsLayer || !tooltip || !window.MAP_PHOTOS) return;

  var W = 960, H = 480;

  function project(lat, lng) {
    return {
      x: (lng + 180) / 360 * W,
      y: (90 - lat) / 180 * H
    };
  }

  MAP_PHOTOS.forEach(function (p) {
    var pos = project(p.lat, p.lng);
    var circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', pos.x.toFixed(2));
    circle.setAttribute('cy', pos.y.toFixed(2));
    circle.setAttribute('r', '3');
    circle.setAttribute('fill', '#0068a5');
    circle.setAttribute('fill-opacity', '0.7');
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
}());
