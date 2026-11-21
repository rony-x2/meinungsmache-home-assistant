/* Meinungsmache für Home Assistant – Kopieren, Menü, Vorführung der Karte */
for (const b of document.querySelectorAll('[data-kopie]')) {
  b.addEventListener('click', async () => {
    const t = document.getElementById(b.dataset.kopie)?.textContent ?? '';
    const vorher = b.dataset.vorher ??= b.textContent;
    try { await navigator.clipboard.writeText(t); b.textContent = 'Kopiert'; setTimeout(() => { b.textContent = vorher; }, 1800); } catch {}
  });
}

// Menü auf dem Smartphone
(() => {
  const kopf = document.querySelector('.kopf'), knopf = kopf?.querySelector('.menue-knopf');
  if (!knopf) return;
  const setze = (auf) => { kopf.classList.toggle('offen', auf); knopf.setAttribute('aria-expanded', String(auf)); };
  knopf.addEventListener('click', () => {
    const auf = !kopf.classList.contains('offen');
    setze(auf);
    if (auf) kopf.querySelector('nav a')?.focus({ preventScroll: true });
  });
  kopf.querySelectorAll('nav a').forEach((a) => a.addEventListener('click', () => setze(false)));
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && kopf.classList.contains('offen')) { setze(false); knopf.focus(); } });
  document.addEventListener('click', (e) => { if (!kopf.contains(e.target)) setze(false); });
})();

/* Vorführung: die echte Karte der Integration mit einem nachgebildeten Home-Assistant-Zustand.
   Erst ohne den neuesten Artikel, dann „erscheint“ er: Die Karte hebt ihn hervor, die Mitteilung fährt ein. */
(() => {
  const karte = document.querySelector('meinungsmache-card[data-demo]');
  const mitteilung = document.querySelector('[data-mitteilung]');
  const nochmal = document.querySelector('.nochmal');
  if (!karte) return;
  const ruhig = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const ENTITAET = 'sensor.meinungsmache_all_neuester_artikel';
  let eintraege = [];
  try { eintraege = JSON.parse(document.getElementById('demo-daten').textContent || '[]'); } catch {}
  let zaehler = 0;

  const berlin = (t) => {   // „2026-11-21 18:00“ in deutscher Zeit -> ISO
    const roh = new Date(t.replace(' ', 'T') + 'Z');
    const teile = Object.fromEntries(new Intl.DateTimeFormat('en-US', { timeZone: 'Europe/Berlin', hourCycle: 'h23',
      year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).formatToParts(roh).map((p) => [p.type, p.value]));
    const versatz = Date.UTC(teile.year, teile.month - 1, teile.day, teile.hour, teile.minute) - roh.getTime();
    return new Date(roh.getTime() - versatz).toISOString();
  };
  const zustand = (liste) => ({
    states: { [ENTITAET]: { entity_id: ENTITAET, state: liste[0]?.titel ?? '', last_updated: String(++zaehler),
      attributes: { feed: 'all', feed_name: 'Alle Artikel', eintraege: liste } } },
    locale: { language: 'de' }, language: 'de',
  });
  const art = (a) => (a.exklusiv ? 'Exklusiv · Alle Artikel' : a.eigen ? `${a.autor} · Alle Artikel` : 'Meldung · Alle Artikel');

  const zeige = (liste) => { karte.hass = zustand(liste); };
  const ablauf = () => {
    if (!eintraege.length) return;
    mitteilung?.classList.remove('da');
    nochmal?.setAttribute('hidden', '');
    if (ruhig) { zeige(eintraege); mitteilung?.classList.add('da', 'ruhig'); return; }
    zeige(eintraege.slice(1));
    setTimeout(() => {
      zeige(eintraege);
      if (mitteilung) {
        mitteilung.querySelector('[data-m-titel]').textContent = eintraege[0].titel;
        mitteilung.querySelector('[data-m-unter]').textContent = art(eintraege[0]);
        mitteilung.classList.add('da');
      }
      setTimeout(() => nochmal?.removeAttribute('hidden'), 2500);
    }, 1800);
  };

  const start = () => {
    // aktueller Stand aus der Schnittstelle von „Rede mit Meinungsmache“ (gleicher Server); höchstens 1,5 s warten
    const holen = fetch('/meinungsmache/stand.php', { headers: { Accept: 'application/json' } })
      .then((r) => (r.ok ? r.json() : null)).then((d) => {
        if (!d || !Array.isArray(d.neueste) || !d.neueste.length) return;
        eintraege = d.neueste.map((a) => ({ titel: a.titel, link: a.url, veroeffentlicht: berlin(a.zeit), autor: a.art === 'eigen' ? a.von : null,
          eigen: a.art === 'eigen', exklusiv: /^\s*exklusiv\b/i.test(a.titel) }));
        const stand = document.querySelector('[data-demo-stand]');
        const m = /^(\d{4})-(\d{2})-(\d{2}) (\d{2}:\d{2})/.exec(d.letzter_abruf || d.bis || '');
        if (stand && m) stand.textContent = `${m[3]}.${m[2]}.${m[1]}, ${m[4]} Uhr`;
      }).catch(() => {});
    Promise.race([holen, new Promise((r) => setTimeout(r, 1500))]).then(ablauf);
  };
  nochmal?.addEventListener('click', ablauf);

  customElements.whenDefined('meinungsmache-card').then(() => {
    // gleich etwas zeigen; der neueste Artikel „erscheint“, sobald die Karte im Blick ist
    karte.setConfig({ entities: [ENTITAET], anzahl: 5, bilder: false, teaser: false });
    if (eintraege.length) zeige(ruhig ? eintraege : eintraege.slice(1));
    if (!('IntersectionObserver' in window) || ruhig) { start(); return; }
    const io = new IntersectionObserver((e) => { if (e[0].isIntersecting) { io.disconnect(); start(); } }, { threshold: 0.3 });
    io.observe(karte);
  });
})();
