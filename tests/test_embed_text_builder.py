"""Unit tests for the shared embed-text builder."""

from app.services.embed_text_builder import (
    build_mcc_text,
    build_vsic_text,
    build_vsic_query,
    strip_html,
)


class TestStripHtml:
    def test_removes_tags(self) -> None:
        assert strip_html("<b>Hello</b> world") == "Hello world"

    def test_none_returns_empty(self) -> None:
        assert strip_html(None) == ""

    def test_empty_returns_empty(self) -> None:
        assert strip_html("") == ""


class TestBuildMccText:
    def test_combines_title_and_description(self) -> None:
        mcc = {"title": "Farms", "description": "Crop farming"}
        assert build_mcc_text(mcc) == "Farms — Crop farming"

    def test_strips_html_in_title_and_description(self) -> None:
        mcc = {"title": "<b>Farms</b>", "description": "<i>Crop</i>"}
        assert build_mcc_text(mcc) == "Farms — Crop"

    def test_truncates_description_to_1000_chars(self) -> None:
        mcc = {"title": "T", "description": "x" * 1200}
        text = build_mcc_text(mcc)
        assert text == "T — " + "x" * 1000

    def test_missing_description(self) -> None:
        assert build_mcc_text({"title": "Farms"}) == "Farms — "


class TestBuildVsicText:
    def test_returns_raw_title(self) -> None:
        assert build_vsic_text({"code": "0111", "title": "Trồng lúa"}) == "Trồng lúa"

    def test_does_not_strip_html(self) -> None:
        """VSIC text is the raw title — no HTML stripping (preserves parity)."""
        assert build_vsic_text({"title": "<b>X</b>"}) == "<b>X</b>"


class TestBuildVsicQuery:
    def test_prefixes_instruction(self) -> None:
        vsic = {"code": "0111", "title": "Trồng lúa"}
        query = build_vsic_query(vsic)
        assert query.startswith("Instruct: Given a Vietnamese industry name, retrieve the most relevant Visa MCC merchant category")
        assert "Query: Trồng lúa" in query
