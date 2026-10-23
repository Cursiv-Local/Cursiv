"""Application-owned phone pointers shared by command and graphical help."""
from html import escape

NOTEBOOK_URL = 'https://cursiv.us/notebook'
PHOTO_URL = 'https://cursiv.us/app'
PHONE_CAPTURE = (f'Phone capture (works offline after first load): {NOTEBOOK_URL} '
                 '— export the file, then Field Notebook → Import or field log import <file>.')
PHONE_LINKS = (f'Phone notebook: {NOTEBOOK_URL} · Phone photo chat: {PHOTO_URL} '
               '(separate from the notebook).')


def markdown_links(text: str) -> str:
    text = text.replace('<file>', '&lt;file&gt;')
    for url in (NOTEBOOK_URL, PHOTO_URL):
        text = text.replace(url, f'[{url}]({url})')
    return text


def capture_html(link_color: str) -> str:
    return escape(PHONE_CAPTURE).replace(NOTEBOOK_URL,
        f'<a href="{NOTEBOOK_URL}" style="color:{escape(link_color, quote=True)}">{NOTEBOOK_URL}</a>')
