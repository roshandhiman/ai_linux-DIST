"""The boundary where somebody else's text becomes text the model reads.

Ported from clarkeAgent's ``onyx.tools.untrusted`` and ``onyx.prompt._one_line``.
The defence is structural, never semantic: nothing here tries to decide whether
a file or a command's output is *trying* to manipulate the model. It removes the
shapes by which text impersonates a turn (chat-template markers, faked speaker
labels), forces ASCII (which also kills homoglyph and bidi tricks, and keeps a
cp1252 console alive), and bounds the size. The caller then labels what is left
as untrusted, because a model that knows it is reading a quotation behaves
better than one handed the same words bare.
"""

import re
from typing import Final

__all__ = ["one_line", "quote_block", "sanitise", "fold_ascii"]

#: Per-field ceiling for one-line fields (file names, titles, error messages).
FIELD_MAX_CHARS: Final[int] = 160

#: Markers by which text impersonates a role or a turn boundary.
_ROLE_MARKERS: Final[re.Pattern[str]] = re.compile(
    r"""(
          <\|[^|>]{0,32}\|>              # <|im_start|>, <|endoftext|>
        | \[/?(?:INST|SYS)\]             # [INST] [/INST] [SYS]
        | \#{2,}\s*(?:system|assistant|user|human)\b
        | ^\s*(?:system|assistant|user|human)\s*:   # a faked speaker label
        | </?\s*(?:system|assistant|user|human)\s*> # a faked tag
        | ^\s*ANSWER\b                   # our own directive, forged by data
    )""",
    re.IGNORECASE | re.VERBOSE | re.MULTILINE,
)

#: Punctuation and units folded to ASCII before everything else is dropped, so
#: "64 x 0.18" does not become "64 0.18". Nothing here maps two different
#: letters onto one, so it adds no homoglyph the drop would otherwise catch.
_FOLD: Final[dict[int, str]] = str.maketrans(
    {
        "×": "x",
        "÷": "/",
        "°": " deg",
        "–": "-",
        "—": "-",
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "…": "...",
        " ": " ",
        "→": "->",
        "£": "GBP ",
        "€": "EUR ",
        "¥": "JPY ",
        "₹": "INR ",
        "•": "-",
    }
)


def fold_ascii(text: str) -> str:
    """Fold common punctuation, then drop anything that is still not ASCII."""
    return text.translate(_FOLD).encode("ascii", "ignore").decode("ascii")


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip(" ,;:") + "..."


def one_line(text: str, limit: int = 400) -> str:
    """Flatten, force ASCII and bound: what the model says to the user."""
    return _clip(" ".join(fold_ascii(text).split()), limit)


def sanitise(text: str, *, limit: int = FIELD_MAX_CHARS) -> str:
    """One field of untrusted text, safe to place in a window.

    Safe means bounded, single-line, ASCII and carrying no turn marker. It
    does not mean trustworthy -- the caller still labels it.
    """
    without_roles = _ROLE_MARKERS.sub(" ", text)
    return _clip(" ".join(fold_ascii(without_roles).split()), limit)


def quote_block(text: str, *, limit: int = 900, max_lines: int = 30,
                preserve_layout: bool = False) -> str:
    """Multi-line untrusted text (program output, file contents) for a window.

    Lines survive, because a directory listing flattened onto one line is
    useless to the model; markers, control characters and length do not.
    Every line is indented, so nothing in it can start a line the reply
    parser or a chat template would read as a directive.
    """
    if preserve_layout:
        cleaned = re.sub(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]", "", text.replace("\r\n", "\n"))
        lines = cleaned.split("\n")
    else:
        cleaned = _ROLE_MARKERS.sub(" ", fold_ascii(text))
        lines = [" ".join(line.split()) for line in cleaned.splitlines() if line.strip()]
    dropped = max(0, len(lines) - max_lines)
    lines = lines[:max_lines]
    body = "\n".join("  | " + line for line in lines) if lines else "  | (nothing)"
    if dropped:
        body += f"\n  | ... {dropped} more line(s)"
    return _clip(body, limit)
