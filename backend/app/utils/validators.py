import re
import secrets

# Special characters accepted by validate_password's rule below. Kept as a
# curated, unambiguous subset (no quotes/backslashes) for generated passwords.
_TEMP_PW_SPECIALS = "!@#$%^&*-_=+"
_TEMP_PW_LOWER = "abcdefghijkmnpqrstuvwxyz"   # no l/o (ambiguous)
_TEMP_PW_UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ"   # no I/O
_TEMP_PW_DIGITS = "23456789"                  # no 0/1


def generate_temp_password(length: int = 12) -> str:
    """Generate a random password guaranteed to satisfy validate_password().

    Always contains at least one upper, lower, digit and special character.
    Uses the ``secrets`` module (cryptographically strong). Ambiguous glyphs
    (0/O/1/l/I) are excluded so the emailed temp password is easy to type.
    """
    length = max(length, 8)
    alphabet = _TEMP_PW_LOWER + _TEMP_PW_UPPER + _TEMP_PW_DIGITS + _TEMP_PW_SPECIALS
    # Guarantee one of each required category.
    chars = [
        secrets.choice(_TEMP_PW_UPPER),
        secrets.choice(_TEMP_PW_LOWER),
        secrets.choice(_TEMP_PW_DIGITS),
        secrets.choice(_TEMP_PW_SPECIALS),
    ]
    chars += [secrets.choice(alphabet) for _ in range(length - len(chars))]
    # Fisher–Yates shuffle with a CSPRNG so category chars aren't front-loaded.
    for i in range(len(chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        chars[i], chars[j] = chars[j], chars[i]
    return "".join(chars)


def validate_password(password: str) -> list:
    """Returns a list of validation error strings. Empty list means valid."""
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")
    if not re.search(r'[!@#$%^&*()\-_=+\[\]{};:\'",.<>?/\\|`~]', password):
        errors.append("Password must contain at least one special character")
    return errors


def validate_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    pattern = r"^\+?[\d\s\-().]{7,20}$"
    return bool(re.match(pattern, phone))
