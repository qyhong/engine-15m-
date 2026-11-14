# Mind 15 web tab

`mind15/index.html` is the whole page: one static file, inline CSS and JavaScript, no build
step, no framework, no outside script (it draws its own candle chart on a `<canvas>`). Fonts
come from Google Fonts, loaded the same way as the other `/aitrading/` pages.

## What it reads

One file, `./page.json`, beside the page (same origin, `cache: "no-cache"`, no query stamp;
checked on load and every 60 seconds). The engine writes it every 15 minutes to
`out/live/page.json` (`engine15/export.py`, `build_page`). `mind15/page.json` here is a copy
for local preview only.

A panel whose data is missing or null says "no data yet"; the rest still draws. The page always
shows "Data is N minutes old" and a red notice when the file is older than 45 minutes or cannot
be loaded. Every string from the file is written as text, never as markup.

## The one constant to set

Near the top of the script:

    const ANSWER_ENDPOINT = null;

While it is `null` the Send button of "The engine asks you" is off and the page says answers
are taken through the owner's console. Set it to the answer service's URL (same origin, or
the site's Content-Security-Policy must allow it) and Send POSTs JSON
`{pin, who, asset, side, conviction, note}` and shows the reply: accepted on a 2xx answer,
otherwise refused with the reply's `reason` / `message` / `error`. The PIN is checked by that
service only; the page never checks it, stores it or logs it.

## What a deploy needs

1. `mind15/index.html` served at `/aitrading/mind15/index.html`.
2. `page.json` beside it (`/aitrading/mind15/page.json`), refreshed from `out/live/page.json`
   after every 15-minute step, served with an ETag.
3. A fourth nav link, `Mind 15`, added on the three existing pages (Forecast, Engine & books,
   Congress trades); this page already links back to them with `../`, `../books/`, `../congress/`.

Preview: `py -3 -m http.server 8765 --directory web`, then `http://127.0.0.1:8765/mind15/`.
