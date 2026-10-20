// Shows what is already booked on the chosen day while filling in the event form.
(function () {
  var input = document.querySelector('input[data-day-check]');
  var box = document.getElementById('day-check');
  if (!input || !box) return;
  var url = box.dataset.url;
  var exclude = box.dataset.exclude || '';
  var t = JSON.parse(document.getElementById('day-check-text').textContent);

  function render(data) {
    if (!data.ok) { box.innerHTML = ''; return; }
    var list = data.events.map(function (e) {
      return '<li>' + e.time + ' — ' + escapeHtml(e.title) + ' (' + escapeHtml(e.church) + ')</li>';
    }).join('');
    var cls = data.full ? 'error' : (data.count ? 'warning' : 'success');
    var head = data.full ? t.full : (data.count ? t.some.replace('{n}', data.count).replace('{limit}', data.limit) : t.free);
    box.innerHTML = '<div class="msg ' + cls + '"><strong>' + head + '</strong>' + (list ? '<ul>' + list + '</ul>' : '') + '</div>';
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function check() {
    if (!input.value) { box.innerHTML = ''; return; }
    fetch(url + '?date=' + encodeURIComponent(input.value) + '&exclude=' + exclude, { credentials: 'same-origin' })
      .then(function (r) { return r.json(); }).then(render).catch(function () { box.innerHTML = ''; });
  }
  input.addEventListener('change', check);
  check();
})();

// "Are you sure?" on buttons marked data-confirm.
document.addEventListener('submit', function (e) {
  var btn = e.submitter;
  var msg = (btn && btn.dataset.confirm) || e.target.dataset.confirm;
  if (msg && !window.confirm(msg)) e.preventDefault();
});

// Show the "what help do you need" box only when the checkbox is ticked.
(function () {
  var cb = document.getElementById('id_needs_support');
  var notes = document.getElementById('id_support_notes');
  if (!cb || !notes) return;
  var wrap = notes.closest('.field');
  function sync() { wrap.style.display = cb.checked ? '' : 'none'; }
  cb.addEventListener('change', sync);
  sync();
})();

// Upcoming-events slideshow: arrows, dots, auto-advance (pauses while someone is touching it).
(function () {
  var box = document.querySelector('.upcoming');
  if (!box) return;
  var track = box.querySelector('.slides');
  var slides = track ? track.querySelectorAll('.slide') : [];
  var dots = box.querySelectorAll('.slide-dots button');
  var index = 0, paused = false;

  function go(i) {
    if (!slides.length) return;
    index = (i + slides.length) % slides.length;
    track.scrollTo({ left: slides[index].offsetLeft - track.offsetLeft, behavior: 'smooth' });
    mark();
  }
  function mark() {
    dots.forEach(function (d, i) { d.classList.toggle('on', i === index); });
  }
  if (slides.length > 1) {
    box.querySelector('.slide-prev').addEventListener('click', function () { go(index - 1); });
    box.querySelector('.slide-next').addEventListener('click', function () { go(index + 1); });
    dots.forEach(function (d, i) { d.addEventListener('click', function () { go(i); }); });
    track.addEventListener('scroll', function () {
      var i = Math.round(track.scrollLeft / track.clientWidth);
      if (i !== index) { index = i; mark(); }
    }, { passive: true });
    ['mouseenter', 'touchstart', 'focusin'].forEach(function (ev) {
      track.addEventListener(ev, function () { paused = true; }, { passive: true });
    });
    ['mouseleave', 'touchend', 'focusout'].forEach(function (ev) {
      track.addEventListener(ev, function () { setTimeout(function () { paused = false; }, 4000); }, { passive: true });
    });
    setInterval(function () { if (!paused && !document.hidden) go(index + 1); }, 7000);
    mark();
  }

  // Reload now and then so statuses and new events show up without pressing refresh.
  var seconds = parseInt(box.dataset.autorefresh || '0', 10);
  if (seconds > 0) {
    setInterval(function () {
      if (!document.hidden && !paused) window.location.reload();
    }, seconds * 1000);
  }
})();

// Let phones install the app and open it from the home screen.
if ('serviceWorker' in navigator && window.isSecureContext) {
  window.addEventListener('load', function () {
    navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(function () {});
  });
}

// "Copy link" buttons.
document.addEventListener('click', function (e) {
  var btn = e.target.closest('[data-copy]');
  if (!btn) return;
  var text = btn.dataset.copy;
  var done = function () {
    var old = btn.innerHTML;
    btn.textContent = btn.dataset.copied || '✓';
    setTimeout(function () { btn.innerHTML = old; }, 2000);
  };
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(done, function () { window.prompt('', text); });
  } else {
    window.prompt('', text);
  }
});
