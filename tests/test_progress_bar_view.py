"""
Unit tests for ProgressBarView.

Covers: context manager, update, set_description, set_postfix, iterate.
"""

from app.views.progress_bar_view import ProgressBarView


class TestProgressBarViewContextManager:
    def test_context_manager_enters_and_exits(self) -> None:
        view = ProgressBarView(total=5, desc="Test", unit="img")
        with view as bar:
            assert bar is view
            bar.update(1)

    def test_update_without_context_does_not_raise(self) -> None:
        view = ProgressBarView(total=5)
        view.update(1)  # _bar is None — should be a no-op

    def test_set_description_without_context_does_not_raise(self) -> None:
        view = ProgressBarView(total=5)
        view.set_description("Test")

    def test_set_postfix_without_context_does_not_raise(self) -> None:
        view = ProgressBarView(total=5)
        view.set_postfix(status="ok")


class TestProgressBarViewMethods:
    def test_set_description_inside_context(self) -> None:
        with ProgressBarView(total=3) as view:
            view.set_description("Processing images")

    def test_set_postfix_inside_context(self) -> None:
        with ProgressBarView(total=3) as view:
            view.set_postfix(parsed=5, errors=0)

    def test_update_increments_inside_context(self) -> None:
        with ProgressBarView(total=3) as view:
            view.update(1)
            view.update(1)


class TestProgressBarViewIterate:
    def test_iterate_returns_iterable(self) -> None:
        items = [1, 2, 3]
        result = list(ProgressBarView.iterate(items, desc="Test"))
        assert result == items
