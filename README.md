# ECD Germany feed

Napi ar- es keszletfigyelo feed az [ecdgermany.de](https://www.ecdgermany.de) katalogusarol,
**cikkszam (Artikelnummer)** alapu termekazonositassal.

## Allando linkek

| Fajl | Direkt URL |
| --- | --- |
| JSON | `https://raw.githubusercontent.com/szabviktor-aligvarom/ecd-feed/main/ecd_feed.json` |
| CSV | `https://raw.githubusercontent.com/szabviktor-aligvarom/ecd-feed/main/ecd_feed.csv` |

Ezek az URL-ek **nem valtoznak**, a tartalom naponta frissul.

## Adatforras

Az ecdgermany.de Shopify-on fut, ezert a katalogus a publikus `/products.json`
vegponton keresztul elerheto. Nincs HTML-scraping, nincs API kulcs, nincs
blokkolasi kockazat, es nem torik el, ha az ECD atalakitja az oldal designjat.

## Mezok

| Mezo | Jelentes |
| --- | --- |
| `cikkszam` | ECD Artikelnummer (Shopify SKU) - **ez az azonosito kulcs**, egyedi |
| `nev` | Termeknev (nemet) |
| `ar_eur` | Aktualis eladasi ar, EUR |
| `listaar_eur` | Eredeti / athuzott ar, EUR |
| `akcios` | Akcios-e most |
| `kedvezmeny_szazalek` | Kedvezmeny szazalekban |
| `keszleten` | `true` = keszleten, `false` = elfogyott |
| `keszlet_szoveg` | Ugyanez szovegesen |
| `suly_gramm` | Szallitasi suly |
| `url` | Termekoldal linkje |
| `kep` | Fokep URL |
| `valtozatok_szama` | Ha >1, az ECD tobbszor listazza ezt a cikkszamot |
| `utolso_modositas` | Az ECD sajat modositasi idopontja |

## Fontos tudnivalok

- **A keszlet csak van/nincs.** Pontos darabszamot a Shopify nem ad ki
  hitelesites nelkul. Ez a publikus vegpont korlatja, nem a scripte.
- **Az arak brutto kiskereskedelmi arak EUR-ban**, nem beszallitoi nettó arak.
- Az ECD nehany terméket duplan listaz ugyanazzal a cikkszammal. A feed ilyenkor
  a keszleten levo valtozatot tartja meg, hogy a cikkszam egyedi maradjon.

## Ujragneralas kezzel

```sh
python3 ecd_feed.py ecd_feed.json
```
