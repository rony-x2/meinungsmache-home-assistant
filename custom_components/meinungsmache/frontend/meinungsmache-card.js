/* Meinungsmache-Karte für das Home-Assistant-Dashboard.
 * Zeigt die neuesten Artikel eines oder mehrerer Feeds der Integration „Meinungsmache“.
 * Ohne Abhängigkeiten: eigenes Element mit Shadow DOM, Farben aus dem aktiven Theme. */

const VERSION = "0.1.0";
const AKZENT = "#C5A46D";

const TEXTE = {
  de: {
    titel: "Meinungsmache", leer: "Noch keine Artikel.", fehlt: "Entität nicht gefunden",
    exklusiv: "Exklusiv", eigen: "Eigener Artikel", von: "von", jetzt: "gerade eben",
    keine: "Bitte in der Karte einen Feed der Integration Meinungsmache wählen.",
    f_entities: "Feeds", f_titel: "Überschrift", f_anzahl: "Anzahl Artikel", f_bilder: "Bilder zeigen",
    f_teaser: "Anrisstext zeigen", f_nur: "Nur eigene Artikel",
    name: "Meinungsmache", beschreibung: "Die neuesten Artikel von meinungsmache.de",
  },
  en: {
    titel: "Meinungsmache", leer: "No articles yet.", fehlt: "Entity not found",
    exklusiv: "Exclusive", eigen: "Own article", von: "by", jetzt: "just now",
    keine: "Please choose a feed of the Meinungsmache integration in the card.",
    f_entities: "Feeds", f_titel: "Heading", f_anzahl: "Number of articles", f_bilder: "Show images",
    f_teaser: "Show teaser", f_nur: "Own articles only",
    name: "Meinungsmache", beschreibung: "The latest articles from meinungsmache.de",
  },
};

const sprache = (hass) => ((hass?.locale?.language || hass?.language || navigator.language || "de").startsWith("de") ? "de" : "en");
const text = (hass, schluessel) => TEXTE[sprache(hass)][schluessel];

const ZEICHEN = `<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><rect width="24" height="24" rx="5.5" fill="${AKZENT}"/>
<g fill="none" stroke="#1b1f27" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 5.5h12v13H6z"/><path d="M8.6 8.4h3.3v3.1H8.6zM14 8.6h1.6M14 11.3h1.6M8.6 14.6h6.9"/></g></svg>`;

const STIL = `
:host { --mm-akzent: ${AKZENT}; --mm-akzent-text: var(--mm-akzent-dunkel, #806333); }
ha-card { overflow: hidden; height: 100%; display: flex; flex-direction: column; }
.kopf { display: flex; align-items: center; gap: 10px; padding: 14px 16px 8px; }
.kopf svg { width: 28px; height: 28px; flex: none; }
.kopf h2 { margin: 0; font-size: var(--ha-card-header-font-size, 1.15rem); font-weight: 500; line-height: 1.25;
  color: var(--ha-card-header-color, var(--primary-text-color)); flex: 1; min-width: 0; }
.reiter { display: flex; gap: 6px; padding: 0 16px 8px; overflow-x: auto; scrollbar-width: none; }
.reiter::-webkit-scrollbar { display: none; }
.reiter button { font: inherit; font-size: .85rem; border: 1px solid var(--divider-color); background: none;
  color: var(--primary-text-color); border-radius: 999px; padding: 0 12px; min-height: 32px; cursor: pointer;
  white-space: nowrap; transition: background-color .2s, border-color .2s; }
.reiter button[aria-pressed="true"] { background: var(--mm-akzent); border-color: var(--mm-akzent); color: #1b1f27; }
.reiter button:focus-visible, a:focus-visible { outline: 2px solid var(--mm-akzent); outline-offset: 2px; }
ul { list-style: none; margin: 0; padding: 0 8px 8px; }
li + li { border-top: 1px solid var(--divider-color); }
a { display: flex; gap: 12px; padding: 10px 8px; color: inherit; text-decoration: none; border-radius: 10px;
  transition: background-color .2s; }
@media (hover: hover) { a:hover { background: var(--secondary-background-color); } }
.bild { flex: none; width: 72px; height: 72px; border-radius: 8px; object-fit: cover; background: var(--secondary-background-color); }
.inhalt { min-width: 0; flex: 1; display: flex; flex-direction: column; gap: 3px; }
.titel { font-weight: 500; line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.teaser { color: var(--secondary-text-color); font-size: .9rem; line-height: 1.35; display: -webkit-box; -webkit-line-clamp: 2;
  -webkit-box-orient: vertical; overflow: hidden; }
.meta { color: var(--secondary-text-color); font-size: .8rem; display: flex; flex-wrap: wrap; gap: 4px 8px; align-items: center; }
.marke { font-size: .7rem; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; border-radius: 4px; padding: 1px 6px;
  background: var(--mm-akzent); color: #1b1f27; }
.marke.eigen { background: none; color: var(--primary-text-color); border: 1px solid var(--mm-akzent); }
.hinweis { padding: 8px 16px 16px; color: var(--secondary-text-color); }
li.neu a { animation: mm-neu 2.4s ease-out; }
@keyframes mm-neu { from { background: color-mix(in srgb, var(--mm-akzent) 28%, transparent); } to { background: transparent; } }
@media (prefers-reduced-motion: reduce) { li.neu a { animation: none; } a, .reiter button { transition: none; } }
@media (max-width: 420px) { .bild { width: 60px; height: 60px; } a { gap: 10px; } }
`;

const maskiere = (wert) => String(wert ?? "").replace(/[&<>"']/g, (z) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[z]);
const sichereUrl = (url) => { try { const u = new URL(url, location.origin); return u.protocol === "https:" || u.protocol === "http:" ? u.href : ""; } catch { return ""; } };

function relativ(hass, iso) {
  if (!iso) return "";
  const zeit = new Date(iso);
  const sek = Math.round((zeit.getTime() - Date.now()) / 1000);
  const sp = hass?.locale?.language || sprache(hass);
  if (Math.abs(sek) < 60) return text(hass, "jetzt");
  const fmt = new Intl.RelativeTimeFormat(sp, { numeric: "auto" });
  for (const [einheit, s] of [["day", 86400], ["hour", 3600], ["minute", 60]]) {
    if (Math.abs(sek) >= s && (einheit !== "day" || Math.abs(sek) < 7 * 86400)) return fmt.format(Math.round(sek / s), einheit);
  }
  return zeit.toLocaleDateString(sp, { day: "numeric", month: "short", year: zeit.getFullYear() === new Date().getFullYear() ? undefined : "numeric" });
}

class MeinungsmacheCard extends HTMLElement {
  static getConfigForm() {
    return {
      schema: [
        { name: "entities", required: true, selector: { entity: { multiple: true, filter: { integration: "meinungsmache", domain: "sensor" } } } },
        { name: "titel", selector: { text: {} } },
        { type: "grid", name: "", schema: [
          { name: "anzahl", selector: { number: { min: 1, max: 30, mode: "box" } } },
          { name: "bilder", selector: { boolean: {} } },
          { name: "teaser", selector: { boolean: {} } },
          { name: "nur_eigene", selector: { boolean: {} } },
        ] },
      ],
      computeLabel: (s) => TEXTE[document.documentElement.lang?.startsWith("de") ? "de" : "en"]["f_" + (s.name === "nur_eigene" ? "nur" : s.name)] ?? s.name,
    };
  }

  static getStubConfig(hass) {
    const passend = Object.keys(hass.states).filter((e) => e.startsWith("sensor.meinungsmache_") && e.endsWith("_neuester_artikel"));
    const alle = passend.find((e) => e === "sensor.meinungsmache_all_neuester_artikel");
    return { entities: [alle || passend[0] || "sensor.meinungsmache_all_neuester_artikel"], anzahl: 5, bilder: true, teaser: false };
  }

  setConfig(config) {
    const roh = config.entities ?? (config.entity ? [config.entity] : []);
    if (!Array.isArray(roh)) throw new Error("entities muss eine Liste sein");
    // Wer den Zeit-Sensor oder das Ereignis eines Feeds wählt, bekommt dessen Artikelliste
    const entities = [...new Set(roh.map((e) => String(e)
      .replace(/^event\.(meinungsmache_.+)_neuer_artikel$/, "sensor.$1_neuester_artikel")
      .replace(/^sensor\.(meinungsmache_.+)_zuletzt_erschienen$/, "sensor.$1_neuester_artikel")))];
    this._config = { anzahl: 5, bilder: true, teaser: false, nur_eigene: false, ...config, entities };
    if (!this._aktiv || !entities.includes(this._aktiv)) this._aktiv = entities[0];
    this._fingerabdruck = null;
    this._bekannt = null;
    this._zeichne();
  }

  set hass(hass) {
    this._hass = hass;
    const abdruck = (this._config?.entities || []).map((e) => hass.states[e]?.last_updated).join("|") + "|" + sprache(hass);
    if (abdruck === this._fingerabdruck) return;
    this._fingerabdruck = abdruck;
    this._zeichne();
  }

  connectedCallback() {
    // Relative Zeiten einmal pro Minute auffrischen
    this._takt = setInterval(() => {
      this.shadowRoot?.querySelectorAll("time[datetime]").forEach((t) => { t.textContent = relativ(this._hass, t.getAttribute("datetime")); });
    }, 60000);
  }

  disconnectedCallback() { clearInterval(this._takt); }

  getCardSize() { return 1 + Math.min(this._config?.anzahl ?? 5, 30) * 2; }

  getGridOptions() { return { columns: 12, min_columns: 4, rows: "auto" }; }

  _zeichne() {
    if (!this._config) return;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.addEventListener("click", (e) => {
        const knopf = e.target.closest("button[data-entity]");
        if (!knopf) return;
        this._aktiv = knopf.dataset.entity;
        this._bekannt = null;
        this._zeichne();
      });
    }
    const hass = this._hass;
    const cfg = this._config;
    const reiter = cfg.entities.length > 1
      ? `<div class="reiter" role="group">${cfg.entities.map((e) => {
          const name = hass?.states[e]?.attributes.feed_name || e;
          return `<button type="button" data-entity="${maskiere(e)}" aria-pressed="${e === this._aktiv}">${maskiere(name)}</button>`;
        }).join("")}</div>`
      : "";

    let inhalt;
    const zustand = hass?.states[this._aktiv];
    if (!this._aktiv) inhalt = `<div class="hinweis">${text(hass, "keine")}</div>`;
    else if (!hass) inhalt = "";
    else if (!zustand) inhalt = `<div class="hinweis">${text(hass, "fehlt")}: ${maskiere(this._aktiv)}</div>`;
    else {
      let eintraege = zustand.attributes.eintraege || [];
      if (cfg.nur_eigene) eintraege = eintraege.filter((a) => a.eigen);
      eintraege = eintraege.slice(0, cfg.anzahl);
      const vorher = this._bekannt;
      this._bekannt = new Set(eintraege.map((a) => a.link));
      inhalt = eintraege.length
        ? `<ul>${eintraege.map((a) => this._eintrag(a, vorher && !vorher.has(a.link))).join("")}</ul>`
        : `<div class="hinweis">${text(hass, "leer")}</div>`;
    }
    const titel = cfg.titel ?? (cfg.entities.length === 1 && zustand ? `${text(hass, "titel")} · ${zustand.attributes.feed_name}` : text(hass, "titel"));
    this.shadowRoot.innerHTML = `<style>${STIL}</style><ha-card>
      <div class="kopf">${ZEICHEN}<h2>${maskiere(titel)}</h2></div>${reiter}${inhalt}</ha-card>`;
  }

  _eintrag(a, neu) {
    const hass = this._hass;
    const cfg = this._config;
    const link = sichereUrl(a.link);
    const bild = cfg.bilder && a.bild ? sichereUrl(a.bild) : "";
    const meta = [
      a.exklusiv ? `<span class="marke">${text(hass, "exklusiv")}</span>` : a.eigen ? `<span class="marke eigen">${text(hass, "eigen")}</span>` : "",
      a.veroeffentlicht ? `<time datetime="${maskiere(a.veroeffentlicht)}" title="${maskiere(new Date(a.veroeffentlicht).toLocaleString(hass?.locale?.language))}">${maskiere(relativ(hass, a.veroeffentlicht))}</time>` : "",
      a.autor ? `<span>${text(hass, "von")} ${maskiere(a.autor)}</span>` : "",
    ].filter(Boolean).join("");
    return `<li${neu ? ' class="neu"' : ""}><a href="${maskiere(link)}" target="_blank" rel="noopener noreferrer">
      ${bild ? `<img class="bild" src="${maskiere(bild)}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer">` : ""}
      <span class="inhalt"><span class="titel">${maskiere(a.titel)}</span>
      ${cfg.teaser && a.teaser ? `<span class="teaser">${maskiere(a.teaser)}</span>` : ""}
      ${meta ? `<span class="meta">${meta}</span>` : ""}</span></a></li>`;
  }
}

if (!customElements.get("meinungsmache-card")) {
  customElements.define("meinungsmache-card", MeinungsmacheCard);
  window.customCards = window.customCards || [];
  const de = (document.documentElement.lang || navigator.language || "de").startsWith("de");
  window.customCards.push({
    type: "meinungsmache-card",
    name: TEXTE[de ? "de" : "en"].name,
    description: TEXTE[de ? "de" : "en"].beschreibung,
    preview: true,
    documentationURL: "https://github.com/rony-x2/meinungsmache-home-assistant",
  });
  console.info(`%c MEINUNGSMACHE-KARTE %c ${VERSION} `, `background:${AKZENT};color:#1b1f27;font-weight:600`, "");
}
