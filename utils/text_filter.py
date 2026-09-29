from pathlib import Path


BLOCKED_WORDS_FILE = (
    Path(__file__).resolve().parent.parent
    / "blocked_words.txt"
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


def contains_blocked_word(text):

    if not text:
        return False

    text = text.lower()

    blocked_words = load_blocked_words()

    return any(
        word in text
        for word in blocked_words
    )