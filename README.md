# telegraph-cli

Markdown → [telegra.ph](https://telegra.ph) publisher. Single-file Python 3 CLI,
stdlib only, no dependencies, no build step.

Publishes a Markdown file as a telegra.ph article, edits existing pages,
uploads images, and prints the resulting URL.

## Install

Drop the script anywhere on your `PATH`:

```bash
git clone https://github.com/dim-s/telegraph-cli.git ~/dev/telegraph-cli
ln -s ~/dev/telegraph-cli/telegraph-publish ~/.local/bin/telegraph-publish
chmod +x ~/.local/bin/telegraph-publish
```

Requires Python 3.8+ (uses only the standard library).

## Quick start

```bash
# publish a markdown file → prints the page URL
telegraph-publish draft.md

# parse only, print stats, do not call the API
telegraph-publish draft.md --dry-run

# update an existing page (URL or path)
telegraph-publish draft.md --edit https://telegra.ph/My-Post-05-27

# upload a single image, print its URL
telegraph-publish --upload-image cover.png

# publish without auto-uploading local images
telegraph-publish draft.md --no-image-upload
```

On first publish the script creates a telegra.ph account and caches the
access token in `~/.config/telegraph/account.json`. **Keep that file** —
without it the pages you created become unmanageable (telegra.ph has no
"recover account" flow).

## Markdown support

| Markdown | Renders as |
|---|---|
| `# Title` (first one) | Page title |
| `##`, `###` | `<h3>` (telegra.ph has no `<h2>`) |
| `####` | `<h4>` |
| `---` on its own line | `<hr>` |
| `**bold**` | `<strong>` |
| `*italic*` | `<em>` |
| `` `code` `` | `<code>` |
| `[text](url)` | `<a href>` |
| `![alt](path)` block | `<figure><img><figcaption>` (local paths auto-upload) |
| Pipe table | One paragraph per data row, headers in `<strong>`, cells joined by `·` |

Tables are not natively supported by telegra.ph — the script renders each
row as a compact bold-header paragraph. If you need real tables, telegra.ph
is the wrong platform.

## Environment

| Variable | Purpose |
|---|---|
| `TELEGRAPH_SHORT_NAME` | Short account name on first run (default: `Anonymous`) |
| `TELEGRAPH_AUTHOR` | Display name shown under the article title |

Both are baked into `account.json` on first publish — after that the env
vars are no longer needed.

## Known limits of telegra.ph (not bugs of this CLI)

- **No `<h1>` or `<h2>`** — headings of any level collapse to `h3`/`h4`.
- **No `<table>`** — tables are rendered as paragraph-per-row.
- **`--upload-image` often returns `Unknown error` (HTTP 400)** — telegra.ph
  has throttled its public `/upload` endpoint for external clients since
  ~2022. Host images on any CDN and pass absolute URLs in markdown when
  this happens. The script reports a clear error, not a traceback.
- **`--edit` only works for pages created with the same access token.**
  Delete `~/.config/telegraph/account.json` and your previous pages
  become read-only.

## License

[MIT](./LICENSE) © 2026 Дмитрий Зайцев (Dmitry Zaytsev)
