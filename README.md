# Sirius Official Site

静的なアーティストサイト。`index.html`(トップ) / `music.html`(全曲一覧) / `music/*.html`(曲ごとのページ) /
`css/style.css` / `js/main.js` のみで動作します。

## サイト構成

- `index.html`: トップページ。Hero(SNS/配信サービスのフォロー導線つき) → New Single → Music(最新曲ティーザー) → Goods → Profile+Contact
- `music.html`: 全曲一覧ページ
- `music/<ハッシュ>.html`: 曲ごとのランディングページ。ジャケット・Spotify/Apple Music/YouTube Musicの検索リンク・
  「その他の配信サービスはこちら」(TuneCoreのスマートリンクへ)を掲載。Google Analyticsタグ入りなので、
  Meta広告などのランディングページ先としてそのまま使えます

## 新曲の自動反映について

`scripts/sync_tunecore.py` が TuneCore のアーティストページ ( https://www.tunecore.co.jp/artists?id=666152 ) を
チェックし、`data/tracks.json` にない新曲があれば

1. ジャケット画像を `images/jackets/` にダウンロード
2. `data/tracks.json` に追記
3. `index.html` の最新曲ティーザー・「New Single」表示・カウントダウンを更新
4. `music.html` の全曲一覧を更新
5. `music/<ハッシュ>.html` を新規生成

を行います。`.github/workflows/sync.yml` により毎日 06:00 JST に自動実行され、変更があれば
自動でコミット・push されます(GitHub Pages を有効化しておけば、push だけで公開サイトにも反映されます)。

- 手動で今すぐ実行したい場合: GitHub の Actions タブ → 「Sync TuneCore」→ Run workflow
- ローカルで試す場合: `python scripts/sync_tunecore.py`
- テンプレートを直した後などに、TuneCoreへ問い合わせずローカルの `data/tracks.json` から
  `index.html` / `music.html` / 曲ページを全部作り直したい場合: `python scripts/sync_tunecore.py --regenerate`
- 実行間隔を変えたい場合: `.github/workflows/sync.yml` の `cron` を編集
- TuneCoreには載っているが**サイトには出したくない曲**がある場合(例: 過去の古い曲など)は、
  `data/tracks.json` から該当曲を消すだけでは次回の自動実行で復活してしまいます。
  `data/excluded_tracks.json` にその曲の linkco.re のハッシュ(URLの末尾、例 `https://linkco.re/XXXXXXXX` の `XXXXXXXX` 部分)
  を追記してください。以後、自動同期はその曲を無視します。

TuneCore に公式APIは無いため、ページに埋め込まれたデータを解析する非公式な方法です。
TuneCore側のサイト実装が変わると動かなくなる可能性があります。その場合は
`scripts/sync_tunecore.py` の正規表現(`NAME_PAT` / `LINK_PAT` / `DATE_PAT` / `ARTWORK_PAT`)の
調整が必要です。
