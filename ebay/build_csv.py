import csv, sys, io
src, out = sys.argv[1], sys.argv[2]
lines = open(src, encoding='utf-8-sig').read().split('\n')
info_line, header_line = lines[0], lines[1]
header = header_line.split(';')
extra = ['IntlShippingService-1:Option', 'IntlShippingService-1:Cost', 'IntlShippingService-1:Locations']
header += extra
col = {h.lstrip('*').split('(')[0] if h.startswith('*Action') else h.lstrip('*'): i for i, h in enumerate(header)}

FOOT = ("<p><b>Versand:</b> sicher verpackt, Versand innerhalb von 2 Werktagen aus Düsseldorf. "
        "Kombiversand bei mehreren Artikeln möglich, bitte vor dem Kauf anfragen.</p>"
        "<p><b>Rückgabe:</b> 14 Tage Rückgabe, Rücksendekosten trägt der Käufer.</p>"
        "<p>Gemäß § 19 UStG wird keine Umsatzsteuer berechnet (Kleinunternehmer).</p>")

def desc(title, bullets, intro):
    lis = ''.join(f'<li>{b}</li>' for b in bullets)
    return f'<h2>{title}</h2><p>{intro}</p><ul>{lis}</ul>{FOOT}'

BOX = dict(dom='DE_DHLPaket', dom_cost='6.50', intl_cost='20.00')
CARD = dict(dom='DE_DHLPackchen', dom_cost='5.00', intl_cost='15.00')

items = [
  dict(sku='RB-SG-01', cat='261044',
       title='Riftbound League of Legends TCG Secret Garden Bundle Box - Neu & OVP',
       cond='1000', spiel='Riftbound: League of Legends TCG', edition='Secret Garden',
       hersteller='Riot Games', sprache='Englisch', jahr='2026', konf='',
       price='179.00', auto='165.00', minoff='150.00', qty='2', ship=BOX,
       d=desc('Riftbound: League of Legends TCG – Secret Garden Bundle Box',
              ['Zustand: neu, originalverschweißt', 'Limitiertes Event-Exklusiv-Produkt', 'Nicht im regulären Handel erhältlich'],
              'Verkauft wird die limitierte Secret Garden Bundle Box für Riftbound: League of Legends TCG.')),
  dict(sku='PKM-30-TTB-POSTER', cat='261044',
       title='Pokémon 30 Jahre Top-Trainer-Box + Poster Kollektion Bundle Deutsch Neu OVP',
       cond='1000', spiel='Pokémon TCG', edition='30th Anniversary Edition',
       hersteller='The Pokémon Company', sprache='Deutsch', jahr='2026', konf='',
       price='189.00', auto='175.00', minoff='165.00', qty='1', ship=BOX,
       d=desc('Pokémon 30 Jahre – Top-Trainer-Box + Poster Kollektion',
              ['1× Pokémon 30 Jahre Top-Trainer-Box (deutsch), neu & OVP', '1× Pokémon 30 Jahre Poster Kollektion (deutsch), neu & OVP', 'Ideal als Geschenk oder für Sammler'],
              'Bundle aus der Top-Trainer-Box und der Poster Kollektion zum 30-jährigen Pokémon-Jubiläum.')),
  dict(sku='CP-REBECCA-PROMO', cat='183454',
       title='Cyberpunk TCG Rebecca Having a Moment Promo Foil Karte Near Mint',
       cond='4000', kz='400010', spiel='Cyberpunk CCG', edition='Promo',
       hersteller='', sprache='Englisch', jahr='2026', konf='',
       price='229.00', auto='210.00', minoff='190.00', qty='2', ship=CARD,
       d=desc('Cyberpunk TCG – Rebecca „Having a Moment“ Promo (Foil)',
              ['Zustand: Near Mint, direkt aus der Verpackung in Hülle', 'Versand in Sleeve + Toploader, gut geschützt', 'Seltene Event-Promo'],
              'Verkauft wird die Rebecca-Promokarte aus dem Cyberpunk Trading Card Game.')),
  dict(sku='MTG-BENJAMIN-PROMO', cat='183454',
       title='Magic the Gathering Benjamin Promo Karte SPIEL Essen 2026 Near Mint',
       cond='4000', kz='400010', spiel='Magic: The Gathering', edition='Diverse Promos',
       hersteller='Wizards of the Coast', sprache='', jahr='2026', konf='',
       price='5.00', auto='', minoff='', qty='9', ship=CARD, nooffer=True,
       d=desc('Magic: The Gathering – Benjamin Promo (SPIEL Essen 2026)',
              ['Zustand: Near Mint', 'Event-Promo von der SPIEL Essen 2026', 'Mehrere Exemplare verfügbar – einfach gewünschte Stückzahl wählen'],
              'Verkauft wird die Benjamin-Promokarte von der SPIEL Essen 2026.')),
]

def row(it):
    r = [''] * len(header)
    def s(name, v):
        if name not in col: raise SystemExit('missing column ' + name)
        r[col[name]] = v
    r[0] = 'Draft'
    s('CustomLabel', it['sku']); s('Category', it['cat']); s('Title', it['title'])
    s('ConditionID', it['cond'])
    if it.get('kz'): s('CD:Kartenzustand - (ID: 40001)', it['kz'])
    s('C:Spiel', it['spiel']); s('C:Edition', it['edition'])
    if it['hersteller']: s('C:Hersteller', it['hersteller'])
    if it['sprache']: s('C:Sprache', it['sprache'])
    s('C:Herstellungsjahr', it['jahr'])
    if it['konf']: s('C:Konfiguration', it['konf'])
    s('Description', it['d']); s('Format', 'FixedPrice'); s('Duration', 'GTC')
    s('StartPrice', it['price']); s('Quantity', it['qty'])
    if not it.get('nooffer'):
        s('BestOfferEnabled', '1'); s('BestOfferAutoAcceptPrice', it['auto']); s('MinimumBestOfferPrice', it['minoff'])
    s('Location', '40235 Düsseldorf'); s('ShippingType', 'Flat')
    s('ShippingService-1:Option', it['ship']['dom']); s('ShippingService-1:Cost', it['ship']['dom_cost'])
    s('IntlShippingService-1:Option', 'DE_PaketInternational'); s('IntlShippingService-1:Cost', it['ship']['intl_cost'])
    s('IntlShippingService-1:Locations', 'Worldwide')
    s('DispatchTimeMax', '2')
    s('ReturnsAcceptedOption', 'ReturnsAccepted'); s('ReturnsWithinOption', 'Days_14')
    s('RefundOption', 'MoneyBack'); s('ShippingCostPaidByOption', 'Buyer')
    return r

for it in items: assert len(it['title']) <= 80, (len(it['title']), it['title'])
buf = io.StringIO()
buf.write(info_line + '\n')
w = csv.writer(buf, delimiter=';', lineterminator='\n')
w.writerow(header)
for it in items: w.writerow(row(it))
open(out, 'w', encoding='utf-8-sig').write(buf.getvalue())
print('ok', len(items))
