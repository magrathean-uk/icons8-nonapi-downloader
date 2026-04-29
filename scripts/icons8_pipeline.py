#!/usr/bin/env python3
"""Icons8 Liquid Glass search, SVG download, theming, and render pipeline."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


MCP_URL = "https://mcp.icons8.com/mcp/"
IMG_URL = "https://api-img.icons8.com/"


def chrome_public_api_key() -> str:
    cookie_db = Path.home() / "Library/Application Support/Google/Chrome/Default/Cookies"
    password = subprocess.check_output(
        ["security", "find-generic-password", "-wa", "Chrome"],
        text=True,
    ).strip().encode()
    key = hashlib.pbkdf2_hmac("sha1", password, b"saltysalt", 1003, 16)
    iv = b" " * 16

    cookies: dict[str, str] = {}
    query = """
        select host_key, name, encrypted_value
        from cookies
        where host_key like '%icons8%'
    """
    for _host, name, encrypted in sqlite3.connect(cookie_db).execute(query):
        data = encrypted[3:] if encrypted.startswith(b"v10") else encrypted
        decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
        decoded = decryptor.update(data) + decryptor.finalize()
        pad = decoded[-1]
        if 1 <= pad <= 16:
            decoded = decoded[:-pad]
        if len(decoded) > 32:
            decoded = decoded[32:]
        try:
            cookies[name] = decoded.decode()
        except UnicodeDecodeError:
            continue

    token = cookies.get("i8token")
    if not token:
        raise RuntimeError("Chrome profile is missing Icons8 i8token cookie")
    payload = token.split(".")[1]
    payload += "=" * ((4 - len(payload) % 4) % 4)
    data = json.loads(base64.urlsafe_b64decode(payload))
    public_key = data.get("publicApiKey")
    if not public_key:
        raise RuntimeError("Icons8 i8token has no publicApiKey")
    return public_key


def public_api_key() -> str:
    key = os.environ.get("ICONS8_PUBLIC_API_KEY")
    if key:
        return key
    raise RuntimeError("Set ICONS8_PUBLIC_API_KEY or run token-from-chrome")


def mcp_search(query: str, amount: int) -> dict[str, Any]:
    payload = {
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000) % 1_000_000,
        "method": "tools/call",
        "params": {
            "name": "search_icons",
            "arguments": {
                "query": query,
                "platform": "liquid-glass",
                "amount": amount,
            },
        },
    }
    request = urllib.request.Request(
        MCP_URL,
        data=json.dumps(payload).encode(),
        headers={"Accept": "application/json, text/event-stream", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        rpc = json.loads(response.read())
    if "error" in rpc:
        raise RuntimeError(rpc["error"])
    return json.loads(rpc["result"]["content"][0]["text"])


def score_icon(icon: dict[str, Any], query: str) -> int:
    haystack = " ".join(str(icon.get(key, "")) for key in ("name", "commonName", "category", "subcategory")).lower()
    score = 10 if icon.get("platform") == "liquid-glass" else 0
    score += 2 if icon.get("isColor") else 0
    for token in query.lower().replace("-", " ").split():
        if token and token in haystack:
            score += 3
    return score


def pick_icon(result: dict[str, Any], query: str) -> dict[str, Any] | None:
    icons = result.get("icons") or []
    if not icons:
        return None
    return max(icons, key=lambda icon: score_icon(icon, query))


def load_overrides(path: Path | None) -> dict[str, dict[str, str]]:
    if not path:
        return {}
    rows = csv.DictReader(path.open())
    overrides: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("asset_key") and row.get("icons8_id"):
            overrides[row["asset_key"]] = row
    return overrides


def override_icon(asset_key: str, overrides: dict[str, dict[str, str]]) -> dict[str, Any] | None:
    row = overrides.get(asset_key)
    if not row:
        return None
    return {
        "id": row["icons8_id"],
        "name": row.get("icons8_name", ""),
        "commonName": row.get("icons8_common_name", ""),
        "platform": "liquid-glass",
        "isColor": True,
    }


def download_svg(icon_id: str, key: str) -> bytes:
    params = urllib.parse.urlencode(
        {"id": icon_id, "format": "svg", "size": "512", "fromSite": "true", "token": key}
    )
    request = urllib.request.Request(
        f"{IMG_URL}?{params}",
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://icons8.com/"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read()
    if b"<svg" not in data:
        raise RuntimeError(data[:160].decode(errors="replace"))
    return data


def command_token_from_chrome(_args: argparse.Namespace) -> None:
    print(f"export ICONS8_PUBLIC_API_KEY={chrome_public_api_key()!r}")


def command_download(args: argparse.Namespace) -> None:
    key = public_api_key()
    args.out.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(args.queries.open()))
    overrides = load_overrides(args.overrides)
    resolved: list[dict[str, Any]] = []
    failed: list[dict[str, str]] = []

    for index, row in enumerate(rows, start=1):
        asset_key = row["asset_key"]
        query = row["icons8_query"]
        try:
            result = {} if asset_key in overrides else mcp_search(query, args.amount)
            icon = override_icon(asset_key, overrides) or pick_icon(result, query)
            if not icon:
                raise RuntimeError("no Icons8 result")
            svg = download_svg(icon["id"], key)
            svg_file = args.out / f"{asset_key}.svg"
            svg_file.write_bytes(svg)
            resolved.append(
                {
                    "asset_key": asset_key,
                    "icons8_query": query,
                    "sf_symbols": row.get("sf_symbols", ""),
                    "icons8_id": icon.get("id", ""),
                    "icons8_name": icon.get("name", ""),
                    "icons8_common_name": icon.get("commonName", ""),
                    "svg_file": str(svg_file),
                    "status": "downloaded",
                }
            )
            print(f"{index:03}/{len(rows)} ok {asset_key} -> {icon.get('name')}", flush=True)
        except Exception as exc:
            failed.append(
                {
                    "asset_key": asset_key,
                    "icons8_query": query,
                    "sf_symbols": row.get("sf_symbols", ""),
                    "error": str(exc),
                }
            )
            print(f"{index:03}/{len(rows)} fail {asset_key}: {exc}", flush=True)
        time.sleep(args.pause)

    args.resolved.parent.mkdir(parents=True, exist_ok=True)
    with args.resolved.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "asset_key",
                "icons8_query",
                "sf_symbols",
                "icons8_id",
                "icons8_name",
                "icons8_common_name",
                "svg_file",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(resolved)

    args.failed.parent.mkdir(parents=True, exist_ok=True)
    with args.failed.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["asset_key", "icons8_query", "sf_symbols", "error"])
        writer.writeheader()
        writer.writerows(failed)

    print(f"resolved={len(resolved)} failed={len(failed)}")
    if failed:
        raise SystemExit(1)


def color_for_opacity(opacity: float) -> str:
    if opacity >= 0.64:
        return "#F8FBFF"
    if opacity >= 0.54:
        return "#6BD8FF"
    if opacity >= 0.40:
        return "#20D7E8"
    return "#1A26FF"


def attr_value(tag: str, name: str, default: str) -> str:
    match = re.search(rf'{name}="([^"]+)"', tag)
    return match.group(1) if match else default


def theme_stop(match: re.Match[str]) -> str:
    tag = match.group(0)
    opacity = float(attr_value(tag, "stop-opacity", "1"))
    color = color_for_opacity(opacity)
    return re.sub(r'stop-color="#(?:fff|ffffff)"', f'stop-color="{color}"', tag, flags=re.IGNORECASE)


def theme_svg(svg: str) -> str:
    themed = re.sub(r"<stop\b[^>]*>", theme_stop, svg)
    themed = re.sub(r'fill="#999"', 'fill="#20D7E8"', themed, flags=re.IGNORECASE)
    themed = re.sub(r'fill="#4c4c4c"', 'fill="#1A26FF"', themed, flags=re.IGNORECASE)
    themed = re.sub(r'stroke="#999"', 'stroke="#20D7E8"', themed, flags=re.IGNORECASE)
    themed = re.sub(r'stroke="#4c4c4c"', 'stroke="#1A26FF"', themed, flags=re.IGNORECASE)
    return themed.replace('width="48px"', 'width="512px"').replace('height="48px"', 'height="512px"')


def command_theme(args: argparse.Namespace) -> None:
    args.out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for source in sorted(args.in_dir.glob("*.svg")):
        (args.out_dir / source.name).write_text(theme_svg(source.read_text(errors="ignore")), encoding="utf-8")
        count += 1
    print(f"themed={count}")


def command_render(args: argparse.Namespace) -> None:
    if not shutil.which("rsvg-convert"):
        raise RuntimeError("rsvg-convert missing; install librsvg")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for source in sorted(args.in_dir.glob("*.svg")):
        output = args.out_dir / f"{source.stem}.png"
        with output.open("wb") as handle:
            subprocess.run(
                ["rsvg-convert", "-w", str(args.size), "-h", str(args.size), str(source)],
                check=True,
                stdout=handle,
            )
        count += 1
    print(f"rendered={count}")


def command_contact_sheet(args: argparse.Namespace) -> None:
    from PIL import Image, ImageDraw, ImageFont

    rows = list(csv.DictReader(args.resolved.open()))
    thumb = args.thumb
    label_h = 30
    pad = 14
    cols = args.cols
    sheet_rows = (len(rows) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (thumb + pad * 2), sheet_rows * (thumb + label_h + pad * 2)), (6, 9, 20))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 9)
    except OSError:
        font = None

    for index, row in enumerate(rows):
        x = (index % cols) * (thumb + pad * 2) + pad
        y = (index // cols) * (thumb + label_h + pad * 2) + pad
        image = Image.open(args.png_dir / f"{row['asset_key']}.png").convert("RGBA").resize((thumb, thumb))
        sheet.paste(image, (x, y), image)
        draw.text((x, y + thumb + 4), row["asset_key"].replace("lg_", "")[:18], fill=(248, 251, 255), font=font)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    print(args.out)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(required=True)

    token = sub.add_parser("token-from-chrome")
    token.set_defaults(func=command_token_from_chrome)

    download = sub.add_parser("download")
    download.add_argument("--queries", type=Path, required=True)
    download.add_argument("--overrides", type=Path)
    download.add_argument("--out", type=Path, required=True)
    download.add_argument("--resolved", type=Path, required=True)
    download.add_argument("--failed", type=Path, required=True)
    download.add_argument("--amount", type=int, default=5)
    download.add_argument("--pause", type=float, default=0.08)
    download.set_defaults(func=command_download)

    theme = sub.add_parser("theme")
    theme.add_argument("--in-dir", type=Path, required=True)
    theme.add_argument("--out-dir", type=Path, required=True)
    theme.set_defaults(func=command_theme)

    render = sub.add_parser("render")
    render.add_argument("--in-dir", type=Path, required=True)
    render.add_argument("--out-dir", type=Path, required=True)
    render.add_argument("--size", type=int, default=512)
    render.set_defaults(func=command_render)

    contact = sub.add_parser("contact-sheet")
    contact.add_argument("--png-dir", type=Path, required=True)
    contact.add_argument("--resolved", type=Path, required=True)
    contact.add_argument("--out", type=Path, required=True)
    contact.add_argument("--thumb", type=int, default=72)
    contact.add_argument("--cols", type=int, default=8)
    contact.set_defaults(func=command_contact_sheet)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
