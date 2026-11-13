#!/usr/bin/env python3
"""Poll Microsoft's macOS service-status RSS feed and print incident updates."""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from typing import NamedTuple

FEED_URL = "https://status.cloud.microsoft/api/feed/mac"
POLL_INTERVAL_SECONDS = 5 * 60


def clear_terminal() -> None:
    if sys.stdout.isatty():
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()


class Incident(NamedTuple):
    key: str
    title: str
    published: str
    status: str
    link: str
    description: str


class _DescriptionParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"br", "div", "p", "li"}:
            self.parts.append("\n")
        if tag == "li":
            self.parts.append("- ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"div", "p", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def format_description(description: str) -> str:
    parser = _DescriptionParser()
    parser.feed(description)
    lines = (" ".join(line.split()) for line in "".join(parser.parts).splitlines())
    return "\n".join(line for line in lines if line)


def fetch_incidents() -> list[Incident]:
    request = urllib.request.Request(
        FEED_URL,
        headers={"User-Agent": "m365-status-watcher/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        root = ET.fromstring(response.read())

    incidents = []
    for item in root.findall("./channel/item"):
        def text(tag: str) -> str:
            element = item.find(tag)
            return (element.text or "").strip() if element is not None else ""

        title = text("title") or "Untitled incident"
        link = text("link")
        key = text("guid") or link or title
        incidents.append(
            Incident(
                key=key,
                title=title,
                published=text("pubDate"),
                status=text("status"),
                link=link,
                description=format_description(text("description")),
            )
        )
    return incidents


def print_incident(incident: Incident) -> None:
    print(f"\n{incident.title}")
    print("=" * len(incident.title))
    if incident.status:
        print(f"Status:    {incident.status}")
    if incident.published:
        print(f"Published: {incident.published}")
    if incident.link:
        print(f"Link:      {incident.link}")
    if incident.description:
        print(f"\n{incident.description}")
    print(flush=True)


def poll(previous: dict[str, Incident] | None) -> dict[str, Incident]:
    incidents = fetch_incidents()
    current = {incident.key: incident for incident in incidents}
    changed = [
        incident
        for incident in incidents
        if previous is None or previous.get(incident.key) != incident
    ]

    if not changed:
        return current

    clear_terminal()
    for incident in changed:
        print_incident(incident)
    checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"\nCurrent time (UTC): {checked_at}", flush=True)
    return current


def main() -> int:
    clear_terminal()
    print(f"Watching Microsoft 365 status feed: {FEED_URL}")
    print("Checking now; refreshing every 5 minutes. Press Ctrl+C to stop.")

    try:
        known_incidents = poll(None)
    except (OSError, urllib.error.URLError, ET.ParseError) as error:
        print(f"Unable to read the status feed: {error}", file=sys.stderr)
        return 1

    while True:
        try:
            time.sleep(POLL_INTERVAL_SECONDS)
            known_incidents = poll(known_incidents)
        except KeyboardInterrupt:
            print("\nStopped.")
            return 0
        except (OSError, urllib.error.URLError, ET.ParseError) as error:
            print(f"Status feed check failed: {error}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
