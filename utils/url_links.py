import re

from markupsafe import Markup, escape


URL_PATTERN = re.compile(r"""https?://[^\s<>"']+""", re.IGNORECASE)
TRAILING_PUNCTUATION = ".,!?;:"


def linkify_urls(text):
    parts = []
    position = 0

    for match in URL_PATTERN.finditer(text):
        url = match.group()
        link_url = url.rstrip(TRAILING_PUNCTUATION)

        if not link_url:
            continue

        link_end = match.start() + len(link_url)
        parts.append(escape(text[position:match.start()]))
        parts.append(
            Markup('<a href="')
            + escape(link_url)
            + Markup('" target="_blank" rel="noopener noreferrer">')
            + escape(link_url)
            + Markup("</a>")
        )
        position = link_end

    parts.append(escape(text[position:]))
    return Markup("").join(parts)
