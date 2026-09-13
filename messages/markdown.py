import re

_MD_SPECIAL = re.compile(r'([_*`\[])')


def escape_md(text: str) -> str:
    """Escape Markdown v1 special characters in user-supplied or external text."""
    return _MD_SPECIAL.sub(r'\\\1', text)
