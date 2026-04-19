"""Unit tests for MappingController."""

import json
from pathlib import Path
from unittest.mock import patch


from app.controllers.mapping_controller import MappingController
from app.models.mapping_entry import MappingEntry, RankedMcc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_vsic_json(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "source": "test",
                "total_vsic_count": 2,
                "vsic_list": [
                    {
                        "code": "0111",
                        "title": "Trồng lúa",
                        "level": 4,
                        "parent_code": None,
                        "description": "",
                    },
                    {
                        "code": "6201",
                        "title": "Lập trình",
                        "level": 4,
                        "parent_code": None,
                        "description": "",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def _write_mcc_json(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "source": "test",
                "total_mcc_count": 2,
                "mcc_list": [
                    {"mcc": "0111", "title": "Farms", "description": "Agriculture"},
                    {
                        "mcc": "7372",
                        "title": "Computer Programming",
                        "description": "Software",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def _make_template(tmp_path: Path) -> Path:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Mapping Result"
    wb.create_sheet("Hướng Dẫn")
    wb.create_sheet("Thống Kê")
    p = tmp_path / "template.xlsx"
    wb.save(p)
    return p


FAKE_ENTRIES = [
    MappingEntry(
        vsic_code="0111",
        vsic_title="Trồng lúa",
        top_results=[
            RankedMcc(mcc_code="0111", mcc_title="Farms", score=0.9, comment="ok")
        ],
    ),
    MappingEntry(vsic_code="6201", vsic_title="Lập trình", top_results=[]),
]


class TestMappingControllerExitCodes:
    def test_returns_1_when_vsic_file_missing(self, tmp_path: Path) -> None:
        controller = MappingController(template_path=_make_template(tmp_path))
        exit_code = controller.execute(
            vsic_input=tmp_path / "missing.json",
            mcc_input=tmp_path / "mcc.json",
            output=tmp_path / "out.xlsx",
            output_detail=tmp_path / "detail.xlsx",
        )
        assert exit_code == 1

    def test_returns_1_when_mcc_file_missing(self, tmp_path: Path) -> None:
        vsic_path = tmp_path / "vsic.json"
        _write_vsic_json(vsic_path)
        controller = MappingController(template_path=_make_template(tmp_path))
        exit_code = controller.execute(
            vsic_input=vsic_path,
            mcc_input=tmp_path / "missing.json",
            output=tmp_path / "out.xlsx",
            output_detail=tmp_path / "detail.xlsx",
        )
        assert exit_code == 1

    def test_returns_2_when_ollama_unavailable(self, tmp_path: Path) -> None:
        vsic_path = tmp_path / "vsic.json"
        mcc_path = tmp_path / "mcc.json"
        _write_vsic_json(vsic_path)
        _write_mcc_json(mcc_path)
        with patch(
            "app.controllers.mapping_controller.check_ollama_models",
            side_effect=RuntimeError("Ollama unavailable"),
        ):
            controller = MappingController(template_path=_make_template(tmp_path))
            exit_code = controller.execute(
                vsic_input=vsic_path,
                mcc_input=mcc_path,
                output=tmp_path / "out.xlsx",
                output_detail=tmp_path / "detail.xlsx",
            )
        assert exit_code == 2

    def test_returns_0_on_success(self, tmp_path: Path) -> None:
        vsic_path = tmp_path / "vsic.json"
        mcc_path = tmp_path / "mcc.json"
        _write_vsic_json(vsic_path)
        _write_mcc_json(mcc_path)

        def fake_use_case_execute(**kwargs):
            return iter(FAKE_ENTRIES)

        with patch("app.controllers.mapping_controller.check_ollama_models"), patch(
            "app.services.map_vsic_to_mcc_use_case.MapVsicToMccUseCase.execute",
            return_value=iter(FAKE_ENTRIES),
        ):
            controller = MappingController(template_path=_make_template(tmp_path))
            exit_code = controller.execute(
                vsic_input=vsic_path,
                mcc_input=mcc_path,
                output=tmp_path / "out.xlsx",
                output_detail=tmp_path / "detail.xlsx",
            )
        assert exit_code == 0

    def test_returns_3_on_io_error(self, tmp_path: Path) -> None:
        vsic_path = tmp_path / "vsic.json"
        mcc_path = tmp_path / "mcc.json"
        _write_vsic_json(vsic_path)
        _write_mcc_json(mcc_path)

        with patch("app.controllers.mapping_controller.check_ollama_models"), patch(
            "app.services.map_vsic_to_mcc_use_case.MapVsicToMccUseCase.execute",
            return_value=iter(FAKE_ENTRIES),
        ), patch(
            "app.repositories.simple_mapping_xlsx_repository"
            ".SimpleMappingXlsxRepository.write",
            side_effect=IOError("disk full"),
        ):
            controller = MappingController(template_path=_make_template(tmp_path))
            exit_code = controller.execute(
                vsic_input=vsic_path,
                mcc_input=mcc_path,
                output=tmp_path / "out.xlsx",
                output_detail=tmp_path / "detail.xlsx",
            )
        assert exit_code == 3


class TestMappingControllerDefaults:
    def test_default_top_k_is_15(self) -> None:
        import inspect

        sig = inspect.signature(MappingController.execute)
        assert sig.parameters["top_k"].default == 15

    def test_template_path_none_skips_detail_output(self, tmp_path: Path) -> None:
        vsic_path = tmp_path / "vsic.json"
        mcc_path = tmp_path / "mcc.json"
        _write_vsic_json(vsic_path)
        _write_mcc_json(mcc_path)

        with patch("app.controllers.mapping_controller.check_ollama_models"), patch(
            "app.services.map_vsic_to_mcc_use_case.MapVsicToMccUseCase.execute",
            return_value=iter(FAKE_ENTRIES),
        ):
            controller = MappingController(template_path=None)
            controller.execute(
                vsic_input=vsic_path,
                mcc_input=mcc_path,
                output=tmp_path / "out.xlsx",
                output_detail=tmp_path / "detail.xlsx",
            )
        detail_path = tmp_path / "detail.xlsx"
        assert not detail_path.exists()
