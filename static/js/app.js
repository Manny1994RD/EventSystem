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
