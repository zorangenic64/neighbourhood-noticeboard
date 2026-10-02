import config


def validate_username(username):
    if not config.USERNAME_MIN_LENGTH <= len(username) <= config.USERNAME_MAX_LENGTH:
        return (
            f"Username must be between "
            f"{config.USERNAME_MIN_LENGTH} and "
            f"{config.USERNAME_MAX_LENGTH} characters."
        )

    return None


def validate_password(password):
    if not (
        config.PASSWORD_MIN_LENGTH
        <= len(password)
        <= config.PASSWORD_MAX_LENGTH
    ):
        return (
            f"Password must be between "
            f"{config.PASSWORD_MIN_LENGTH} and "
            f"{config.PASSWORD_MAX_LENGTH} characters."
        )

    return None


def validate_security_question(question):
    if not (
        config.SECURITY_QUESTION_MIN_LENGTH
        <= len(question)
        <= config.SECURITY_QUESTION_MAX_LENGTH
    ):
        return (
            f"Security question must be between "
            f"{config.SECURITY_QUESTION_MIN_LENGTH} and "
            f"{config.SECURITY_QUESTION_MAX_LENGTH} characters."
        )

    return None


def validate_security_answer(answer):
    if not (
        config.SECURITY_ANSWER_MIN_LENGTH
        <= len(answer)
        <= config.SECURITY_ANSWER_MAX_LENGTH
    ):
        return (
            f"Security answer must be between "
            f"{config.SECURITY_ANSWER_MIN_LENGTH} and "
            f"{config.SECURITY_ANSWER_MAX_LENGTH} characters."
        )

    return None


def validate_post_title(title):
    if not (
        config.POST_TITLE_MIN_LENGTH
        <= len(title)
        <= config.POST_TITLE_MAX_LENGTH
    ):
        return (
            f"Post title must be between "
            f"{config.POST_TITLE_MIN_LENGTH} and "
            f"{config.POST_TITLE_MAX_LENGTH} characters."
        )

    return None


def validate_post_body(body):
    if not (
        config.POST_BODY_MIN_LENGTH
        <= len(body)
        <= config.POST_BODY_MAX_LENGTH
    ):
        return (
            f"Post description must be between "
            f"{config.POST_BODY_MIN_LENGTH} and "
            f"{config.POST_BODY_MAX_LENGTH} characters."
        )

    return None


def validate_comment(body):
    if not (
        config.COMMENT_MIN_LENGTH
        <= len(body)
        <= config.COMMENT_MAX_LENGTH
    ):
        return (
            f"Comment must be between "
            f"{config.COMMENT_MIN_LENGTH} and "
            f"{config.COMMENT_MAX_LENGTH} characters."
        )

    return None


def validate_expiry_days(days):
    if days not in config.POST_EXPIRY_CHOICES:
        return "Expiry must be 7, 14, or 30 days."

    return None