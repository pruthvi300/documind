import re


def clean_text(text: str) -> str:
    """Collapse runs of blank lines and spaces left behind by PDF/DOCX extraction."""
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
