#!/usr/bin/env python3
"""Discover SF Symbol usage in a SwiftUI source tree."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


PLAIN_SYMBOLS = {
    "bolt",
    "calendar",
    "checkmark",
    "circle",
    "clock",
    "eye",
    "globe",
    "house",
    "leaf",
    "map",
    "memorychip",
    "network",
    "play",
    "plus",
    "powerplug",
    "sparkles",
    "speedometer",
    "steeringwheel",
    "stethoscope",
    "trash",
    "xmark",
}

NON_ICONS = {
    "overview",
    "battery",
    "drives",
    "trips",
    "settings",
    "close",
    "delete",
    "home",
}

MANUAL_QUERIES = {
    "battery.100percent": "battery full",
    "battery.75percent": "battery level",
    "battery.100percent.bolt": "car battery charging",
    "bolt": "lightning bolt",
    "bolt.fill": "lightning bolt",
    "bolt.circle.fill": "lightning bolt",
    "bolt.car": "electric car charging",
    "bolt.slash": "flash off",
    "bolt.slash.fill": "flash off",
    "bolt.trianglebadge.exclamationmark": "electric warning",
    "bolt.badge.clock.fill": "charging time",
    "car.fill": "car",
    "car.circle": "car",
    "car.side": "sedan",
    "car.side.fill": "sedan",
    "car.rear.waves.up": "parking sensor",
    "map": "map",
    "map.fill": "map",
    "road.lanes": "road",
    "steeringwheel": "steering wheel",
    "gearshape.fill": "settings",
    "server.rack": "server",
    "cylinder.fill": "database",
    "externaldrive.fill": "external drive",
    "network": "network",
    "person.crop.circle.fill": "user",
    "key.fill": "key",
    "lock.fill": "lock",
    "lock.shield.fill": "security shield",
    "eye": "eye",
    "eye.slash": "hide",
    "eye.slash.fill": "hide",
    "chart.line.uptrend.xyaxis": "line chart up",
    "chart.line.downtrend.xyaxis": "line chart down",
    "chart.bar.xaxis": "bar chart",
    "waveform.path.ecg": "health graph",
    "heart.fill": "heart",
    "leaf": "leaf",
    "leaf.fill": "leaf",
    "drop.fill": "water drop",
    "thermometer.medium": "thermometer",
    "thermometer.snowflake": "cold thermometer",
    "thermometer.sun.fill": "hot thermometer",
    "stethoscope": "stethoscope",
    "memorychip": "microchip",
    "wrench.and.screwdriver.fill": "tools",
    "trash": "trash",
    "trash.fill": "trash",
    "plus": "plus",
    "plus.circle": "plus",
    "checkmark": "checkmark",
    "checkmark.circle.fill": "checkmark",
    "checkmark.seal": "verified",
    "checkmark.seal.fill": "verified",
    "xmark": "close",
    "xmark.circle": "cancel",
    "xmark.circle.fill": "cancel",
    "exclamationmark.triangle.fill": "warning",
    "exclamationmark.circle.fill": "error",
    "exclamationmark.octagon.fill": "error",
    "info.circle.fill": "info",
    "number.circle.fill": "number",
    "arrow.clockwise": "refresh",
    "arrow.triangle.2.circlepath": "sync",
    "arrow.down.circle": "download",
    "tray.and.arrow.down": "download tray",
    "arrow.uturn.backward": "undo",
    "arrow.left.and.right": "horizontal arrows",
    "arrow.up.left.and.arrow.down.right": "expand",
    "chevron.backward": "back",
    "chevron.left": "back",
    "chevron.right": "next",
    "chevron.down": "down",
    "chevron.up.chevron.down": "sort",
    "play.fill": "play",
    "pause.fill": "pause",
    "forward.fill": "fast forward",
    "forward.circle.fill": "fast forward",
    "camera.fill": "camera",
    "calendar": "calendar",
    "clock": "clock",
    "clock.fill": "clock",
    "clock.arrow.circlepath": "history",
    "globe": "globe",
    "globe.americas.fill": "globe",
    "globe.europe.africa": "globe",
    "building.2": "city",
    "building.2.fill": "city",
    "building.columns.fill": "bank",
    "house": "home",
    "paintpalette.fill": "palette",
    "ruler.fill": "ruler",
    "envelope.fill": "email",
    "square.and.arrow.up": "share",
    "doc.text.magnifyingglass": "document search",
    "sparkles": "sparkles",
    "sparkles.rectangle.stack": "layers",
    "powerplug": "plug",
}


def looks_like_symbol(value: str) -> bool:
    if not value or value in NON_ICONS or value[0].isupper():
        return False
    return "." in value or value in PLAIN_SYMBOLS


def add_symbol(symbols: dict[str, set[str]], value: str, path: Path, line: int) -> None:
    if looks_like_symbol(value):
        symbols.setdefault(value, set()).add(f"{path}:{line}")


def discover(source: Path) -> dict[str, set[str]]:
    symbols: dict[str, set[str]] = {}
    for path in source.rglob("*.swift"):
        text = path.read_text(errors="ignore")
        for line_number, line in enumerate(text.splitlines(), 1):
            if any(key in line for key in ("systemName:", "systemImage:", "icon:")):
                for value in re.findall(r'"([a-z0-9][a-z0-9._]+)"', line):
                    add_symbol(symbols, value, path, line_number)
        for match in re.finditer(
            r'(?:func|var)\s+\w*(?:icon|Icon|systemImage|menuIconName)\w*[^\{]*\{(?P<body>.*?)\n\s*\}',
            text,
            re.S,
        ):
            start = text[: match.start()].count("\n") + 1
            for value in re.findall(r'"([a-z0-9][a-z0-9._]+)"', match.group("body")):
                add_symbol(symbols, value, path, start)
    return symbols


def query_for(symbol: str) -> str:
    if symbol in MANUAL_QUERIES:
        return MANUAL_QUERIES[symbol]
    cleaned = symbol
    if cleaned.endswith(".fill"):
        cleaned = cleaned[:-5]
    cleaned = cleaned.replace(".circle", "")
    return cleaned.replace(".", " ").replace("_", " ")


def asset_key(query: str) -> str:
    return "lg_" + re.sub(r"[^a-z0-9]+", "_", query.lower()).strip("_")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--queries", type=Path, required=True)
    args = parser.parse_args()

    symbols = discover(args.source)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.queries.parent.mkdir(parents=True, exist_ok=True)

    with args.out.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sf_symbol", "asset_key", "icons8_query", "refs"])
        for symbol in sorted(symbols):
            query = query_for(symbol)
            writer.writerow([symbol, asset_key(query), query, ";".join(sorted(symbols[symbol])[:8])])

    grouped: dict[tuple[str, str], list[str]] = {}
    for symbol in sorted(symbols):
        query = query_for(symbol)
        grouped.setdefault((asset_key(query), query), []).append(symbol)

    with args.queries.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["asset_key", "icons8_query", "sf_symbols"])
        for (key, query), grouped_symbols in sorted(grouped.items()):
            writer.writerow([key, query, ";".join(grouped_symbols)])

    print(f"symbols={len(symbols)} assets={len(grouped)}")


if __name__ == "__main__":
    main()
