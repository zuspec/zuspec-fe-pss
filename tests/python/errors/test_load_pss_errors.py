"""Tests for load_pss() error handling.

Three layers:
  1. Syntax/resolution errors  → ParseException (raised by parser/linker)
  2. IR translation errors     → PssTranslationError (raised by load_pss)
  3. Valid PSS                 → no exception, usable ClassRegistry returned
"""
import pytest
from unittest.mock import patch

from zuspec.fe.pss import load_pss, ParseException, PssTranslationError
from zuspec.fe.pss.ast_to_ir import AstToIrContext


# ---------------------------------------------------------------------------
# Layer 1 — ParseException from the parser/linker
# ---------------------------------------------------------------------------

def test_syntax_error_raises_parse_exception():
    """Missing ']' in bit-width triggers ParseException."""
    with pytest.raises(ParseException):
        load_pss("struct Foo { rand bit[8 x; }")


def test_unresolved_type_raises_parse_exception():
    """Unknown field type triggers ParseException from linker."""
    with pytest.raises(ParseException):
        load_pss("struct Foo { Nonexistent x; }")


def test_parse_exception_carries_markers():
    """ParseException.markers contains at least one structured error dict."""
    with pytest.raises(ParseException) as exc_info:
        load_pss("struct S { UnknownType x; }")
    markers = exc_info.value.markers
    assert len(markers) >= 1
    assert markers[0]["severity"] == "error"


def test_parse_exception_marker_names_bad_type():
    """The bad type name appears in the marker message."""
    with pytest.raises(ParseException) as exc_info:
        load_pss("struct S { CompletelyMadeUpType x; }")
    messages = [m["message"] for m in exc_info.value.markers]
    assert any("CompletelyMadeUpType" in msg for msg in messages)


# ---------------------------------------------------------------------------
# Layer 2 — PssTranslationError from load_pss() checking ctx.errors
# ---------------------------------------------------------------------------

def test_translation_error_raised_when_ctx_has_errors():
    """load_pss() raises PssTranslationError if the translator records errors."""
    def fake_translate(self, root):
        ctx = AstToIrContext()
        ctx.add_error("synthetic error A")
        ctx.add_error("synthetic error B")
        return ctx

    with patch(
        "zuspec.fe.pss.AstToIrTranslator.translate",
        fake_translate,
    ):
        with pytest.raises(PssTranslationError) as exc_info:
            load_pss("struct Foo { rand bit[8] x; }")

    err = exc_info.value
    assert len(err.errors) == 2
    assert "synthetic error A" in err.errors
    assert "synthetic error B" in err.errors


def test_translation_error_message_lists_errors():
    """PssTranslationError str() includes each individual error."""
    def fake_translate(self, root):
        ctx = AstToIrContext()
        ctx.add_error("problem with field x")
        return ctx

    with patch(
        "zuspec.fe.pss.AstToIrTranslator.translate",
        fake_translate,
    ):
        with pytest.raises(PssTranslationError) as exc_info:
            load_pss("struct Foo { rand bit[8] x; }")

    assert "problem with field x" in str(exc_info.value)


def test_translation_error_is_exception():
    """PssTranslationError is a proper Exception subclass."""
    err = PssTranslationError(["oops"])
    assert isinstance(err, Exception)
    assert err.errors == ["oops"]


# ---------------------------------------------------------------------------
# Layer 3 — no exception on valid PSS
# ---------------------------------------------------------------------------

def test_valid_pss_no_exception():
    """Well-formed PSS raises nothing and returns a usable ClassRegistry."""
    ns = load_pss("""
        struct Packet {
            rand bit[8] addr;
            constraint addr % 4 == 0;
        }
    """)
    assert hasattr(ns, "Packet")
    pkt = ns.Packet()
    assert hasattr(pkt, "addr")


def test_valid_pss_no_ctx_errors():
    """Translator ctx.errors is empty for normal valid PSS."""
    from zuspec.fe.pss import Parser, AstToIrTranslator

    p = Parser()
    p.parses([("x.pss", "struct Foo { rand bit[8] x; constraint x > 0; }")])
    root = p.link()
    ctx = AstToIrTranslator().translate(root)
    assert ctx.errors == []
