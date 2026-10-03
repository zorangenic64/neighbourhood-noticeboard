from pathlib import Path

BLOCKED_TEXT_FILE = (
    Path(__file__).resolve().parent.parent
    / "blocked_post_comment_words.txt"
)


def load_blocked_words():

    if not BLOCKED_TEXT_FILE.exists():
        return set()

    with open(
        BLOCKED_TEXT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return {
            line.strip().lower()
            for line in file
            if line.strip()
            and not line.strip().startswith("#")
        }


BLOCKED_WORDS = sorted(
    load_blocked_words(),
    key=len,
    reverse=True
)


def contains_blocked_word(text):

    if not text:
        return False

    text = text.lower()

    return any(
        blocked_word in text
        for blocked_word in BLOCKED_WORDS
    )