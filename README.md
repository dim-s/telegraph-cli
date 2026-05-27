# telegraph-cli

Markdown → [telegra.ph](https://telegra.ph) publisher. Single-file Python 3
CLI, **stdlib only**, no runtime dependencies, no build step.

Publishes a Markdown file as a telegra.ph article, edits existing pages,
uploads images, and prints the resulting URL.

## Install

Works on macOS, Linux, and Windows. Requires Python 3.8+.

```bash
pip install git+https://github.com/dim-s/telegraph-cli.git
```

That's it. `pip` creates a `telegraph-publish` executable on your PATH
(including a proper `.exe` shim on Windows). No git clone, no symlinks, no
shell-specific setup.

To upgrade:

```bash
pip install -U git+https://github.com/dim-s/telegraph-cli.git
```

### Alternatives

**With `pipx`** (isolated, recommended if you don't want to pollute your
base Python):

```bash
pipx install git+https://github.com/dim-s/telegraph-cli.git
```

**With `uv tool`** (fastest):

```bash
uv tool install git+https://github.com/dim-s/telegraph-cli.git
```

**Manual** (just the script, no install):

```bash
curl -fsSL https://raw.githubusercontent.com/dim-s/telegraph-cli/main/telegraph_publish.py \
  -o ~/.local/bin/telegraph-publish
chmod +x ~/.local/bin/telegraph-publish
```

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
access token in `~/.config/telegraph/account.json` (or
`%APPDATA%\telegraph\account.json` on Windows — Python's `Path.home()`
locates it for you). **Keep that file** — without it the pages you created
become unmanageable (telegra.ph has no "recover account" flow).

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

## Claude Code skill

For [Claude Code](https://claude.com/claude-code) users: the [`skill/`](./skill)
directory contains a ready-to-use skill (`SKILL.md` + `setup.md`) so the
agent can invoke `telegraph-publish` on demand and self-install when the
CLI is missing.

Install — pick the line that matches your OS. No git clone, no symlinks
needed (unless you want them).

**macOS / Linux:**

```bash
mkdir -p ~/.claude/skills/telegraph && \
curl -fsSL -o ~/.claude/skills/telegraph/SKILL.md https://raw.githubusercontent.com/dim-s/telegraph-cli/main/skill/SKILL.md && \
curl -fsSL -o ~/.claude/skills/telegraph/setup.md  https://raw.githubusercontent.com/dim-s/telegraph-cli/main/skill/setup.md
```

**Windows (PowerShell):**

```powershell
$dir = "$env:USERPROFILE\.claude\skills\telegraph"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
Invoke-WebRequest https://raw.githubusercontent.com/dim-s/telegraph-cli/main/skill/SKILL.md -OutFile "$dir\SKILL.md"
Invoke-WebRequest https://raw.githubusercontent.com/dim-s/telegraph-cli/main/skill/setup.md  -OutFile "$dir\setup.md"
```

**Already cloned the repo? Symlink instead** — edits to the skill stay
in sync with `git pull`:

```bash
ln -s "$(pwd)/skill" ~/.claude/skills/telegraph
```

After install, restart Claude Code (or `/reload`) so the new skill is
indexed. The CLI itself installs automatically the first time the skill
fires — `setup.md` guides the agent through it.

## License

[MIT](./LICENSE) © 2026 Дмитрий Зайцев (Dmitry Zaytsev)
