"""The code and URL patterns every scribe check strips before scoring.

Four sites used to carry their own copy and three of them were the
single-backtick form. On an RST double-backtick span that form matches
the opening pair as an empty span and the closing pair as another,
which leaves the code between them exposed: ``to_american`` rewrote
``colour`` inside one, and the negation density counted ``not_found``
as a stance. Importing one compiled pattern is what keeps the four
from drifting apart again.

The double-backtick alternative comes first so the single-backtick one
cannot consume the opening pair. The single-backtick alternative stops
at a newline, because an unmatched backtick would otherwise swallow the
rest of the document.

``FENCED_CODE`` is line-anchored and closes on the marker that opened
it. The unanchored backtick-only copies it replaced left a ``~~~``
block exposed, so ``to_american`` rewrote ``colour`` inside one, and
they matched triple backticks quoted mid-line. The backreference keeps
a tilde fence that quotes a backtick fence open until its own ``~~~``.

``URL`` takes ``www.`` addresses as well as a scheme, because a bare
``www.`` host is as much a link as an ``https://`` one.
"""

from __future__ import annotations

import re

__all__ = ["FENCED_CODE", "INLINE_CODE", "URL"]

INLINE_CODE = re.compile(r"``[^`]*``|`[^`\n]*`")

FENCED_CODE = re.compile(r"^ {0,3}(```|~~~).*?^ {0,3}\1", re.DOTALL | re.MULTILINE)

URL = re.compile(r"\b(?:https?://|www\.)\S+")
