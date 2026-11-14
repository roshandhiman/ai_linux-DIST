import html
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path


@dataclass
class Artifact:
    filename: str
    content: str
    folder: str


def requested_artifact(text, history):
    low = text.lower()
    if re.search(r"\b(?:save|write|create|make|generate|build)\b", low) is None:
        return None
    filename = re.search(r"\b([\w-]+\.(?:html|txt|md|csv|json))\b", text, re.IGNORECASE)
    kind = "html" if re.search(r"\b(?:html|web ?page|website)\b", low) else ""
    if not kind and not filename:
        if "save" in low and re.search(r"\b(?:it|that|this)\b", low):
            for item in reversed(history[:-1]):
                if item["role"] == "user":
                    previous = requested_artifact(item["content"], [])
                    if previous:
                        return previous
        return None
    path = filename.group(1) if filename else "index.html"
    folder = "Desktop" if "desktop" in low else "Documents"
    return path, folder, text


def unfence(text):
    match = re.search(r"```(?:[\w-]+)?\s*\n(.*?)```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


class StaticHTML(HTMLParser):
    blocked = {"script", "iframe", "object", "embed", "form", "base", "link", "svg", "math", "video", "audio", "canvas"}
    void = {"base", "embed", "link", "meta", "img", "input", "source", "track", "hr", "br", "wbr", "area", "col", "param"}
    attrs = {"class", "id", "style", "lang", "charset", "name", "content", "role", "aria-label", "alt", "title", "width", "height"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output = ["<!doctype html>"]
        self.skip = []
        self.style = False

    def handle_starttag(self, tag, attrs):
        if self.skip or tag in self.blocked:
            if tag not in self.void:
                self.skip.append(tag)
            return
        if tag == "meta" and any(name == "http-equiv" for name, _ in attrs):
            return
        safe = []
        for name, value in attrs:
            value = value or ""
            if name == "href" and value.startswith("#"):
                safe.append(f' href="{html.escape(value, quote=True)}"')
            elif name in self.attrs and (name != "style" or self.safe_css(value)):
                safe.append(f' {name}="{html.escape(value, quote=True)}"')
        self.output.append(f"<{tag}{''.join(safe)}>")
        self.style = tag == "style" or self.style

    def handle_endtag(self, tag):
        if self.skip:
            if tag == self.skip[-1]:
                self.skip.pop()
            return
        if tag not in self.blocked and tag not in self.void:
            self.output.append(f"</{tag}>")
        if tag == "style":
            self.style = False

    def handle_data(self, data):
        if self.skip:
            return
        if self.style:
            if self.safe_css(data):
                self.output.append(data)
        else:
            self.output.append(html.escape(data))

    @staticmethod
    def safe_css(text):
        return not re.search(r"@import|url\s*\(|image-set\s*\(|\\|/\*|<", text, re.IGNORECASE)


def materialize(path, folder, content):
    content = unfence(content)
    if path.lower().endswith(".html"):
        start = re.search(r"<!doctype\s+html[^>]*>|<html(?:\s|>)", content, re.IGNORECASE)
        end = content.lower().rfind("</html>")
        if start and end >= start.start():
            content = content[start.start():end + 7]
        else:
            title = html.escape(Path(path).stem.replace("-", " ").title())
            text = html.escape(content)
            content = (
                f'<!doctype html>\n<html lang="en"><meta charset="utf-8">\n<title>{title}</title>\n'
                f'<style>body{{font:17px/1.6 system-ui;background:#f4f2ed;color:#222;margin:8vh auto;'
                f'max-width:70ch;padding:0 24px}}article{{white-space:pre-wrap}}</style>\n'
                f'<h1>{title}</h1><article>{text}</article></html>'
            )
        parser = StaticHTML()
        parser.feed(content)
        parser.close()
        content = "".join(parser.output)
    return Artifact(path, content + "\n", folder)
