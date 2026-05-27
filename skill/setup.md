# setup — install `telegraph-publish` when missing

Read this only when `telegraph-publish --help` fails with
"command not found" (or the Windows equivalent). Otherwise the tool is
already installed — skip this file.

## Pick one install command

All three install the same thing; pick the first one that's available on
the host. Requires **Python 3.8+** (check with `python3 --version`).

```bash
# (1) pip — universal, present in every Python install
pip install git+https://github.com/dim-s/telegraph-cli.git

# (2) pipx — isolates the install in its own venv (recommended if available)
pipx install git+https://github.com/dim-s/telegraph-cli.git

# (3) uv tool — fastest; needs `uv` installed
uv tool install git+https://github.com/dim-s/telegraph-cli.git
```

Pin a version (optional but safer for scripts):

```bash
pip install git+https://github.com/dim-s/telegraph-cli.git@v1.0.0
```

## Verify

```bash
telegraph-publish --help
```

You should see usage output starting with `usage: telegraph-publish ...`.
If the command still isn't found, `pip`'s scripts directory may not be on
`PATH`. Common locations:

- macOS / Linux: `~/.local/bin` (user install) or the venv's `bin/`.
- Windows: `%APPDATA%\Python\PythonXY\Scripts` (user install) or the
  venv's `Scripts\`.

Add the relevant directory to `PATH`, or invoke via
`python -m pip show -f telegraph-cli` to locate the executable.

## Manual fallback (no pip)

Single-file script, runs from any directory once `python3` is on `PATH`:

```bash
curl -fsSL https://raw.githubusercontent.com/dim-s/telegraph-cli/main/telegraph_publish.py \
  -o ~/.local/bin/telegraph-publish
chmod +x ~/.local/bin/telegraph-publish
```

On Windows without WSL, save the script and invoke as
`python telegraph_publish.py <file.md>`.

## After install

Return to [SKILL.md](SKILL.md) and proceed with the requested task. On
first publish the CLI creates a telegra.ph account and stores the token
in `~/.config/telegraph/account.json` — do not delete that file.
