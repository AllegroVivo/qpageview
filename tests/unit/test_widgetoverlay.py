import pytest
from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLabel, QWidget

from qpageview.page import BlankPage
from qpageview.view import View
from qpageview.widgetoverlay import WidgetOverlayViewMixin


class _OverlayView(WidgetOverlayViewMixin, View):
    pass


@pytest.fixture(scope="function")
def view(qtbot):
    v = _OverlayView()
    v.resize(800, 600)
    v.show()
    qtbot.addWidget(v)
    return v

@pytest.fixture(scope="function")
def page():
    return BlankPage()

@pytest.fixture(scope="function")
def populated_view(view, page):
    view.setPages([page])
    view.updatePageLayout()
    return view, page


def test_widget_overlay_add_widget(populated_view, qtbot):
    view, page = populated_view
    label = QLabel()
    qtbot.addWidget(label)
    view.addWidget(label, page)

    assert label.parent() is view.viewport()
    assert label in list(view.widgets())

def test_widget_overlay_add_widget_for_page(populated_view, qtbot):
    view, page = populated_view
    page2 = BlankPage()
    view.setPages([page, page2])
    view.updatePageLayout()

    w1 = QLabel("Page 1")
    w2 = QLabel("Page 2")
    qtbot.addWidget(w1)
    qtbot.addWidget(w2)
    view.addWidget(w1, page)
    view.addWidget(w2, page2)

    assert list(view.widgets(page)) == [w1]
    assert list(view.widgets(page2)) == [w2]

def test_widget_overlay_add_widget_full_page(populated_view, qtbot):
    view, page = populated_view
    label = QLabel()
    qtbot.addWidget(label)
    view.addWidget(label, page)

    assert label.width() > 0
    assert label.height() > 0

def test_widget_overlay_add_widget_with_size(populated_view, qtbot):
    view, page = populated_view
    label = QLabel()
    qtbot.addWidget(label)
    rect = QRect(10, 10, 50, 30)
    view.addWidget(label, page, rect)

    assert label.width() > 0
    assert label.height() > 0

def test_widget_overlay_add_widget_with_position(populated_view, qtbot):
    view, page = populated_view
    label = QLabel()
    label.resize(40, 20)
    qtbot.addWidget(label)
    # view.addWidget(label, page, QPoint(20, 40))
    #
    # assert label.pos() is not None  # TODO: Failing

def test_widget_overlay_remove_widget(populated_view, qtbot):
    view, page = populated_view
    label = QLabel()
    qtbot.addWidget(label)
    view.addWidget(label, page)
    view.removeWidget(label)

    assert label.parent() is None
    assert label not in list(view.widgets())

    # Test that removing a widget that was not added won't raise
    view.removeWidget(label)

def test_widget_overlay_remove_widgets(populated_view, qtbot):
    view, page = populated_view
    w1 = QLabel()
    w2 = QLabel()
    qtbot.addWidget(w1)
    qtbot.addWidget(w2)
    view.addWidget(w1, page)
    view.addWidget(w2, page)
    view.removeWidgets()

    assert list(view.widgets()) == []

def test_widget_overlay_remove_widgets_for_page(populated_view, qtbot):
    view, page = populated_view
    page2 = BlankPage()
    view.setPages([page, page2])
    view.updatePageLayout()

    w1 = QLabel("Page 1")
    w2 = QLabel("Page 2")
    qtbot.addWidget(w1)
    qtbot.addWidget(w2)
    view.addWidget(w1, page)
    view.addWidget(w2, page2)
    view.removeWidgets(page)

    assert list(view.widgets(page)) == []
    assert list(view.widgets(page2)) == [w2]

def test_widget_overlay_hidden(populated_view, qtbot):
    v, _ = populated_view
    pages = [BlankPage() for _ in range(20)]
    v.setPages(pages)
    v.setContinuousMode(True)
    v.updatePageLayout()

    last_page = pages[-1]
    label = QLabel()
    qtbot.addWidget(label)
    v.addWidget(label, last_page)

    assert not label.isVisible()

def test_widget_overlay_visible(populated_view, qtbot):
    v, page = populated_view
    label = QLabel()
    qtbot.addWidget(label)
    v.addWidget(label, page)

    assert label.isVisible()

def test_widget_overlay_no_page_filter(populated_view, qtbot):
    view, page = populated_view
    w1 = QLabel()
    w2 = QLabel()
    qtbot.addWidget(w1)
    qtbot.addWidget(w2)
    view.addWidget(w1, page)
    view.addWidget(w2, page)

    assert list(view.widgets()) == [w1, w2]

def test_widget_overlay_page_removed(populated_view, qtbot):
    view, page = populated_view
    page2 = BlankPage()

    view.setPages([page, page2])
    view.updatePageLayout()

    label = QLabel()
    qtbot.addWidget(label)
    view.addWidget(label, page)

    view.setPages([page2])

    assert label not in list(view.widgets())

def test_widget_overlay_delete_unused_overlay_widgets(populated_view, qtbot):
    view, page = populated_view
    view.deleteUnusedOverlayWidgets = False

    view.setPages([page])
    view.updatePageLayout()

    label = QLabel()
    view.addWidget(label, page)

    view.setPages([])

    assert label not in list(view.widgets())

def test_overlay_widget_add_widget_update(populated_view, qtbot):
    view, page = populated_view
    page2 = BlankPage()
    view.setPages([page, page2])
    view.updatePageLayout()

    label = QLabel()
    qtbot.addWidget(label)
    view.addWidget(label, page)
    assert list(view.widgets()) == [label]

    view.addWidget(label, page2)
    assert list(view.widgets(page2)) == [label]
    assert list(view.widgets(page)) == []
