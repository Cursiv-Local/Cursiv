"""Application-owned phone pointers shared by command and graphical help."""
from html import escape

from cursiv_v215.core.phone_help import NOTEBOOK_URL, PHOTO_URL, PHONE_CAPTURE, PHONE_LINKS


def markdown_links(text: str) -> str:
    text = text.replace('<file>', '&lt;file&gt;')
    for url in (NOTEBOOK_URL, PHOTO_URL):
        text = text.replace(url, f'[{url}]({url})')
    return text


def capture_html(link_color: str) -> str:
    return escape(PHONE_CAPTURE).replace(NOTEBOOK_URL,
        f'<a href="{NOTEBOOK_URL}" style="color:{escape(link_color, quote=True)}">{NOTEBOOK_URL}</a>')
