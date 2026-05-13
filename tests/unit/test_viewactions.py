import pytest
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QToolBar

from qpageview import FixedScale
from qpageview.constants import (
    FitBoth, FitHeight, FitWidth, Horizontal, Rotate_0, Rotate_90,
    Vertical,
)
from qpageview.page import BlankPage
from qpageview.view import View, ViewProperties
from qpageview.viewactions import PagerAction, ViewActions, ZoomerAction


@pytest.fixture(scope="function")
def view(qtbot):
    v = View()
    v.resize(640, 480)
    v.show()
    qtbot.addWidget(v)
    return v

@pytest.fixture(scope="function")
def pages():
    return [BlankPage() for _ in range(4)]

@pytest.fixture(scope="function")
def actions(qtbot):
    a = ViewActions()
    qtbot.addWidget(a.pager.createWidget(QToolBar()))
    qtbot.addWidget(a.zoomer.createWidget(QToolBar()))
    return a

def test_view_actions_action_names():
    names = ViewActions.names()

    assert "print" in names
    assert "fit_width" in names
    assert "fit_height" in names
    assert "fit_both" in names
    assert "zoom_natural" in names
    assert "zoom_in" in names
    assert "zoom_out" in names
    assert "layout_single" in names
    assert "layout_double_left" in names
    assert "layout_double_right" in names
    assert "layout_raster" in names
    assert "vertical" in names
    assert "horizontal" in names
    assert "continuous" in names
    assert "reload" in names
    assert "previous_page" in names
    assert "next_page" in names
    assert "pager" in names
    assert "magnifier" in names

def test_view_actions_set_view(view, pages, actions):
    view.setPages(pages)
    actions.setView(view)

    assert actions.print.isEnabled() is True
    assert actions.vertical.isChecked() is True
    assert actions.horizontal.isChecked() is False
    assert actions.continuous.isChecked() is True
    assert actions.pager.pageCount() == 4
    assert actions.pager.currentPageNumber() == 1
    assert actions.previous_page.isEnabled() is False
    assert actions.next_page.isEnabled() is True

def test_view_actions_view_requested_signal(actions, qtbot):
    with qtbot.waitSignal(actions.viewRequested):
        actions.view()

def test_view_actions_update_from_properties(actions):
    props = ViewProperties()
    props.pageLayoutMode = "double_left"
    props.orientation = Horizontal
    props.continuousMode = False
    props.zoomFactor = 1.5
    props.viewMode = FitHeight

    actions.updateFromProperties(props)

    assert actions.layout_double_left.isChecked() is True
    assert actions.horizontal.isChecked() is True
    assert actions.vertical.isChecked() is False
    assert actions.continuous.isChecked() is False
    assert actions.fit_height.isChecked() is True
    assert actions.zoomer.zoomFactor() == 1.5

def test_view_actions_slot_view_mode(actions, view):
    actions.setView(view)

    actions.slotViewMode(actions.fit_width)
    assert view.viewMode() == FitWidth

    actions.slotViewMode(actions.fit_height)
    assert view.viewMode() == FitHeight

    actions.slotViewMode(actions.fit_both)
    assert view.viewMode() == FitBoth

def test_view_actions_slot_zoom_original(actions, view):
    view.setZoomFactor(2.0)
    actions.setView(view)
    actions.slotZoomOriginal()

    assert view.zoomFactor() == 1.0

def test_view_actions_slot_zoom_in_out(actions, view):
    actions.setView(view)
    initial = view.zoomFactor()

    actions.slotZoomIn()
    assert view.zoomFactor() > initial

    actions.slotZoomOut()
    assert view.zoomFactor() < view.MAX_ZOOM

def test_view_actions_slot_zoom_factor(actions, view):
    actions.setView(view)
    actions.zoomer.setZoomFactor(2.25)

    assert view.zoomFactor() == 2.25

def test_view_actions_slow_rotate_left_right(actions, view):
    actions.setView(view)

    actions.slotRotateRight()
    assert view.rotation() == Rotate_90

    actions.slotRotateLeft()
    assert view.rotation() == Rotate_0

def test_view_actions_slot_page_layout_mode(actions, view):
    actions.setView(view)

    actions.slotPageLayoutMode(actions.layout_single)
    assert view.pageLayoutMode() == "single"

    actions.slotPageLayoutMode(actions.layout_double_left)
    assert view.pageLayoutMode() == "double_left"

    actions.slotPageLayoutMode(actions.layout_double_right)
    assert view.pageLayoutMode() == "double_right"

    actions.slotPageLayoutMode(actions.layout_raster)
    assert view.pageLayoutMode() == "raster"

def test_view_actions_slot_page_layout_mode_smart_enabled(actions, view):
    actions.setView(view)
    view.setOrientation(Horizontal)

    actions.smartLayoutOrientationEnabled = True
    actions.slotPageLayoutMode(actions.layout_double_left)

    assert view.pageLayoutMode() == "double_left"
    assert view.orientation() == Vertical

def test_view_actions_slot_page_layout_mode_smart_disabled(actions, view):
    actions.setView(view)
    view.setOrientation(Horizontal)

    actions.smartLayoutOrientationEnabled = False
    actions.slotPageLayoutMode(actions.layout_double_right)

    assert view.pageLayoutMode() == "double_right"
    assert view.orientation() == Horizontal

def test_view_actions_slot_orientation(actions, view):
    actions.setView(view)

    actions.slotOrientation(actions.vertical)
    assert view.orientation() == Vertical

    actions.slotOrientation(actions.horizontal)
    assert view.orientation() == Horizontal

def test_view_actions_slot_orientation_smart_enabled(actions, view):
    actions.setView(view)
    view.setPageLayoutMode("double_left")

    actions.smartLayoutOrientationEnabled = True
    actions.slotOrientation(actions.horizontal)

    assert view.orientation() == Horizontal
    assert view.pageLayoutMode() == "single"

def test_view_actions_slot_continuous_mode(actions, view):
    actions.setView(view)

    actions.continuous.setChecked(False)
    actions.slotContinuousMode()
    assert view.continuousMode() is False

    actions.continuous.setChecked(True)
    actions.slotContinuousMode()
    assert view.continuousMode() is True

def test_view_actions_slot_previous_and_next(actions, view, pages):
    view.setPages(pages)
    actions.setView(view)

    view.setCurrentPageNumber(3)
    actions.slotPreviousPage()
    assert view.currentPageNumber() == 2

    actions.slotNextPage()
    assert view.currentPageNumber() == 3

def test_view_actions_slot_set_page_number(actions, view, pages):
    view.setPages(pages)
    actions.setView(view)

    actions.pager.setCurrentPageNumber(4)
    assert view.currentPageNumber() == 4

def test_view_actions_update_pager_actions(actions, view, pages):
    view.setPages(pages)
    actions.setView(view)

    view.setCurrentPageNumber(1)
    actions.updatePagerActions()
    assert actions.previous_page.isEnabled() is False
    assert actions.next_page.isEnabled() is True

    view.setCurrentPageNumber(4)
    actions.updatePagerActions()
    assert actions.previous_page.isEnabled() is True
    assert actions.next_page.isEnabled() is False

def test_pager_action_page_count(qtbot):
    obj = QObject()
    pager = PagerAction(obj)
    toolbar = QToolBar()
    w = pager.createWidget(toolbar)
    qtbot.addWidget(w)

    pager.setPageCount(10)
    pager.setCurrentPageNumber(8)
    assert pager.currentPageNumber() == 8

    pager.setPageCount(3)
    assert pager.currentPageNumber() == 3

    pager.setCurrentPageNumber(0)
    assert pager.currentPageNumber() == 3

def test_pager_action_signal(qtbot):
    obj = QObject()
    pager = PagerAction(obj)
    toolbar = QToolBar()
    w = pager.createWidget(toolbar)
    qtbot.addWidget(w)

    pager.setPageCount(5)
    with qtbot.waitSignal(pager.currentPageNumberChanged) as blocker:
        pager.setCurrentPageNumber(2)

    assert blocker.args == [2]
    assert pager.currentPageNumber() == 2

def test_pager_action_set_display_format():
    obj = QObject()
    pager = PagerAction(obj)
    with pytest.raises(AssertionError):
        pager.setDisplayFormat("Page only")

def test_zoomer_action_defaults():
    obj = QObject()
    zoomer = ZoomerAction(obj)

    assert zoomer.viewMode() == FixedScale
    assert zoomer.zoomFactor() == 1.0
    assert len(zoomer.viewModes()) >= 3
    assert 1.0 in zoomer.zoomFactors()

def test_zoomer_action_signal(qtbot):
    obj = QObject()
    zoomer = ZoomerAction(obj)

    with qtbot.waitSignal(zoomer.zoomFactorChanged) as blocker:
        zoomer.setZoomFactor(1.5)

    assert blocker.args == [1.5]
    assert zoomer.zoomFactor() == 1.5

def test_zoomer_action_set_current_index(qtbot):
    obj = QObject()
    zoomer = ZoomerAction(obj)
    toolbar = QToolBar()
    w = zoomer.createWidget(toolbar)
    qtbot.addWidget(w)

    zoomer.setCurrentIndex(1)
    assert zoomer.viewMode() == zoomer.viewModes()[1][0]

    zoomer.setCurrentIndex(len(zoomer.viewModes()))
    assert zoomer.zoomFactor() == zoomer.zoomFactors()[0]

def test_zoomer_action_custom_modes_and_factors(qtbot):
    obj = QObject()
    zoomer = ZoomerAction(obj)
    toolbar = QToolBar()
    w = zoomer.createWidget(toolbar)
    qtbot.addWidget(w)

    custom_modes = ((FitWidth, "W"), (FitBoth, "P"))
    custom_factors = (0.25, 0.5, 1.0)
    zoomer.setViewModes(custom_modes)
    zoomer.setZoomFactors(custom_factors)
    zoomer.setZoomFormat("{0:.1%}")

    assert zoomer.viewModes() == custom_modes
    assert zoomer.zoomFactors() == custom_factors
    assert zoomer.zoomFormat() == "{0:.1%}"
