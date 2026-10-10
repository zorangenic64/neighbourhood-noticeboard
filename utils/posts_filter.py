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


def find_blocked_word(text):
    if not text:
        return None

    text = text.lower()
    return next(
        (
            blocked_word
            for blocked_word in BLOCKED_WORDS
            if blocked_word in text
        ),
        None,
    )


def contains_blocked_word(text):
    return find_blocked_word(text) is not None