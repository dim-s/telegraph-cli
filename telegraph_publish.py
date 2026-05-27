#!/usr/bin/env python3
"""Publish or edit a Markdown post on telegra.ph (stdlib only)."""
import argparse
import json
import mimetypes
import os
import re
import sys
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

API = "https://api.telegra.ph"
UPLOAD_URL = "https://telegra.ph/upload"
CONFIG_DIR = Path.home() / ".config" / "telegraph"
ACCOUNT_FILE = CONFIG_DIR / "account.json"


# ----- API helpers ---------------------------------------------------------

def api_call(method: str, params: dict) -> dict:
    url = f"{API}/{method}"
    data = urllib.parse.urlencode(
        {k: (v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))
         for k, v in params.items()}
    ).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read().decode())
    if not body.get("ok"):
        raise RuntimeError(f"telegraph API error: {body.get('error')}")
    return body["result"]


def ensure_account(short_name: str, author_name: str) -> str:
    if ACCOUNT_FILE.exists():
        return json.loads(ACCOUNT_FILE.read_text())["access_token"]
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    result = api_call("createAccount", {
        "short_name": short_name,
        "author_name": author_name,
    })
    ACCOUNT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"created account: short_name={short_name}", file=sys.stderr)
    return result["access_token"]


def upload_image(path: Path) -> str:
    """Upload a local image to telegra.ph, return absolute URL."""
    if not path.exists():
        raise FileNotFoundError(path)
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    boundary = f"----telegraph{uuid.uuid4().hex}"
    body = bytearray()
    body += f"--{boundary}\r\n".encode()
    body += (
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode()
    body += path.read_bytes()
    body += f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        UPLOAD_URL,
        data=bytes(body),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "telegraph-publish/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        raise RuntimeError(
            f"telegra.ph /upload returned HTTP {exc.code}: {raw!r}. "
            "Note: telegra.ph has throttled this endpoint for external "
            "clients since ~2022 — host images elsewhere and use absolute "
            "URLs in markdown."
        ) from None
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError(f"telegra.ph /upload returned non-JSON: {raw!r}")
    if isinstance(result, dict) and "error" in result:
        raise RuntimeError(
            f"telegra.ph /upload error: {result['error']}. "
            "This endpoint is unreliable for external clients; "
            "host the image elsewhere and pass an absolute URL."
        )
    if isinstance(result, str):
        raise RuntimeError(
            f"telegra.ph /upload returned a bare string: {result!r}. "
            "Endpoint is currently rejecting external uploads; "
            "host the image elsewhere and pass an absolute URL."
        )
    src = result[0]["src"]
    return urllib.parse.urljoin("https://telegra.ph", src)


# ----- Markdown → telegraph nodes -----------------------------------------

INLINE_PATTERNS = [
    (re.compile(r"\*\*(.+?)\*\*"), "strong"),
    (re.compile(r"`([^`]+)`"), "code"),
    (re.compile(r"\*(.+?)\*"), "em"),
]
LINK_RE = re.compile(r"(?<!\!)\[([^\]]+)\]\(([^)]+)\)")
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$")


def parse_inline(text: str):
    """Convert a text run with inline md → list of telegraph children."""
    nodes = []
    pos = 0
    while pos < len(text):
        candidates = []
        m_link = LINK_RE.search(text, pos)
        if m_link:
            candidates.append((m_link.start(), m_link, "link"))
        for rx, tag in INLINE_PATTERNS:
            m = rx.search(text, pos)
            if m:
                candidates.append((m.start(), m, tag))
        if not candidates:
            if text[pos:]:
                nodes.append(text[pos:])
            break
        candidates.sort(key=lambda c: c[0])
        start, m, kind = candidates[0]
        if text[pos:start]:
            nodes.append(text[pos:start])
        if kind == "link":
            nodes.append({"tag": "a", "attrs": {"href": m.group(2)},
                          "children": parse_inline(m.group(1))})
        else:
            nodes.append({"tag": kind, "children": parse_inline(m.group(1))})
        pos = m.end()
    return nodes


def split_table_row(line: str):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def parse_table_block(block: str):
    """Parse a markdown table block → list of telegraph nodes.

    Strategy: one paragraph per data row, with column headers in <strong>
    and cells joined by ' · '. Compact, no real <table> (telegra.ph doesn't
    support it).
    """
    lines = [ln for ln in block.splitlines() if ln.strip()]
    if len(lines) < 2:
        return None
    if not TABLE_SEP_RE.match(lines[1]):
        return None
    headers = split_table_row(lines[0])
    rows = [split_table_row(ln) for ln in lines[2:]]
    nodes = []
    for row in rows:
        children = []
        for i, cell in enumerate(row):
            if i > 0:
                children.append(" · ")
            header = headers[i] if i < len(headers) else ""
            if header:
                children.append({"tag": "strong",
                                 "children": parse_inline(header + ": ")})
            children.extend(parse_inline(cell))
        nodes.append({"tag": "p", "children": children})
    return nodes


def parse_image_block(block: str):
    """If block is exactly one image, return figure node; else None."""
    s = block.strip()
    m = IMAGE_RE.fullmatch(s)
    if not m:
        return None
    alt, src = m.group(1), m.group(2)
    children = [{"tag": "img", "attrs": {"src": src}}]
    if alt:
        children.append({"tag": "figcaption",
                         "children": parse_inline(alt)})
    return [{"tag": "figure", "children": children}]


def md_to_nodes(md: str):
    """Convert markdown to telegraph node list. Returns (title, nodes)."""
    lines = md.splitlines()
    title = None
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("# ") and title is None:
            title = line[2:].strip()
            body_start = i + 1
            break
    if title is None:
        title = "Untitled"
    body = "\n".join(lines[body_start:])

    nodes = []
    for raw in re.split(r"\n\s*\n", body):
        block = raw.strip("\n")
        if not block.strip():
            continue
        stripped = block.strip()
        if stripped == "---":
            nodes.append({"tag": "hr"})
            continue
        if stripped.startswith("#### "):
            nodes.append({"tag": "h4",
                          "children": parse_inline(stripped[5:].strip())})
            continue
        if stripped.startswith("### "):
            nodes.append({"tag": "h3",
                          "children": parse_inline(stripped[4:].strip())})
            continue
        if stripped.startswith("## "):
            nodes.append({"tag": "h3",
                          "children": parse_inline(stripped[3:].strip())})
            continue
        # image block
        img_nodes = parse_image_block(block)
        if img_nodes:
            nodes.extend(img_nodes)
            continue
        # table block
        if stripped.startswith("|") or stripped.startswith("| "):
            table_nodes = parse_table_block(block)
            if table_nodes:
                nodes.extend(table_nodes)
                continue
        text = re.sub(r"\s*\n\s*", " ", stripped)
        nodes.append({"tag": "p", "children": parse_inline(text)})
    return title, nodes


# ----- Local image auto-upload -------------------------------------------

def preprocess_local_images(md: str, base_dir: Path) -> str:
    """Find ![alt](local-path) and replace local-path with uploaded URL."""
    def replace(m):
        alt, src = m.group(1), m.group(2)
        if src.startswith(("http://", "https://", "data:")):
            return m.group(0)
        local_path = (base_dir / src).expanduser()
        if not local_path.exists():
            return m.group(0)
        try:
            url = upload_image(local_path)
        except Exception as exc:
            print(f"image upload failed for {src}: {exc}", file=sys.stderr)
            return m.group(0)
        print(f"uploaded {src} → {url}", file=sys.stderr)
        return f"![{alt}]({url})"
    return IMAGE_RE.sub(replace, md)


# ----- CLI ----------------------------------------------------------------

def extract_path(value: str) -> str:
    """Accept 'My-Title-05-27' or full URL — return path portion."""
    if value.startswith("http://") or value.startswith("https://"):
        return urllib.parse.urlparse(value).path.lstrip("/")
    return value.lstrip("/")


def build_parser():
    p = argparse.ArgumentParser(
        prog="telegraph-publish",
        description="Publish or edit a Markdown post on telegra.ph.",
        epilog=(
            "Supports headings h3/h4 (from ###/####), paragraphs, hr (---),\n"
            "tables (rendered as one paragraph per row), images (as figure),\n"
            "**bold**, *italic*, `code`, [text](url).\n"
            "Account is cached in ~/.config/telegraph/account.json.\n"
            "Env: TELEGRAPH_SHORT_NAME, TELEGRAPH_AUTHOR."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("file", nargs="?", help="Markdown file to publish")
    p.add_argument("--dry-run", action="store_true",
                   help="parse only, print stats, do not call API")
    p.add_argument("--edit", metavar="PATH_OR_URL",
                   help="update existing page instead of creating new one")
    p.add_argument("--upload-image", metavar="FILE",
                   help="upload an image file and print its URL (standalone)")
    p.add_argument("--no-image-upload", action="store_true",
                   help="do not auto-upload local images referenced in md")
    return p


def cmd_upload_only(image_path: str):
    url = upload_image(Path(image_path).expanduser())
    print(url)


def cmd_publish(args):
    path = Path(args.file).expanduser()
    md = path.read_text()
    if not args.no_image_upload and not args.dry_run:
        md = preprocess_local_images(md, path.parent)
    title, nodes = md_to_nodes(md)

    if args.dry_run:
        kinds = {}
        for n in nodes:
            tag = n.get("tag", "?") if isinstance(n, dict) else "text"
            kinds[tag] = kinds.get(tag, 0) + 1
        print(f"title: {title}")
        print(f"blocks: {len(nodes)}")
        print(f"tags:  {kinds}")
        for n in nodes[:3]:
            print(json.dumps(n, ensure_ascii=False)[:200])
        return

    short_name = os.environ.get("TELEGRAPH_SHORT_NAME", "Anonymous")
    author_name = os.environ.get("TELEGRAPH_AUTHOR", short_name)
    access_token = ensure_account(short_name, author_name)

    params = {
        "access_token": access_token,
        "title": title,
        "author_name": author_name,
        "content": nodes,
        "return_content": "false",
    }
    if args.edit:
        params["path"] = extract_path(args.edit)
        result = api_call("editPage", params)
    else:
        result = api_call("createPage", params)
    print(result["url"])


def main():
    args = build_parser().parse_args()
    if args.upload_image:
        cmd_upload_only(args.upload_image)
        return
    if not args.file:
        build_parser().print_help(sys.stderr)
        sys.exit(1)
    cmd_publish(args)


if __name__ == "__main__":
    main()
