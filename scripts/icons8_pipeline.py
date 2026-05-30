#!/usr/bin/env python3
"""Icons8 Liquid Glass search, SVG download, theming, and render pipeline."""

from __future__ import annotations

import argparse
import base64
import concurrent.futures
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
ICONS8_URL = "https://icons8.com"
NUXT_WRAPPERS = {"Reactive", "ShallowReactive", "Ref", "ShallowRef"}
SET_PAGE_RE = re.compile(r"/icons/set/(?P<category>[^/?#\"'<>]+?)--style-(?P<style>[^/?#\"'<>]+)")
NUXT_DATA_RE = re.compile(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL)
PAGE_MANIFEST_FIELDS = [
    "source_url",
    "category",
    "style",
    "subcategory_code",
    "subcategory_name",
    "icons8_id",
    "name",
    "common_name",
    "slug",
    "asset_key",
    "icon_url",
]


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


def canonical_icons8_url(url: str, base_url: str = ICONS8_URL) -> str:
    absolute = urllib.parse.urljoin(base_url, url)
    parsed = urllib.parse.urlparse(absolute)
    return urllib.parse.urlunparse(("https", "icons8.com", parsed.path.rstrip("/"), "", "", ""))


def set_page_parts(url: str) -> tuple[str, str] | None:
    match = SET_PAGE_RE.search(urllib.parse.urlparse(url).path)
    if not match:
        return None
    return match.group("category"), match.group("style")


def root_page_style(url: str) -> str | None:
    path = urllib.parse.urlparse(url).path.strip("/")
    parts = path.split("/")
    if len(parts) == 2 and parts[0] == "icons" and parts[1] != "set":
        return parts[1]
    return None


def clean_slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-").lower()
    return cleaned or "icon"


def icon_slug(icon_url: str, common_name: str, icon_id: str) -> str:
    parsed = urllib.parse.urlparse(icon_url)
    slug = parsed.path.rstrip("/").split("/")[-1] if parsed.path else ""
    return clean_slug(slug or common_name or icon_id)


def fetch_text(url: str, timeout: int) -> str:
    request = urllib.request.Request(
        canonical_icons8_url(url),
        headers={"User-Agent": "Mozilla/5.0", "Referer": ICONS8_URL},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="ignore")


def extract_set_page_urls(html: str, source_url: str) -> list[str]:
    source_style = root_page_style(source_url) or (set_page_parts(source_url) or ("", ""))[1]
    normalized_html = html.replace("\\u002F", "/")
    urls: list[str] = []
    seen: set[str] = set()
    for match in SET_PAGE_RE.finditer(normalized_html):
        category = match.group("category")
        style = match.group("style")
        if source_style and style != source_style:
            continue
        page = canonical_icons8_url(f"/icons/set/{category}--style-{style}")
        if page not in seen:
            seen.add(page)
            urls.append(page)
    return urls


def nuxt_payload(html: str) -> list[Any]:
    match = NUXT_DATA_RE.search(html)
    if not match:
        raise RuntimeError("Icons8 page has no __NUXT_DATA__ payload")
    return json.loads(match.group(1))


def nuxt_value(payload: list[Any], value: Any) -> Any:
    while isinstance(value, int):
        if value < 0 or value >= len(payload):
            raise RuntimeError(f"Nuxt reference out of range: {value}")
        value = payload[value]
    if isinstance(value, list) and len(value) == 2 and value[0] in NUXT_WRAPPERS:
        return nuxt_value(payload, value[1])
    return value


def nuxt_text(payload: list[Any], value: Any) -> str:
    value = nuxt_value(payload, value)
    if isinstance(value, dict):
        if "en-US" in value:
            return nuxt_text(payload, value["en-US"])
        for item in value.values():
            text = nuxt_text(payload, item)
            if text:
                return text
        return ""
    return "" if value is None else str(value)


def nuxt_data_entries(payload: list[Any]) -> list[dict[str, Any]]:
    root = nuxt_value(payload, payload[0])
    data = nuxt_value(payload, root.get("data", {})) if isinstance(root, dict) else {}
    if not isinstance(data, dict):
        raise RuntimeError("Icons8 page has no Nuxt data object")
    entries: list[dict[str, Any]] = []
    for value in data.values():
        entry = nuxt_value(payload, value)
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def find_category_data(payload: list[Any]) -> dict[str, Any]:
    for entry in nuxt_data_entries(payload):
        if "categoryData" in entry:
            category_data = nuxt_value(payload, entry["categoryData"])
            if isinstance(category_data, dict):
                return category_data
    raise RuntimeError("Icons8 page has no categoryData payload")


def find_icons_data(payload: list[Any]) -> dict[str, Any]:
    for entry in nuxt_data_entries(payload):
        if "iconsData" in entry:
            icons_data = nuxt_value(payload, entry["iconsData"])
            if isinstance(icons_data, dict):
                return icons_data
    raise RuntimeError("Icons8 page has no iconsData payload")


def row_from_icon(
    payload: list[Any],
    icon: dict[str, Any],
    source_url: str,
    category: str,
    style: str,
    subcategory_code: str,
    subcategory_name: str,
) -> dict[str, str] | None:
    icon_id = nuxt_text(payload, icon.get("id", ""))
    name = nuxt_text(payload, icon.get("name", ""))
    common_name = nuxt_text(payload, icon.get("commonName", ""))
    icon_url = nuxt_text(payload, icon.get("url", ""))
    if not icon_id:
        return None
    slug = icon_slug(icon_url, common_name, icon_id)
    if not icon_url:
        icon_url = f"/icon/{icon_id}/{slug}"
    asset_key = f"{category}--style-{style}__{slug}"
    return {
        "source_url": canonical_icons8_url(source_url),
        "category": category,
        "style": style,
        "subcategory_code": subcategory_code,
        "subcategory_name": subcategory_name,
        "icons8_id": icon_id,
        "name": name,
        "common_name": common_name,
        "slug": slug,
        "asset_key": asset_key,
        "icon_url": urllib.parse.urljoin(ICONS8_URL, icon_url),
    }


def extract_category_data_icons(
    payload: list[Any], source_url: str, category: str, style: str
) -> list[dict[str, str]]:
    parts = set_page_parts(source_url)
    if not parts:
        raise RuntimeError(f"not an Icons8 set page: {source_url}")
    category_data = find_category_data(payload)
    category_payload = nuxt_value(payload, category_data.get("category", {}))
    subcategories = nuxt_value(payload, category_payload.get("subcategory", []))
    if not isinstance(subcategories, list):
        raise RuntimeError("Icons8 category payload has no subcategory list")

    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for subcategory_ref in subcategories:
        subcategory = nuxt_value(payload, subcategory_ref)
        if not isinstance(subcategory, dict):
            continue
        subcategory_code = nuxt_text(payload, subcategory.get("code", ""))
        subcategory_name = nuxt_text(payload, subcategory.get("name", ""))
        icon_refs = nuxt_value(payload, subcategory.get("icons", []))
        if not isinstance(icon_refs, list):
            continue
        for icon_ref in icon_refs:
            icon = nuxt_value(payload, icon_ref)
            if not isinstance(icon, dict):
                continue
            row = row_from_icon(
                payload, icon, source_url, category, style, subcategory_code, subcategory_name
            )
            if not row:
                continue
            unique_key = (row["icons8_id"], row["slug"])
            if unique_key in seen:
                continue
            seen.add(unique_key)
            rows.append(row)
    return rows


def extract_icons_data_icons(payload: list[Any], source_url: str, category: str, style: str) -> list[dict[str, str]]:
    icons_data = find_icons_data(payload)
    icon_refs = nuxt_value(payload, icons_data.get("icons", []))
    if not isinstance(icon_refs, list):
        raise RuntimeError("Icons8 iconsData payload has no icons list")
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for icon_ref in icon_refs:
        icon = nuxt_value(payload, icon_ref)
        if not isinstance(icon, dict):
            continue
        subcategory_name = nuxt_text(payload, icon.get("subcategory", ""))
        subcategory_code = clean_slug(subcategory_name)
        row = row_from_icon(payload, icon, source_url, category, style, subcategory_code, subcategory_name)
        if not row:
            continue
        unique_key = (row["icons8_id"], row["slug"])
        if unique_key in seen:
            continue
        seen.add(unique_key)
        rows.append(row)
    return rows


def extract_category_icons_from_html(html: str, source_url: str) -> list[dict[str, str]]:
    parts = set_page_parts(source_url)
    if not parts:
        raise RuntimeError(f"not an Icons8 set page: {source_url}")
    category, style = parts
    payload = nuxt_payload(html)
    try:
        return extract_category_data_icons(payload, source_url, category, style)
    except RuntimeError as category_error:
        try:
            return extract_icons_data_icons(payload, source_url, category, style)
        except RuntimeError:
            raise category_error


def ensure_unique_asset_keys(rows: list[dict[str, str]]) -> None:
    owners: dict[str, str] = {}
    for row in rows:
        asset_key = row["asset_key"]
        icon_id = row["icons8_id"]
        previous = owners.get(asset_key)
        if previous and previous != icon_id:
            raise ValueError(f"output collision for {asset_key}: {previous} and {icon_id}")
        owners[asset_key] = icon_id


def make_asset_key(category: str, style: str, slug: str) -> str:
    return f"{category}--style-{style}__{slug}"


def disambiguate_asset_key_collisions(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    fixed = [dict(row) for row in rows]
    groups: dict[str, list[int]] = {}
    for index, row in enumerate(fixed):
        groups.setdefault(row["asset_key"], []).append(index)

    for asset_key, indexes in groups.items():
        icon_ids = {fixed[index]["icons8_id"] for index in indexes}
        if len(icon_ids) <= 1:
            continue
        used = {row["asset_key"] for row in fixed if row["asset_key"] != asset_key}
        for index in indexes:
            row = fixed[index]
            base_slug = clean_slug(row.get("common_name") or row.get("slug") or row["icons8_id"])
            candidate = make_asset_key(row["category"], row["style"], base_slug)
            if candidate in used:
                base_slug = clean_slug(f"{base_slug}-{row['icons8_id']}")
                candidate = make_asset_key(row["category"], row["style"], base_slug)
            row["slug"] = base_slug
            row["asset_key"] = candidate
            used.add(candidate)
    ensure_unique_asset_keys(fixed)
    return fixed


def dedupe_manifest_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (row["asset_key"], row["icons8_id"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    deduped = disambiguate_asset_key_collisions(deduped)
    ensure_unique_asset_keys(deduped)
    return deduped


def collect_page_manifest(urls: list[str], expand_root: bool, timeout: int) -> list[dict[str, str]]:
    queue = [canonical_icons8_url(url) for url in urls]
    seen_pages: set[str] = set()
    rows: list[dict[str, str]] = []
    while queue:
        url = queue.pop(0)
        if url in seen_pages:
            continue
        seen_pages.add(url)
        html = fetch_text(url, timeout)
        if expand_root and root_page_style(url):
            for set_url in extract_set_page_urls(html, url):
                if set_url not in seen_pages and set_url not in queue:
                    queue.append(set_url)
            continue
        if set_page_parts(url):
            page_rows = extract_category_icons_from_html(html, url)
            print(f"{url} icons={len(page_rows)}", flush=True)
            rows.extend(page_rows)
            continue
        raise RuntimeError(f"unsupported Icons8 page URL: {url}")
    return dedupe_manifest_rows(rows)


def write_manifest_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PAGE_MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_manifest_json(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_urls(args: argparse.Namespace) -> list[str]:
    urls = list(args.url or [])
    if args.urls_file:
        urls.extend(line.strip() for line in args.urls_file.read_text().splitlines() if line.strip())
    if not urls:
        raise RuntimeError("pass at least one --url or --urls-file")
    return urls


def command_page_manifest(args: argparse.Namespace) -> None:
    rows = collect_page_manifest(read_urls(args), expand_root=not args.no_expand_root, timeout=args.timeout)
    if not rows:
        raise RuntimeError("no Icons8 icons found")
    write_manifest_csv(rows, args.out)
    if args.json_out:
        write_manifest_json(rows, args.json_out)
    print(f"manifest={len(rows)}")


def download_svg(icon_id: str, key: str, size: int = 512) -> bytes:
    params = urllib.parse.urlencode(
        {"id": icon_id, "format": "svg", "size": str(size), "fromSite": "true", "token": key}
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


def command_download_manifest(args: argparse.Namespace) -> None:
    key = public_api_key()
    rows = list(csv.DictReader(args.manifest.open(encoding="utf-8")))
    if not rows:
        raise RuntimeError("manifest is empty")
    ensure_unique_asset_keys(rows)
    args.out.mkdir(parents=True, exist_ok=True)
    results: dict[int, tuple[dict[str, str] | None, dict[str, str] | None]] = {}

    def download_one(index: int, row: dict[str, str]) -> tuple[int, dict[str, str] | None, dict[str, str] | None]:
        asset_key = row["asset_key"]
        icon_id = row["icons8_id"]
        try:
            svg = download_svg(icon_id, key, args.size)
            svg_file = args.out / f"{asset_key}.svg"
            svg_file.write_bytes(svg)
            time.sleep(args.pause)
            return index, {**row, "svg_file": str(svg_file), "status": "downloaded"}, None
        except Exception as exc:
            return index, None, {**row, "error": str(exc)}

    if args.workers <= 1:
        for index, row in enumerate(rows, start=1):
            result_index, resolved_row, failed_row = download_one(index, row)
            results[result_index] = (resolved_row, failed_row)
            if failed_row:
                print(f"{index:03}/{len(rows)} fail {row['asset_key']}: {failed_row['error']}", flush=True)
            else:
                print(f"{index:03}/{len(rows)} ok {row['asset_key']}", flush=True)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(download_one, index, row) for index, row in enumerate(rows, start=1)]
            for future in concurrent.futures.as_completed(futures):
                result_index, resolved_row, failed_row = future.result()
                row = rows[result_index - 1]
                results[result_index] = (resolved_row, failed_row)
                if failed_row:
                    print(f"{result_index:03}/{len(rows)} fail {row['asset_key']}: {failed_row['error']}", flush=True)
                else:
                    print(f"{result_index:03}/{len(rows)} ok {row['asset_key']}", flush=True)

    resolved = [results[index][0] for index in sorted(results) if results[index][0]]
    failed = [results[index][1] for index in sorted(results) if results[index][1]]

    resolved_fields = PAGE_MANIFEST_FIELDS + ["svg_file", "status"]
    args.resolved.parent.mkdir(parents=True, exist_ok=True)
    with args.resolved.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=resolved_fields)
        writer.writeheader()
        writer.writerows(resolved)

    failed_fields = PAGE_MANIFEST_FIELDS + ["error"]
    args.failed.parent.mkdir(parents=True, exist_ok=True)
    with args.failed.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=failed_fields)
        writer.writeheader()
        writer.writerows(failed)

    print(f"resolved={len(resolved)} failed={len(failed)}")
    if failed:
        raise SystemExit(1)


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

    page_manifest = sub.add_parser("page-manifest")
    page_manifest.add_argument("--url", action="append")
    page_manifest.add_argument("--urls-file", type=Path)
    page_manifest.add_argument("--out", type=Path, required=True)
    page_manifest.add_argument("--json-out", type=Path)
    page_manifest.add_argument("--no-expand-root", action="store_true")
    page_manifest.add_argument("--timeout", type=int, default=30)
    page_manifest.set_defaults(func=command_page_manifest)

    download_manifest = sub.add_parser("download-manifest")
    download_manifest.add_argument("--manifest", type=Path, required=True)
    download_manifest.add_argument("--out", type=Path, required=True)
    download_manifest.add_argument("--resolved", type=Path, required=True)
    download_manifest.add_argument("--failed", type=Path, required=True)
    download_manifest.add_argument("--size", type=int, default=512)
    download_manifest.add_argument("--pause", type=float, default=0.08)
    download_manifest.add_argument("--workers", type=int, default=1)
    download_manifest.set_defaults(func=command_download_manifest)

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
