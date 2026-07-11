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
INDEX_HTML = ROOT / "index.html"
JACKETS_DIR = ROOT / "images" / "jackets"

TRACKS_START = "<!-- TRACKS:START"
TRACKS_END = "<!-- TRACKS:END -->"

JST = timezone(timedelta(hours=9))

NAME_PAT = re.compile(r'"nameJa":"((?:[^"\\]|\\.)*)"')
LINK_PAT = re.compile(r'"linkcore":\{[^}]*?"url":"(https://linkco\.re/[A-Za-z0-9]+)"')
DATE_PAT = re.compile(r'"releaseDate":"(\d{4}-\d{2}-\d{2})"')
ARTWORK_PAT = re.compile(
    r'https://tcj-image-production\.s3-ap-northeast-1\.amazonaws\.com/[^"]+?\.(?:png|jpg|jpeg)\?[^"]*'
)

WINDOW = 2500


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


def render_track_li(track: dict, is_new: bool) -> str:
    d = date.fromisoformat(track["releaseDate"])
    meta = d.strftime("%Y.%m.%d")
    if d > date.today():
        meta += " 配信予定"

    cls = "track-card is-new" if is_new else "track-card"
    title_escaped = track["title"].replace("&", "&amp;").replace('"', "&quot;")

    return (
        f'        <li class="{cls}">\n'
        f'          <a href="{track["linkUrl"]}" target="_blank" rel="noopener">\n'
        f'            <div class="track-art"><img src="{track["jacket"]}" alt="{title_escaped} ジャケット" loading="lazy"></div>\n'
        f'            <div class="track-info">\n'
        f'              <span class="track-name">{track["title"]}</span>\n'
        f'              <span class="track-meta">{meta}</span>\n'
        f"            </div>\n"
        f"          </a>\n"
        f"        </li>"
    )


def update_index_html(tracks: list[dict]) -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")

    ordered = sorted(tracks, key=lambda t: t["releaseDate"], reverse=True)
    latest = ordered[0]

    lis = "\n".join(render_track_li(t, is_new=(t is latest)) for t in ordered)
    block = f"{TRACKS_START} (このコメントの間は scripts/sync_tunecore.py が自動生成します。手動で編集しても次回の自動更新で上書きされます) -->\n{lis}\n        {TRACKS_END}"

    pattern = re.compile(
        re.escape(TRACKS_START) + r".*?" + re.escape(TRACKS_END), re.DOTALL
    )
    if not pattern.search(html):
        raise RuntimeError("TRACKS:START/END marker not found in index.html")
    html = pattern.sub(block, html)

    d = date.fromisoformat(latest["releaseDate"])
    release_date_label = d.strftime("%Y.%m.%d") + " Release"
    html = re.sub(r'(<h2 class="release-title">)[^<]*(</h2>)', rf"\g<1>{latest['title']}\g<2>", html)
    html = re.sub(r'(<p class="release-date">)[^<]*(</p>)', rf"\g<1>{release_date_label}\g<2>", html)
    target_iso = f"{latest['releaseDate']}T00:00:00+09:00"
    html = re.sub(r'(data-target=")[^"]*(")', rf"\g<1>{target_iso}\g<2>", html)

    INDEX_HTML.write_text(html, encoding="utf-8")


def main() -> int:
    print(f"Fetching {ARTIST_URL} ...")
    html = fetch(ARTIST_URL).decode("utf-8", errors="replace")

    scraped = scrape_current_tracks(html)
    if not scraped:
        print("[error] no tracks parsed from TuneCore page (site structure may have changed)", file=sys.stderr)
        return 1

    known = load_known_tracks()
    existing_hashes = known_hashes(known)

    new_tracks = [t for t in scraped if t["hash"] not in existing_hashes]
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

    updated.sort(key=lambda t: t["releaseDate"], reverse=True)
    TRACKS_JSON.write_text(
        json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    update_index_html(updated)

    print(f"Updated data/tracks.json and index.html with {len(updated) - len(known)} new track(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
