'use strict';
(() => {
  const element = id => document.getElementById(id);
  const number = value => Number.isSafeInteger(value) && value >= 0 ? new Intl.NumberFormat().format(value) : 'Unavailable';
  const cell = (row, value, label) => {
    const td = document.createElement('td');
    td.textContent = value;
    td.dataset.label = label;
    row.appendChild(td);
  };
  fetch('/admin/downloads/data', { credentials: 'same-origin', cache: 'no-store', mode: 'same-origin', referrerPolicy: 'no-referrer' })
    .then(response => { if (!response.ok) throw new Error('Authentication or server unavailable'); return response.json(); })
    .then(data => {
      element('stats-status').textContent = data.available
        ? (data.status === 'fresh' ? 'GitHub metadata is current within the one-hour cache.' : `Showing cached metadata; refresh status: ${data.status}.`)
        : 'GitHub statistics are temporarily unavailable. No zero total is assumed.';
      element('stats-total').textContent = number(data.total);
      element('stats-latest').textContent = data.latest ? `${data.latest.tag}: ${number(data.latest.downloads)}` : 'No stable release or data unavailable';
      element('stats-excluded').textContent = number(data.excluded_downloads);
      element('stats-updated').textContent = data.updated_at ? new Date(data.updated_at).toLocaleString() : 'Unavailable';
      for (const release of data.releases || []) {
        const row = document.createElement('tr');
        cell(row, release.tag + (release.prerelease ? ' (prerelease)' : ''), 'Release');
        cell(row, number(release.downloads), 'Installer downloads');
        cell(row, release.assets.map(asset => `${asset.name}: ${number(asset.downloads)}`).join('; ') || 'None', 'Counted assets');
        cell(row, release.excluded_assets.map(asset => `${asset.name}: ${number(asset.downloads)}`).join('; ') || 'None', 'Excluded copies');
        element('stats-releases').appendChild(row);
      }
      const clicks = data.clicks;
      element('stats-clicks').textContent = !clicks?.available ? 'Click totals unavailable.'
        : `${clicks.enabled ? 'Recording enabled.' : 'Recording disabled; previously recorded totals retained.'} ` +
          (clicks.totals.length ? clicks.totals.map(row => `${row.button}: ${number(row.count)} clicks, recorded since ${row.started_day}`).join(' · ') : 'No clicks have been recorded.');
    })
    .catch(() => { element('stats-status').textContent = 'Statistics could not be loaded. Reopen this page to authenticate or try again later.'; element('stats-clicks').textContent = 'Click totals unavailable.'; });
})();
