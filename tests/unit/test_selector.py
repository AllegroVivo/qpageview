import pytest
from PySide6.QtCore import QRect, QPoint, QEvent, Qt
from PySide6.QtGui import QMouseEvent, QKeyEvent
from PySide6.QtWidgets import QWidget


from qpageview.selector import SelectorViewMixin


class _MockPage:
    def __init__(self, geom):
        self._geom = QRect(geom)
        self.width = geom.width()
        self.height = geom.height()

    def geometry(self):
        return QRect(self._geom)

    def rect(self):
        return QRect(0, 0, self._geom.width(), self._geom.height())

    def pos(self):
        return self._geom.topLeft()

class _MockLayout:
    def __init__(self, pages=None):
        self._pages = list(pages or [])

    def index(self, page):
        return self._pages.index(page)

    def pageAt(self, pos):
        for p in self._pages:
            if p.geometry().contains(pos):
                return p
        return None

# We need this class to keep the viewport from painting, otherwise the QPainter will spam
# the test output with warnings about painting outside the paintEvent.
class _NoPaintViewport(QWidget):
    def paintEvent(self, _):
        pass

class _BaseView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._viewport = _NoPaintViewport()
        self._viewport.resize(400, 300)
        self._layout = _MockLayout([])
        self._layout_pos = QPoint(0, 0)
        self.update_page_layout_calls = []
        self.super_mouse_press_calls = 0
        self.super_key_press_calls = 0
        self.super_long_press_calls = 0

    def viewport(self):
        return self._viewport

    def visibleRect(self):
        return QRect(0, 0, self._viewport.width(), self._viewport.height())

    def page(self, n):
        return self._layout._pages[n - 1]

    def pageCount(self):
        return len(self._layout._pages)

    def pageLayout(self):
        return self._layout

    @property
    def _pageLayout(self):
        return self._layout

    def layoutPosition(self):
        return QPoint(self._layout_pos)

    def pagesToPaint(self, rect, _):
        for p in self._layout._pages:
            if p.geometry().intersects(rect):
                yield p, p.geometry()

    def updatePageLayout(self, lazy=False):
        self.update_page_layout_calls.append(lazy)

    def mousePressEvent(self, _):
        self.super_mouse_press_calls += 1

    def keyPressEvent(self, _):
        self.super_key_press_calls += 1

    def longMousePressEvent(self, _):
        self.super_long_press_calls += 1

class _SelectorView(SelectorViewMixin, _BaseView):
    pass


@pytest.fixture(scope="function")
def selector_view(qtbot):
    v = _SelectorView()
    v.resize(400, 300)
    pages = [
        _MockPage(QRect(0, 0, 120, 120)),
        _MockPage(QRect(140, 0, 120, 160)),
        _MockPage(QRect(280, 0, 120, 160)),
    ]
    v._layout = _MockLayout(pages)
    v.show()
    qtbot.addWidget(v)
    return v

def _mouse_event(ev_type, pos, button, buttons, modifiers):
    p = QPoint(pos)
    return QMouseEvent(
        ev_type,
        p,
        p,
        p,
        button,
        buttons,
        modifiers
    )

def test_selected_sorted_pages(selector_view):
    selector_view._selection = {3, 1, 2}

    assert selector_view.selection() == [1, 2, 3]

def test_selector_modify_selection(selector_view):
    emitted = []
    updated = []
    selector_view.selectionChanged.connect(lambda: emitted.append(True))
    selector_view.viewport().update = lambda: updated.append(True)

    with selector_view.modifySelection() as s:
        s.add(1)

    assert emitted == [True]
    assert updated == [True]

def test_selector_modify_selection_no_change(selector_view):
    emitted = []
    selector_view.selectionChanged.connect(lambda: emitted.append(True))

    with selector_view.modifySelection():
        pass

    assert emitted == []

def test_selector_update_page_layout(selector_view):
    selector_view._selection = {1, 4, 9}

    selector_view.updatePageLayout()

    assert selector_view.selection() == [1]

def test_selector_clear_selection(selector_view):
    selector_view._selection = {1, 2}

    selector_view.clearSelection()

    assert selector_view.selection() == []

def test_selector_select_all(selector_view):
    selector_view.selectAll()

    assert selector_view.selection() == [1, 2, 3]

def test_selector_toggle_selection(selector_view):
    selector_view.toggleSelection(2)
    assert selector_view.selection() == [2]

    selector_view.toggleSelection(2)
    assert selector_view.selection() == []

def test_selector_set_selection_mode(selector_view):
    emitted = []
    selector_view.selectionModeChanged.connect(lambda mode: emitted.append(mode))

    selector_view.setSelectionMode(True)
    selector_view.setSelectionMode(True)
    selector_view.setSelectionMode(False)

    assert emitted == [True, False]

def test_selector_mouse_press_on_checkbox(selector_view):
    selector_view.setSelectionMode(True)
    first_page = selector_view.page(1)
    click_pos = first_page.pos() + QPoint(2, 2)

    ev = _mouse_event(
        QEvent.Type.MouseButtonPress,
        click_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    selector_view.mousePressEvent(ev)

    assert selector_view.selection() == [1]

def test_selector_mouse_press_with_control_mod(selector_view):
    selector_view.setSelectionMode(True)
    selector_view._selection = {1}
    second_page = selector_view.page(2)
    click_pos = second_page.pos() + QPoint(2, 2)

    ev = _mouse_event(
        QEvent.Type.MouseButtonPress,
        click_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.ControlModifier
    )
    selector_view.mousePressEvent(ev)

    assert selector_view.selection() == [1, 2]

def test_selector_mouse_press_with_shift_mod(selector_view):
    selector_view.setSelectionMode(True)
    selector_view._selection = {1}
    third_page = selector_view.page(3)
    click_pos = third_page.pos() + QPoint(2, 2)

    ev = _mouse_event(
        QEvent.Type.MouseButtonPress,
        click_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.ShiftModifier
    )
    selector_view.mousePressEvent(ev)

    assert selector_view.selection() == [1, 2, 3]

def test_selector_mouse_press_outside_checkbox(selector_view):
    selector_view.setSelectionMode(True)
    first_page = selector_view.page(1)
    click_pos = first_page.pos() + QPoint(40, 40)

    ev = _mouse_event(
        QEvent.Type.MouseButtonPress,
        click_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    selector_view.mousePressEvent(ev)

    assert selector_view.selection() == []
    assert selector_view.super_mouse_press_calls == 1

def test_selector_key_press_escape(selector_view):
    selector_view.userChangeSelectionModeEnabled = True
    selector_view.setSelectionMode(True)
    selector_view._selection = {1, 2}

    ev = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Escape,
        Qt.KeyboardModifier.NoModifier
    )
    selector_view.keyPressEvent(ev)

    assert selector_view.selection() == []
    assert selector_view.selectionMode() is False
    assert selector_view.super_key_press_calls == 0

def test_selector_key_press_select_all(selector_view):
    selector_view.setSelectionMode(True)
    ev = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_A,
        Qt.KeyboardModifier.ControlModifier
    )
    selector_view.keyPressEvent(ev)

    assert selector_view.selection() == [1, 2, 3]

def test_selector_unhandled_key_press(selector_view):
    selector_view.setSelectionMode(True)
    ev = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_F5,
        Qt.KeyboardModifier.NoModifier
    )
    selector_view.keyPressEvent(ev)

    assert selector_view.super_key_press_calls == 1

def test_selector_long_mouse_press_enables_selection(selector_view):
    selector_view.userChangeSelectionModeEnabled = True
    selector_view.setSelectionMode(False)

    ev = _mouse_event(
        QEvent.Type.MouseButtonPress,
        QPoint(0, 0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    selector_view.longMousePressEvent(ev)

    assert selector_view.selectionMode() is True

def test_selector_long_mouse_press_disables_selection(selector_view):
    selector_view.userChangeSelectionModeEnabled = True
    selector_view.setSelectionMode(True)
    selector_view._selection = set()

    ev = _mouse_event(
        QEvent.Type.MouseButtonPress,
        QPoint(0, 0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    selector_view.longMousePressEvent(ev)

    assert selector_view.selectionMode() is False
    assert selector_view.selection() == []

def test_selector_long_mouse_press_unhandled(selector_view):
    selector_view.userChangeSelectionModeEnabled = True
    selector_view.setSelectionMode(True)
    selector_view._selection = {1}

    ev = _mouse_event(
        QEvent.Type.MouseButtonPress,
        QPoint(0, 0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    selector_view.longMousePressEvent(ev)

    assert selector_view.super_long_press_calls == 1
