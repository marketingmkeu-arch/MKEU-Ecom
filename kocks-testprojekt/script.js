/* =====================================================================
   Baut die Seite aus den Texten in content.js zusammen.
   Normalerweise musst du hier nichts ändern – Texte stehen in content.js,
   Farben & Schriften oben in style.css.
   ===================================================================== */

(function () {
  const S = window.SEITE;
  const app = document.getElementById("app");
  document.title = S.seitenTitel || "";

  const an = (abschnitt) => abschnitt && abschnitt.anzeigen !== false;
  const wenn = (wert, html) => (wert ? html : "");

  // Bild oder Platzhalter
  function bild(src, alt, klasse = "") {
    if (src) return `<img class="${klasse}" src="${src}" alt="${alt || ""}" loading="lazy">`;
    return `<div class="platzhalter ${klasse}"><span>Bild-Platzhalter</span></div>`;
  }

  function logo(dunkel) {
    if (S.logo.bild) return `<img class="logo-bild" src="${S.logo.bild}" alt="${S.logo.text}">`;
    return `<span class="logo ${dunkel ? "logo--dunkel" : ""}">
      <svg class="logo-icon" viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="16" fill="none" stroke="currentColor" stroke-width="6"/></svg>
      <span class="logo-text">${S.logo.text}</span></span>`;
  }

  const pfeil = `<svg class="pfeil" viewBox="0 0 72 10" aria-hidden="true"><path d="M0 5h66" stroke="currentColor" stroke-width="2"/><path d="M64 1l7 4-7 4z" fill="currentColor"/></svg>`;

  const icons = {
    mail: `<svg viewBox="0 0 24 24"><path fill="currentColor" d="M3 5h18a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1zm.5 2.2v.3L12 13l8.5-5.5v-.3z"/></svg>`,
    telefon: `<svg viewBox="0 0 24 24"><path fill="currentColor" d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25 11.4 11.4 0 0 0 3.6.57 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.45.57 3.57a1 1 0 0 1-.25 1z"/></svg>`,
    linkedin: `<svg viewBox="0 0 24 24"><rect width="24" height="24" rx="4" fill="currentColor"/><path fill="var(--navy-hell)" d="M6.5 9.5h2.6V18H6.5zM7.8 5.5a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3zM10.8 9.5h2.5v1.2c.4-.7 1.3-1.4 2.6-1.4 2.7 0 3.2 1.8 3.2 4.1V18h-2.6v-4c0-1 0-2.2-1.4-2.2s-1.6 1-1.6 2.1V18h-2.6z"/></svg>`,
    zeitung: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="4" width="15" height="16" rx="1"/><path d="M18 8h3v11a1 1 0 0 1-2 0V8M6 8h4v4H6zM12 8h3M12 11h3M6 15h9M6 17.5h9"/></svg>`
  };

  let html = "";

  /* ---------- Header + Menü ---------- */
  html += `
  <header class="kopf">
    <a href="#" class="kopf-logo">${logo(false)}</a>
    <button class="burger" aria-label="Menü öffnen"><span></span><span></span><span></span></button>
  </header>
  <nav class="menue" aria-hidden="true">
    <div class="menue-kopf">${logo(false)}<button class="menue-zu" aria-label="Menü schließen">&times;</button></div>
    ${S.menue.map(g => `
      <div class="menue-gruppe">
        <a href="#" class="menue-titel">${g.titel}</a>
        ${g.links.map(l => `<a href="#">${l}</a>`).join("")}
      </div>`).join("")}
  </nav>`;

  /* ---------- Hero ---------- */
  const h = S.hero;
  if (an(h)) html += `
  <section class="hero" ${h.bild ? `style="background-image:linear-gradient(90deg,rgba(13,34,64,.95),rgba(13,34,64,.55)),url('${h.bild}')"` : ""}>
    <div class="hero-inhalt">
      ${wenn(h.marke, `<div class="hero-marke">${h.marke}</div>`)}
      <h1 class="hero-titel">${h.zeile1}<br>${h.zeile2} <span class="gold">${h.zeile2Gold}</span></h1>
      ${wenn(h.text, `<p class="hero-text">${h.text}</p>`)}
    </div>
    ${wenn(h.reiter && h.reiter.length, `
    <div class="hero-reiter">
      ${h.reiter.map(r => `<a href="#" class="reiter"><span class="reiter-linie"></span><span class="reiter-text">${r}</span></a>`).join("")}
    </div>`)}
  </section>`;

  /* ---------- Zahlen ---------- */
  if (an(S.zahlen)) html += `
  <section class="zahlen">
    ${S.zahlen.eintraege.map(z => `<div class="zahl"><strong>${z.zahl}</strong><span>${z.einheit}</span></div>`).join("")}
  </section>`;

  /* ---------- Intro ---------- */
  const i = S.intro;
  if (an(i)) html += `
  <section class="intro">
    <div class="container">
      <h2 class="titel">${i.ueberschrift}</h2>
      <div class="intro-raster">
        <a class="video" ${i.videoLink ? `href="${i.videoLink}" target="_blank" rel="noopener"` : ""}>
          ${i.videoBild ? bild(i.videoBild, "Video") : `<div class="video-flaeche">${logo(false)}<small>${i.videoUntertitel}</small></div>`}
          <span class="play"></span>
        </a>
        <div>
          ${wenn(i.lead, `<p class="lead">${i.lead}</p>`)}
          ${i.absaetze.map(p => `<p class="text">${p}</p>`).join("")}
        </div>
      </div>
    </div>
  </section>`;

  /* ---------- Banner ---------- */
  const b = S.banner;
  if (an(b)) html += `
  <section class="banner">
    <div class="banner-inhalt">
      <div>
        <div class="banner-titel"><span class="gold">${b.titelGold}</span> ${b.titelWeiss}</div>
        ${wenn(b.textGold, `<p class="banner-gold">${b.textGold}</p>`)}
        ${wenn(b.text, `<p class="banner-text">${b.text}</p>`)}
      </div>
      <span class="banner-linie"></span>
      <div class="banner-bild">${bild(b.bild, "Magazin")}</div>
    </div>
  </section>`;

  /* ---------- Karten (News / Experten) ---------- */
  function karte(k, linkText) {
    return `
    <a class="karte karte--${k.farbe === "gold" ? "gold" : "blau"}" href="${k.link || "#"}">
      <div class="karte-bild">${bild(k.bild, k.titel)}</div>
      <div class="karte-text">
        ${wenn(k.datum, `<div class="karte-meta">${k.datum}</div>`)}
        ${wenn(k.kategorie, `<div class="karte-meta">${k.kategorie}</div>`)}
        <h3>${k.titel}</h3>
        <span class="mehr">${linkText} ${pfeil}</span>
      </div>
    </a>`;
  }

  const n = S.news;
  if (an(n)) html += `
  <section class="news">
    <div class="container">
      <h2 class="titel">${n.ueberschrift}</h2>
      <div class="karten karten--3">${n.eintraege.map(k => karte(k, n.linkText)).join("")}</div>
    </div>
  </section>`;

  const e = S.experten;
  if (an(e)) html += `
  <section class="experten">
    <div class="container">
      ${wenn(e.kategorie, `<div class="kategorie">${e.kategorie}</div>`)}
      <h2 class="titel">${e.ueberschrift}</h2>
      <div class="karten karten--2">${e.eintraege.map(k => karte(k, e.linkText)).join("")}</div>
    </div>
  </section>`;

  /* ---------- Kontakt ---------- */
  const c = S.kontakt;
  if (an(c)) html += `
  <section class="kontakt">
    <div class="container kontakt-raster">
      <div>
        <h2 class="titel">${c.ueberschrift}</h2>
        <p class="text">${c.text}</p>
        <a class="mehr mehr--gold" href="${c.link}">${c.linkText} ${pfeil}</a>
      </div>
      <div class="kontakt-bild">${bild(c.bild, "Kontakt")}</div>
    </div>
  </section>`;

  /* ---------- Know-how ---------- */
  const k = S.knowhow;
  if (an(k)) html += `
  <section class="knowhow">
    <div class="container">
      ${wenn(k.kategorie, `<div class="kategorie">${k.kategorie}</div>`)}
      <h2 class="titel">${k.ueberschrift}</h2>
      <div class="knowhow-raster">
        <div class="knowhow-bild">${bild(k.bild, "Team")}</div>
        <div>${k.absaetze.map(p => `<p class="text">${p}</p>`).join("")}</div>
      </div>
    </div>
  </section>`;

  /* ---------- Footer ---------- */
  const f = S.footer;
  if (an(f)) html += `
  <footer class="fuss">
    <div class="container">
      <div class="fuss-logo">${logo(true)}</div>
      <div class="fuss-spalten">
        ${S.menue.map(g => `
          <div class="fuss-spalte">
            <a href="#" class="fuss-titel">${g.titel}</a>
            ${g.links.map(l => `<a href="#">${l}</a>`).join("")}
          </div>`).join("")}
      </div>
      <div class="fuss-extras">
        ${wenn(f.newsButton, `<a href="#" class="news-button">${icons.zeitung}<span>${f.newsButton}</span><em>PDF</em></a>`)}
        <div class="auszeichnung">${bild(f.auszeichnungBild, "Auszeichnung")}</div>
        ${wenn(f.zeigeLinkedin, `<a href="${S.seitenButtons.linkedin}" class="fuss-linkedin" aria-label="LinkedIn">${icons.linkedin}</a>`)}
      </div>
    </div>
  </footer>`;

  /* ---------- Testprojekt-Hinweis ---------- */
  const t = S.hinweis;
  if (an(t)) html += `
  <div class="hinweis"><strong>${t.titel}</strong> · ${t.text}</div>`;

  /* ---------- Schwebende Buttons ---------- */
  const sb = S.seitenButtons;
  if (an(sb)) html += `
  <div class="seiten-buttons">
    ${wenn(sb.email, `<a href="${sb.email}" aria-label="E-Mail">${icons.mail}</a>`)}
    ${wenn(sb.telefon, `<a href="${sb.telefon}" aria-label="Telefon">${icons.telefon}</a>`)}
    ${wenn(sb.linkedin, `<a href="${sb.linkedin}" aria-label="LinkedIn">${icons.linkedin}</a>`)}
  </div>`;

  app.innerHTML = html;

  /* ---------- Menü öffnen / schließen ---------- */
  const menue = document.querySelector(".menue");
  const auf = (offen) => {
    menue.classList.toggle("offen", offen);
    menue.setAttribute("aria-hidden", String(!offen));
    document.body.style.overflow = offen ? "hidden" : "";
  };
  document.querySelector(".burger").addEventListener("click", () => auf(true));
  document.querySelector(".menue-zu").addEventListener("click", () => auf(false));
})();
