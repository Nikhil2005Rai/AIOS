from app.providers.prompt_safety import MAX_UNTRUSTED_CONTENT_CHARS, wrap_untrusted_content


def test_short_content_is_wrapped_in_delimiters() -> None:
    result = wrap_untrusted_content("my_label", "hello world")
    assert result == "<my_label>\nhello world\n</my_label>"


def test_content_over_limit_is_truncated_with_marker() -> None:
    long_content = "x" * (MAX_UNTRUSTED_CONTENT_CHARS + 500)
    result = wrap_untrusted_content("data", long_content)

    assert result.startswith("<data>\n")
    assert result.endswith("\n</data>")
    assert "[...truncated...]" in result

    # The body between delimiters should be exactly MAX chars + the marker
    inner = result.removeprefix("<data>\n").removesuffix("\n</data>")
    assert inner == "x" * MAX_UNTRUSTED_CONTENT_CHARS + "\n[...truncated...]"


def test_exact_limit_content_is_not_truncated() -> None:
    exact_content = "a" * MAX_UNTRUSTED_CONTENT_CHARS
    result = wrap_untrusted_content("label", exact_content)

    assert "[...truncated...]" not in result
    assert result == f"<label>\n{exact_content}\n</label>"


def test_delimiter_format_present() -> None:
    result = wrap_untrusted_content("retrieved_chunk id=c1 score=0.9500", "some doc text")
    assert result.startswith("<retrieved_chunk id=c1 score=0.9500>\n")
    assert result.endswith("\n</retrieved_chunk id=c1 score=0.9500>")


def test_empty_content_is_wrapped() -> None:
    result = wrap_untrusted_content("tool_output", "")
    assert result == "<tool_output>\n\n</tool_output>"
