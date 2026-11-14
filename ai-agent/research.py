import html
import os
import re
import xml.etree.ElementTree as ET
from urllib.parse import quote, urlsplit

import requests

HEADERS = {"User-Agent": "MineOS/1.0 (desktop research; https://github.com/roshandhiman/ai_linux-DIST)"}


def plain(text):
    return html.unescape(re.sub(r"<[^>]+>", "", text or "")).strip()


def search(query):
    if re.search(r'\b(?:today|latest|news|headlines|this week|recent)\b', query, re.IGNORECASE):
        return news(query)
    return references(query)


def references(query):
    key = os.environ.get("BRAVE_SEARCH_API_KEY", "")
    if key:
        result = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": 5},
            headers={"X-Subscription-Token": key},
            timeout=(4, 12),
        )
        result.raise_for_status()
        entries = result.json().get("web", {}).get("results", [])
        return [
            (plain(item["title"]), item["url"], plain(item.get("description"))[:700])
            for item in entries if urlsplit(item.get("url", "")).scheme == "https"
        ]
    result = requests.get(
        "https://en.wikipedia.org/w/rest.php/v1/search/page",
        params={"q": query, "limit": 5},
        headers=HEADERS,
        timeout=(4, 12),
    )
    result.raise_for_status()
    pages = result.json().get("pages", [])
    if not pages:
        return []
    summaries = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params={"action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1,
                "exlimit": 5, "exchars": 450, "pageids": "|".join(str(page["id"]) for page in pages),
                "format": "json"},
        headers=HEADERS,
        timeout=(4, 12),
    )
    summaries.raise_for_status()
    extracts = summaries.json().get("query", {}).get("pages", {})
    return [
        (page["title"], "https://en.wikipedia.org/wiki/" + quote(page["key"], safe=""),
         plain(extracts.get(str(page["id"]), {}).get("extract") or page.get("excerpt"))[:650])
        for page in pages
    ]


def news(query):
    response = requests.get(
        "https://news.google.com/rss/search",
        params={"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"},
        headers=HEADERS,
        timeout=(4, 12),
    )
    response.raise_for_status()
    try:
        items = ET.fromstring(response.content).findall("./channel/item")
    except ET.ParseError as error:
        raise ValueError("The news feed returned an invalid response.") from error
    return [
        (item.findtext("title", ""), item.findtext("link", ""),
         "Headline only. Published " + item.findtext("pubDate", "date unavailable"))
        for item in items[:5] if urlsplit(item.findtext("link", "")).scheme == "https"
    ]


def brief(sources):
    return "\n\n".join(
        f"[{index}] {title}\n{extract}"
        for index, (title, _, extract) in enumerate(sources, 1)
    )
