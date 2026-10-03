import re
from pathlib import Path

BLOCKED_WORDS_FILE = (
    Path(__file__).resolve().parent.parent
    / "blocked_usernames.txt"
)


def load_blocked_words():

    if not BLOCKED_WORDS_FILE.exists():
        return set()

    with open(
        BLOCKED_WORDS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        words = {
            line.strip().lower()
            for line in file
            if line.strip()
            and not line.strip().startswith("#")
        }

    return words


BLOCKED_WORDS = sorted(
    load_blocked_words(),
    key=len,
    reverse=True
)


def normalize_text(text):

    text = text.lower()

    replacements = {
        "0": "o",
        "1": "i",
        "3": "e",
        "4": "a",
        "5": "s",
        "7": "t",
        "@": "a",
        "$": "s",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return re.sub(r"[^a-z]", "", text)


def contains_blocked_word(text):

    if not text:
        return False

    text = normalize_text(text)

    return any(
        normalize_text(word) in text
        for word in BLOCKED_WORDS
    )













