'use strict';
(() => {
  const counters = document.querySelectorAll('[data-download-count]');
  if (counters.length) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    fetch('/api/downloads', { credentials: 'omit', mode: 'same-origin', signal: controller.signal, referrerPolicy: 'no-referrer' })
      .then(response => { if (!response.ok) throw new Error('Unavailable'); return response.json(); })
      .then(data => {
        if (!data.available || !Number.isSafeInteger(data.total) || data.total < 0) throw new Error('Unavailable');
        const count = new Intl.NumberFormat().format(data.total);
        for (const counter of counters) {
          counter.textContent = `${count} versioned installer downloads on GitHub${data.status === 'fresh' ? '' : ' (cached)'}`;
          counter.title = `Canonical installer assets only. Last checked: ${data.updated_at || 'unavailable'}. Download requests, not confirmed completed transfers.`;
        }
      })
      .catch(() => { for (const counter of counters) counter.textContent = 'GitHub download count temporarily unavailable.'; })
      .finally(() => clearTimeout(timer));
  }

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
