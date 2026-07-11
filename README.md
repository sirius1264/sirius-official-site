# Sirius Official Site

静的なアーティストサイト。`index.html` / `css/style.css` / `js/main.js` のみで動作します。

## 新曲の自動反映について

`scripts/sync_tunecore.py` が TuneCore のアーティストページ ( https://www.tunecore.co.jp/artists?id=666152 ) を
チェックし、`data/tracks.json` にない新曲があれば

1. ジャケット画像を `images/jackets/` にダウンロード
2. `data/tracks.json` に追記
3. `index.html` の `<!-- TRACKS:START -->` 〜 `<!-- TRACKS:END -->` と、
   トップの「New Single」表示・カウントダウンを最新曲に合わせて書き換え

を行います。`.github/workflows/sync.yml` により毎日 06:00 JST に自動実行され、変更があれば
自動でコミット・push されます(GitHub Pages を有効化しておけば、push だけで公開サイトにも反映されます)。

- 手動で今すぐ実行したい場合: GitHub の Actions タブ → 「Sync TuneCore」→ Run workflow
- ローカルで試す場合: `python scripts/sync_tunecore.py`
- 実行間隔を変えたい場合: `.github/workflows/sync.yml` の `cron` を編集

TuneCore に公式APIは無いため、ページに埋め込まれたデータを解析する非公式な方法です。
TuneCore側のサイト実装が変わると動かなくなる可能性があります。その場合は
`scripts/sync_tunecore.py` の正規表現(`NAME_PAT` / `LINK_PAT` / `DATE_PAT` / `ARTWORK_PAT`)の
調整が必要です。
