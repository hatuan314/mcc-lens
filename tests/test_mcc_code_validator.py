"""Unit tests for MccCodeValidator."""

from app.services.mcc_code_validator import MccCodeValidator

VALID_CODES = ["0111", "5411", "7372", "5999", "7299"]


class TestMccCodeValidatorValid:
    def test_valid_code_returned_unchanged(self) -> None:
        validator = MccCodeValidator(VALID_CODES)
        assert validator.validate("5411", "0111") == "5411"

    def test_all_valid_codes_pass(self) -> None:
        validator = MccCodeValidator(VALID_CODES)
        for code in VALID_CODES:
            assert validator.validate(code, VALID_CODES[0]) == code


class TestMccCodeValidatorFallback:
    def test_invalid_code_falls_back_to_fallback(self) -> None:
        validator = MccCodeValidator(VALID_CODES)
        result = validator.validate("9999", "0111")
        assert result == "0111"

    def test_invalid_code_and_invalid_fallback_returns_empty(self) -> None:
        validator = MccCodeValidator(VALID_CODES)
        result = validator.validate("9999", "8888")
        assert result == ""

    def test_empty_string_code_falls_back(self) -> None:
        validator = MccCodeValidator(VALID_CODES)
        result = validator.validate("", "5411")
        assert result == "5411"


class TestMccCodeValidatorEdgeCases:
    def test_empty_valid_codes_list(self) -> None:
        validator = MccCodeValidator([])
        result = validator.validate("5411", "0111")
        assert result == ""

    def test_single_valid_code(self) -> None:
        validator = MccCodeValidator(["5411"])
        assert validator.validate("5411", "0111") == "5411"
        assert validator.validate("0111", "5411") == "5411"
