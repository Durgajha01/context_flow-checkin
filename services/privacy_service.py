"""Privacy boundary for checkpoint payloads.

Checkpoint providers can include raw prompts or agent transcripts. CheckIN keeps
only safe operational metadata, so downstream storage and analysis never receive
those fields.
"""
from collections.abc import Mapping


SENSITIVE_FIELDS = {
    "prompt",
    "prompts",
    "raw_prompt",
    "transcript",
    "transcripts",
    "raw_transcript",
    "messages",
    "chat_history",
    "conversation",
}
REDACTION_MARKERS = {"[REDACTED]", "<REDACTED>", "REDACTED", "***"}


def _is_sensitive_field(key):
    normalized = key.lower()
    return normalized in SENSITIVE_FIELDS or "prompt" in normalized or "transcript" in normalized


def sanitize_checkpoint(record):
    """Return a safe checkpoint record plus an explicit completeness state."""
    redacted_fields = []

    def clean(value, path=""):
        if isinstance(value, Mapping):
            safe = {}
            for key, item in value.items():
                key_text = str(key)
                item_path = f"{path}.{key_text}" if path else key_text
                if _is_sensitive_field(key_text):
                    redacted_fields.append(item_path)
                    continue
                safe[key_text] = clean(item, item_path)
            return safe
        if isinstance(value, list):
            return [clean(item, f"{path}[]") for item in value]
        if isinstance(value, str) and value.strip().upper() in REDACTION_MARKERS:
            redacted_fields.append(path or "value")
            return None
        return value

    safe_record = clean(record or {})
    declared = str(safe_record.pop("context_completeness", "")).lower()
    if redacted_fields or declared == "redacted":
        completeness = "redacted"
    elif declared in {"partial", "unavailable"}:
        completeness = declared
    elif not safe_record:
        completeness = "unavailable"
    else:
        completeness = "complete"
    safe_record["context_completeness"] = completeness
    safe_record["redacted_fields"] = sorted(set(redacted_fields))
    return safe_record


def context_is_complete(context):
    return getattr(context, "context_completeness", "complete") == "complete"
