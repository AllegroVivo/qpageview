# -*- coding: utf-8 -*-
#
# This file is part of the qpageview package.
#
# Copyright (c) 2019 - 2019 by Wilbert Berendsen
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# See http://www.gnu.org/licenses/ for more information.

"""
View mixin class to display QWidgets on top of a Page.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple, Optional, Dict, Union, Iterator

from PySide6.QtCore import QPoint, Qt, QRect
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QWidget

from . import constants
from . import util

if TYPE_CHECKING:
    from .page import AbstractPage


class OverlayData(NamedTuple):
    page: AbstractPage
    point: Optional[QPoint]
    rect: Optional[QRect]
    alignment: Qt.AlignmentFlag


class WidgetOverlayViewMixin:
    """Mixin class to add widgets to be displayed on top of pages.

    Widgets are added using addWidget(), and become children of the viewport.

    This class adds the following instance attribute:

    deleteUnusedOverlayWidgets = True

        If True, unused widgets are deleted using QObject.deleteLater().
        Otherwise, only the parent is set to None.  A widget becomes unused if
        the Page it was added to disappears from the page layout.

    """

    deleteUnusedOverlayWidgets: bool = True

    def __init__(self, parent: Optional[QWidget] = None):
        self._widgets: Dict[QWidget, OverlayData] = {}
        super().__init__(parent)

    def addWidget(
        self,
        widget: QWidget,
        page: AbstractPage,
        where: Optional[Union[QPoint, QRect]] = None,
        alignment: Optional[Qt.AlignmentFlag] = None
    ):
        """Add widget to be displayed on top of page.

        The widget becomes a child of the viewport.

        The `where` argument can be a QPoint or a QRect. If a rect is given,
        the widget is resized to occupy that rectangle. The rect should be in
        page coordinates. When the zoom factor is changed, the widget will be
        resized.

        If a point is given, the widget is not resized and aligned on the point
        using the specified alignment (top-left if None).

        If where is None, the widget occupies the whole page.

        You can also use this method to change the page or rect for a widget
        that already has been added.

        """
        if not alignment:
            alignment = Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        # translate rect to original coordinates
        rect = None
        point = None
        if where is not None:
            if isinstance(where, QPoint):
                point = page.mapFromPage().point(where).toPoint()
            else:
                rect = page.mapFromPage().rect(where).toRect()
        else:
            rect = page.pageRect().toRect()
        widget.setParent(self.viewport())
        self._widgets[widget] = OverlayData(page, point, rect, alignment)
        self._updateWidget(widget)
        widget.setVisible(page in set(self.visiblePages()))

    def removeWidget(self, widget: QWidget) -> None:
        """Remove the widget.

        The widget is not deleted, but its parent is set to None.

        """
        try:
            del self._widgets[widget]
        except KeyError:
            pass
        else:
            widget.setParent(None)

    def widgets(self, page: Optional[AbstractPage] = None) -> Iterator[QWidget]:
        """Yield all widgets (for the Page if given)."""
        if page:
            for widget, d in self._widgets.items():
                if d.page is page:
                    yield widget
        else:
            for widget in self._widgets:
                yield widget

    def removeWidgets(self, page: Optional[AbstractPage] = None) -> None:
        """Remove all widgets (for the Page if given).

        The widgets are not deleted, but their parent is set to None.

        """
        if page:
            for widget in list(self.widgets(page)):
                widget.setParent(None)
                del self._widgets[widget]
        else:
            for widget in self._widgets:
                widget.setParent(None)
            self._widgets.clear()

    def _updateWidget(self, widget: QWidget) -> None:
        """Internal. Updates size and position of the specified widget."""
        d = self._widgets[widget]
        pos = self.layoutPosition() + d.page.pos()
        if d.point:
            point = pos + d.page.mapToPage().point(d.point)
            geom = util.alignrect(widget.geometry(), point, d.alignment)
        else:  # d.rect:
            assert d.rect is not None  # for type checker - SP
            rect = d.page.mapToPage().rect(d.rect)
            geom = rect.translated(pos)
        assert geom is not None  # for type checker - SP
        widget.setGeometry(geom)

    def _updateWidgets(self) -> None:
        """Internal. Updates size and position of the widgets."""
        pages = set(self.visiblePages())
        remove = []
        for widget, d in self._widgets.items():
            if d.page in self.pageLayout():
                self._updateWidget(widget)
                widget.setVisible(d.page in pages)
            else:
                remove.append(widget)
        # remove widgets that are not used anymore
        for w in remove:
            w.setParent(None)
            del self._widgets[w]
        if self.deleteUnusedOverlayWidgets:
            for w in remove:
                w.deleteLater()

    def updatePageLayout(self, lazy: bool = False) -> None:
        """Reimplemented to update the size and position of the widgets."""
        super().updatePageLayout(lazy)
        self._updateWidgets()

    def scrollContentsBy(self, dx: int, dy: int) -> None:
        """Reimplemented to scroll the page widgets along with the layout."""
        super().scrollContentsBy(dx, dy)
        d = QPoint(dx, dy)
        for widget in self._widgets.keys():
            widget.move(widget.pos() + d)

    def resizeEvent(self, ev: QResizeEvent) -> None:
        """Reimplemented to keep page widgets in the right position."""
        super().resizeEvent(ev)
        # in fixed scale mode, call _updateWidgets(). In other view modes,
        # updatePageLayout() is called which calls _updateWidgets() anyway.
        if self.viewMode() == constants.FixedScale:
            self._updateWidgets()
