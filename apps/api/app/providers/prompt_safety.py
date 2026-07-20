MAX_UNTRUSTED_CONTENT_CHARS = 4000


def wrap_untrusted_content(label: str, content: str) -> str:
    """Wraps external/untrusted content (retrieved documents, tool output) in clear
    delimiters and truncates it, so it's visually and structurally distinct from
    the model's own instructions in the prompt."""
    truncated = content[:MAX_UNTRUSTED_CONTENT_CHARS]
    if len(content) > MAX_UNTRUSTED_CONTENT_CHARS:
        truncated += "\n[...truncated...]"
    return f"<{label}>\n{truncated}\n</{label}>"
