import re

BLACKLISTED_PHRASES = (
    "ignore previous",
    "ignore all",
    "system prompt",
    "verbatim",
    "debug mode",
    "developer mode",
    "override",
    "forget everything",
    "initial instructions",
)

KNOWN_SECRET = "FitPlate_DB_P@ssw0rd_2026"
KNOWN_SECRET_PATTERN = re.compile(r"FitPlate_DB_[a-zA-Z0-9@_]+")


def contains_prompt_injection(user_input: str) -> bool:
    """Return True for the small set of patterns demonstrated by this lab."""
    normalized = user_input.lower()
    if any(phrase in normalized for phrase in BLACKLISTED_PHRASES):
        return True
    return re.search(r"ignore\s+(all\s+)?previous", normalized) is not None


def apply_known_pattern_redaction(llm_response: str) -> str:
    """Redact the lab's mock secret and closely related test values."""
    redacted = llm_response.replace(KNOWN_SECRET, "[REDACTED_BY_OUTPUT_FILTER]")
    return KNOWN_SECRET_PATTERN.sub("[REDACTED_BY_OUTPUT_FILTER]", redacted)
