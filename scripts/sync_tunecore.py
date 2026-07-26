#!/usr/bin/env python3
"""
TuneCore のアーティストページを毎日チェックし、新曲があれば
data/tracks.json とジャケット画像、index.html の該当箇所を自動更新するスクリプト。

TuneCore の公開APIは存在しないため、アーティストページに埋め込まれた
Next.js のデータ(JSON文字列)を正規表現で読み取っている。TuneCore側の
サイト実装が変わると動かなくなる可能性がある(非公式スクレイピング)。
"""

import json
import re
import sys
import urllib.request
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

ARTIST_URL = "https://www.tunecore.co.jp/artists?id=666152"
ROOT = Path(__file__).resolve().parent.parent
TRACKS_JSON = ROOT / "data" / "tracks.json"
EXCLUDED_JSON = ROOT / "data" / "excluded_tracks.json"
INDEX_HTML = ROOT / "index.html"
MUSIC_HTML = ROOT / "music.html"
MUSIC_DIR = ROOT / "music"
JACKETS_DIR = ROOT / "images" / "jackets"

TRACKS_START = "<!-- TRACKS:START"
TRACKS_END = "<!-- TRACKS:END -->"
TEASER_START = "<!-- TEASER:START"
TEASER_END = "<!-- TEASER:END -->"
TEASER_COUNT = 4

JST = timezone(timedelta(hours=9))

NAME_PAT = re.compile(r'"nameJa":"((?:[^"\\]|\\.)*)"')
LINK_PAT = re.compile(r'"linkcore":\{[^}]*?"url":"(https://linkco\.re/[A-Za-z0-9]+)"')
DATE_PAT = re.compile(r'"releaseDate":"(\d{4}-\d{2}-\d{2})"')
ARTWORK_PAT = re.compile(
    r'https://tcj-image-production\.s3-ap-northeast-1\.amazonaws\.com/[^"]+?\.(?:png|jpg|jpeg)\?[^"]*'
)

WINDOW = 2500

# 曲ごとの配信リンクボタン。表示順もここで決まる。
# slug = linkco.re ページ内の /to/{slug}/{数字ID} のサービスキー
SERVICES = [
    {
        "slug": "apple_music",
        "key": "appleMusic",
        "label": "Apple Musicで聴く",
        "css": "apple",
        "icon": '<path d="M17.05 12.5c-.03-2.6 2.13-3.85 2.23-3.92-1.22-1.78-3.11-2.02-3.78-2.05-1.6-.16-3.13.95-3.95.95-.82 0-2.08-.93-3.43-.9-1.76.03-3.4 1.03-4.3 2.6-1.84 3.2-.47 7.92 1.32 10.51.87 1.27 1.92 2.7 3.3 2.65 1.33-.05 1.83-.86 3.43-.86 1.6 0 2.05.86 3.44.83 1.42-.02 2.32-1.29 3.19-2.56.99-1.45 1.4-2.86 1.42-2.93-.03-.02-2.74-1.05-2.77-4.32zM14.6 4.9c.73-.88 1.22-2.1 1.09-3.32-1.05.04-2.33.7-3.08 1.58-.68.78-1.27 2.03-1.11 3.22 1.16.09 2.36-.59 3.1-1.48z"/>',
    },
    {
        "slug": "spotify",
        "key": "spotify",
        "label": "Spotifyで聴く",
        "css": "spotify",
        "icon": '<path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm4.6 14.4a.6.6 0 0 1-.83.2c-2.27-1.39-5.13-1.7-8.5-.93a.6.6 0 1 1-.27-1.17c3.69-.84 6.86-.48 9.4 1.07.29.18.38.55.2.83zm1.22-2.72a.75.75 0 0 1-1.03.25c-2.6-1.6-6.56-2.06-9.63-1.13a.75.75 0 1 1-.44-1.44c3.51-1.06 7.87-.55 10.85 1.29.36.22.47.68.25 1.03zm.1-2.83c-3.12-1.85-8.27-2.02-11.25-1.12a.9.9 0 1 1-.52-1.72c3.42-1.03 9.1-.83 12.68 1.28a.9.9 0 1 1-.91 1.56z"/>',
    },
    {
        "slug": "youtube_music_key",
        "key": "youtubeMusic",
        "label": "YouTube Musicで聴く",
        "css": "youtube",
        "icon": '<path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.4.6A3 3 0 0 0 .5 6.2 31.6 31.6 0 0 0 0 12a31.6 31.6 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.6 9.4.6 9.4.6s7.5 0 9.4-.6a3 3 0 0 0 2.1-2.1A31.6 31.6 0 0 0 24 12a31.6 31.6 0 0 0-.5-5.8zM9.6 15.6V8.4l6.3 3.6-6.3 3.6z"/>',
    },
    {
        "slug": "line",
        "key": "lineMusic",
        "label": "LINE MUSICで聴く",
        "css": "line",
        "icon": '<path d="M12 2C6.48 2 2 5.58 2 10c0 3.96 3.58 7.27 8.42 7.9.33.07.77.22.88.5.1.26.07.66.03.92l-.14.86c-.04.26-.2 1 .87.55s5.78-3.4 7.89-5.83C21.3 12.6 22 11.37 22 10c0-4.42-4.48-8-10-8zm-3.6 10.4H6.2a.4.4 0 0 1-.4-.4V7.6a.6.6 0 0 1 1.2 0v3.6h1.4a.6.6 0 0 1 0 1.2zm2.2-.6a.6.6 0 0 1-1.2 0V7.6a.6.6 0 0 1 1.2 0v4.2zm5.4 0a.6.6 0 0 1-1.03.42l-2.17-2.7v2.28a.6.6 0 0 1-1.2 0V7.6a.6.6 0 0 1 1.03-.42l2.17 2.7V7.6a.6.6 0 0 1 1.2 0v4.2zm3.6 0a.6.6 0 0 1-.6.6h-1.8a.4.4 0 0 1-.4-.4V7.6a.6.6 0 0 1 1.2 0v3.6h1a.6.6 0 0 1 .6.6z"/>',
    },
    {
        "slug": "amazon_music_unlimited",
        "key": "amazonMusic",
        "label": "Amazon Musicで聴く",
        "css": "amazon",
        "icon": '<path d="M12 3v10.55A4 4 0 1 0 14 17V7h4V3h-6z"/>',
    },
]


def fetch(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read()


def nearest(pos: int, candidates: list[tuple[int, str]]) -> str | None:
    best = None
    best_dist = WINDOW + 1
    for cpos, value in candidates:
        dist = abs(cpos - pos)
        if dist < best_dist:
            best_dist = dist
            best = value
    return best if best_dist <= WINDOW else None


def hash_of(link_url: str) -> str:
    return link_url.split("?")[0].rstrip("/").split("/")[-1]


def unescape_json_fragment(raw: str) -> str:
    """HTML内のJSON文字列断片(\\u0026 等)を実文字に戻す。"""
    return json.loads(f'"{raw}"')


def scrape_current_tracks(html: str) -> list[dict]:
    names = [(m.start(), unescape_json_fragment(m.group(1))) for m in NAME_PAT.finditer(html)]
    dates = [(m.start(), m.group(1)) for m in DATE_PAT.finditer(html)]
    artworks = [
        (m.start(), unescape_json_fragment(m.group(0))) for m in ARTWORK_PAT.finditer(html)
    ]

    seen_hash = set()
    tracks = []
    for m in LINK_PAT.finditer(html):
        url = m.group(1)
        h = hash_of(url)
        if h in seen_hash:
            continue
        seen_hash.add(h)

        pos = m.start()
        title = nearest(pos, names)
        release_date = nearest(pos, dates)
        artwork = nearest(pos, artworks)

        if not title or not release_date or not artwork:
            print(f"[warn] incomplete data for {url}, skipping (title={title}, date={release_date}, artwork={bool(artwork)})", file=sys.stderr)
            continue

        tracks.append(
            {
                "hash": h,
                "title": title,
                "releaseDate": release_date,
                "linkUrl": f"{url}?lang=ja",
                "artworkUrl": artwork,
            }
        )
    return tracks


def load_known_tracks() -> list[dict]:
    if TRACKS_JSON.exists():
        return json.loads(TRACKS_JSON.read_text(encoding="utf-8"))
    return []


def load_excluded_hashes() -> set[str]:
    """手動でサイトから外した曲のハッシュ一覧。次回の自動同期で復活させないための除外リスト。"""
    if EXCLUDED_JSON.exists():
        return set(json.loads(EXCLUDED_JSON.read_text(encoding="utf-8")))
    return set()


def known_hashes(known: list[dict]) -> set[str]:
    return {hash_of(t["linkUrl"]) for t in known}


def download_artwork(url: str, hash_: str) -> str | None:
    try:
        data = fetch(url)
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] failed to download artwork for {hash_}: {exc}", file=sys.stderr)
        return None

    is_png = data[:8].startswith(b"\x89PNG")
    is_jpeg = data[:3].startswith(b"\xff\xd8\xff")
    if len(data) < 2000 or not (is_png or is_jpeg):
        print(f"[warn] downloaded artwork for {hash_} doesn't look like an image, skipping", file=sys.stderr)
        return None

    JACKETS_DIR.mkdir(parents=True, exist_ok=True)
    dest = JACKETS_DIR / f"{hash_}{'.png' if is_png else '.jpg'}"
    dest.write_bytes(data)
    return f"images/jackets/{dest.name}"


STORE_ID_PAT = {
    s["slug"]: re.compile(rf'to/{re.escape(s["slug"])}/(\d+)') for s in SERVICES
}


def fetch_service_links(link_url: str) -> dict[str, str]:
    """曲の linkco.re ページから、各配信サービスへの直リンク(TuneCoreのリダイレクトURL)を取得する。
    JSで描画される部分ではなく静的HTMLに直接埋め込まれているため通常のHTTP取得で読み取れる。"""
    try:
        html = fetch(link_url).decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] failed to fetch linkco.re page {link_url}: {exc}", file=sys.stderr)
        return {}

    links: dict[str, str] = {}
    for service in SERVICES:
        m = STORE_ID_PAT[service["slug"]].search(html)
        if m:
            links[service["key"]] = f"https://www.tunecore.co.jp/to/{service['slug']}/{m.group(1)}"
    return links


def ensure_service_links(tracks: list[dict]) -> bool:
    """serviceLinks が未取得の曲があれば linkco.re から取得して補う。1件でも更新したら True を返す。"""
    changed = False
    for t in tracks:
        if t.get("serviceLinks"):
            continue
        print(f"Fetching service links for '{t['title']}' ...")
        links = fetch_service_links(t["linkUrl"])
        if links:
            t["serviceLinks"] = links
            changed = True
        else:
            print(f"[warn] no service links found for '{t['title']}'", file=sys.stderr)
    return changed


def track_hash(track: dict) -> str:
    return hash_of(track["linkUrl"])


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def format_meta(track: dict) -> str:
    d = date.fromisoformat(track["releaseDate"])
    meta = d.strftime("%Y.%m.%d")
    if d > date.today():
        meta += " 配信予定"
    return meta


def render_track_li(track: dict, is_new: bool) -> str:
    """楽曲一覧(トップのティーザー・music.html)用の<li>。曲ごとの自前ページにリンクする。"""
    cls = "track-card is-new" if is_new else "track-card"
    title_escaped = escape_html(track["title"])
    href = f'music/{track_hash(track)}.html'

    return (
        f'        <li class="{cls}">\n'
        f'          <a href="{href}">\n'
        f'            <div class="track-art"><img src="{track["jacket"]}" alt="{title_escaped} ジャケット" loading="lazy"></div>\n'
        f'            <div class="track-info">\n'
        f'              <span class="track-name">{track["title"]}</span>\n'
        f'              <span class="track-meta">{format_meta(track)}</span>\n'
        f"            </div>\n"
        f"          </a>\n"
        f"        </li>"
    )


def replace_marker_block(html: str, start: str, end: str, inner: str) -> str:
    block = f"{start} (このコメントの間は scripts/sync_tunecore.py が自動生成します。手動で編集しても次回の自動更新で上書きされます) -->\n{inner}\n        {end}"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    if not pattern.search(html):
        raise RuntimeError(f"marker {start} ... {end} not found")
    return pattern.sub(block, html)


def update_index_html(tracks: list[dict]) -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")

    ordered = sorted(tracks, key=lambda t: t["releaseDate"], reverse=True)
    latest = ordered[0]
    teaser = ordered[:TEASER_COUNT]

    lis = "\n".join(render_track_li(t, is_new=(t is latest)) for t in teaser)
    html = replace_marker_block(html, TEASER_START, TEASER_END, lis)

    d = date.fromisoformat(latest["releaseDate"])
    release_date_label = d.strftime("%Y.%m.%d") + " Release"
    html = re.sub(r'(<h2 class="release-title">)[^<]*(</h2>)', rf"\g<1>{latest['title']}\g<2>", html)
    html = re.sub(r'(<p class="release-date">)[^<]*(</p>)', rf"\g<1>{release_date_label}\g<2>", html)
    target_iso = f"{latest['releaseDate']}T00:00:00+09:00"
    html = re.sub(r'(data-target=")[^"]*(")', rf"\g<1>{target_iso}\g<2>", html)
    title_escaped = escape_html(latest["title"])
    html = re.sub(
        r'<img src="[^"]*" alt="[^"]*" class="release-art" id="releaseArt">',
        f'<img src="{latest["jacket"]}" alt="{title_escaped} ジャケット" class="release-art" id="releaseArt">',
        html,
    )

    INDEX_HTML.write_text(html, encoding="utf-8")


def update_music_html(tracks: list[dict]) -> None:
    html = MUSIC_HTML.read_text(encoding="utf-8")
    ordered = sorted(tracks, key=lambda t: t["releaseDate"], reverse=True)
    latest = ordered[0]
    lis = "\n".join(render_track_li(t, is_new=(t is latest)) for t in ordered)
    html = replace_marker_block(html, TRACKS_START, TRACKS_END, lis)
    MUSIC_HTML.write_text(html, encoding="utf-8")


TRACK_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | Sirius Official Site</title>
<meta name="description" content="Sirius「{title}」の配信ページ。Spotify・Apple Music・YouTube Musicなど各配信サービスはこちらから。">
<link rel="stylesheet" href="../css/style.css">

<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-WNW84195G6"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());

  gtag('config', 'G-WNW84195G6');
</script>
</head>
<body>

<header class="site-header" id="siteHeader">
  <div class="header-inner">
    <a href="../index.html#top" class="logo">Sirius</a>
  </div>
</header>

<main>
  <section class="track-page-header">
    <div class="section-inner">
      <img src="../{jacket}" alt="{title} ジャケット" class="track-page-art">
      <h1 class="track-page-title">{title}</h1>
      <p class="track-page-artist">Sirius</p>
      <p class="track-page-date">{date_label} Release</p>
    </div>
  </section>

  <div class="track-page-buttons">
{buttons_html}
    <a class="track-page-btn track-page-btn-more" href="{link_url}" target="_blank" rel="noopener">
      その他の配信サービスはこちら
    </a>
  </div>
</main>

<footer class="site-footer">
  <div class="section-inner footer-inner">
    <p class="footer-logo">Sirius</p>
    <div class="footer-sns">
      <a href="https://www.instagram.com/sirius_mcl" target="_blank" rel="noopener">Instagram</a>
      <a href="https://www.tiktok.com/@mci591" target="_blank" rel="noopener">TikTok</a>
      <a href="https://www.youtube.com/channel/UCcTDaZE5mEKhoSLrzESetUw" target="_blank" rel="noopener">YouTube</a>
    </div>
    <p class="footer-copy">&copy; <span id="year"></span> Sirius. All rights reserved.</p>
  </div>
</footer>

<script src="../js/main.js"></script>
</body>
</html>
"""


def render_service_buttons(track: dict) -> str:
    links = track.get("serviceLinks") or {}
    buttons = []
    for service in SERVICES:
        url = links.get(service["key"])
        if not url:
            continue
        buttons.append(
            f'    <a class="track-page-btn track-page-btn-{service["css"]}" href="{url}" target="_blank" rel="noopener">\n'
            f'      <svg class="track-page-btn-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">{service["icon"]}</svg>\n'
            f'      <span>{service["label"]}</span>\n'
            f"    </a>"
        )
    return "\n".join(buttons)


def render_track_page(track: dict) -> str:
    d = date.fromisoformat(track["releaseDate"])

    return TRACK_PAGE_TEMPLATE.format(
        title=escape_html(track["title"]),
        jacket=track["jacket"],
        date_label=d.strftime("%Y.%m.%d"),
        buttons_html=render_service_buttons(track),
        link_url=track["linkUrl"],
    )


def write_track_pages(tracks: list[dict]) -> None:
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    for t in tracks:
        dest = MUSIC_DIR / f"{track_hash(t)}.html"
        dest.write_text(render_track_page(t), encoding="utf-8")


def regenerate_all() -> int:
    """TuneCoreの曲一覧そのものへは問い合わせず、既存の data/tracks.json から
    index.html・music.html・曲ごとのページを全て再生成する
    (テンプレートを直した後や、初回のバックフィルに使う)。
    ただし各曲の配信サービスリンクがまだ無い場合は linkco.re から取得する。"""
    known = load_known_tracks()
    if not known:
        print("[error] data/tracks.json is empty", file=sys.stderr)
        return 1

    if ensure_service_links(known):
        TRACKS_JSON.write_text(
            json.dumps(known, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    update_index_html(known)
    update_music_html(known)
    write_track_pages(known)
    print(f"Regenerated index.html, music.html and {len(known)} track page(s) from data/tracks.json.")
    return 0


def main() -> int:
    if "--regenerate" in sys.argv:
        return regenerate_all()

    print(f"Fetching {ARTIST_URL} ...")
    html = fetch(ARTIST_URL).decode("utf-8", errors="replace")

    scraped = scrape_current_tracks(html)
    if not scraped:
        print("[error] no tracks parsed from TuneCore page (site structure may have changed)", file=sys.stderr)
        return 1

    known = load_known_tracks()
    existing_hashes = known_hashes(known)
    excluded_hashes = load_excluded_hashes()

    new_tracks = [
        t for t in scraped
        if t["hash"] not in existing_hashes and t["hash"] not in excluded_hashes
    ]
    if not new_tracks:
        print("No new tracks. Nothing to do.")
        return 0

    print(f"Found {len(new_tracks)} new track(s): {[t['title'] for t in new_tracks]}")

    updated = list(known)
    for t in new_tracks:
        jacket = download_artwork(t["artworkUrl"], t["hash"])
        if not jacket:
            print(f"[warn] skipping '{t['title']}' this run (artwork download failed, will retry next run)")
            continue
        updated.append(
            {
                "title": t["title"],
                "releaseDate": t["releaseDate"],
                "linkUrl": t["linkUrl"],
                "jacket": jacket,
            }
        )

    if len(updated) == len(known):
        print("No track could be added (all downloads failed). Nothing to commit.")
        return 0

    ensure_service_links(updated)

    updated.sort(key=lambda t: t["releaseDate"], reverse=True)
    TRACKS_JSON.write_text(
        json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    update_index_html(updated)
    update_music_html(updated)
    write_track_pages(updated)

    print(f"Updated data/tracks.json, index.html, music.html and track pages with {len(updated) - len(known)} new track(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
