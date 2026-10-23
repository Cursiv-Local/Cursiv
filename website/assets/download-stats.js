'use strict';
(() => {
  // Count explicit installer-link activations only, never visits to /start.
  // No cookies/storage/IDs. Navigation is never intercepted or delayed.
  function click(event) {
    if (navigator.globalPrivacyControl === true || navigator.doNotTrack === '1') return;
    if ((event.type === 'click' && event.button !== 0) || (event.type === 'auxclick' && event.button !== 1)) return;
    const link = event.target.closest?.('[data-download-button]');
    if (!link || !['windows', 'mac'].includes(link.dataset.downloadButton)) return;
    fetch('/api/download-click', { method: 'POST', credentials: 'omit', mode: 'same-origin', keepalive: true,
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ button: link.dataset.downloadButton }),
      referrerPolicy: 'no-referrer' }).catch(() => {});
  }
  document.addEventListener('click', click);
  document.addEventListener('auxclick', click);
})();
