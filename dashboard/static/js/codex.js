// Shared helpers used by every Codex page.
(function () {
  window.$ = (s, r = document) => r.querySelector(s);
  window.$$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  const toast = document.getElementById('toast');
  let timer;
  window.showToast = function (msg) {
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add('show');
    clearTimeout(timer);
    timer = setTimeout(() => toast.classList.remove('show'), 2200);
  };

  // Wire any element with [data-toast] to flash a stub toast on click.
  document.addEventListener('DOMContentLoaded', () => {
    $$('[data-toast]').forEach(el => {
      el.addEventListener('click', e => {
        e.preventDefault();
        showToast(el.dataset.toast);
      });
    });
  });
})();
