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
SidebarView, a special View with miniatures to use as a sidebar for a View.

Automatically displays all pages in a view in small size, and makes it easier
to browse large documents.

"""
from __future__ import annotations

from typing import Optional, Any

from PySide6.QtCore import QEvent, QMargins, QRect, Qt
from PySide6.QtGui import QPainter, QPaintEvent, QWheelEvent, QKeyEvent, QResizeEvent
from PySide6.QtWidgets import QWidget

from .constants import (
    Orientation,
    FitWidth,
    FitHeight,
    Vertical,
    Horizontal,
)
from .selector import SelectorViewMixin
from .view import View
from .util import LongMousePressMixin


class SidebarView(SelectorViewMixin, LongMousePressMixin, View):
    """A special View with miniatures to use as a sidebar for a View.

    Automatically displays all pages in a view in small size, and makes it
    easier to browse large documents. Use setView() to connect a View, and
    it automatically shows the pages, also when the view is changed.

    """

    MAX_ZOOM: float = 1.0
    pagingOnScrollEnabled: bool = False
    wheelZoomingEnabled: bool = False
    firstPageNumber: int = 1
    scrollupdatespersec: int = 100

    autoOrientationEnabled: bool = True

    def __init__(self, parent: Optional[QWidget] = None, **kwargs: Any):
        super().__init__(parent, **kwargs)
        self._view: Optional[View] = None
        self.setOrientation(Vertical)
        self.pageLayout().spacing = 1
        self.pageLayout().setMargins(QMargins(0, 0, 0, 0))
        self.pageLayout().setPageMargins(QMargins(4, 4, 4, 20))
        self.setLayoutFontHeight()
        self.currentPageNumberChanged.connect(self.viewport().update)

    def setOrientation(self, orientation: Orientation) -> None:
        """Reimplemented to also set the corresponding view mode."""
        super().setOrientation(orientation)
        if orientation == Vertical:
            self.setViewMode(FitWidth)
        else:
            self.setViewMode(FitHeight)

    def setLayoutFontHeight(self) -> None:
        """Reads the current font height and reserves enough space in the layout."""
        self.pageLayout().pageMargins().setBottom(self.fontMetrics().height())
        self.updatePageLayout()

    def setView(self, view: Optional[View]) -> None:
        """Connects to a View, or disconnects the current view if view is None."""
        if view is not self._view:
            if self._view:
                self.currentPageNumberChanged.disconnect(self._view.setCurrentPageNumber)
                self._view.currentPageNumberChanged.disconnect(self.slotCurrentPageNumberChanged)
                self._view.pageLayoutUpdated.disconnect(self.slotLayoutUpdated)
                self.clear()
            self._view = view
            if view:
                self.slotLayoutUpdated()
                self.setCurrentPageNumber(view.currentPageNumber())
                self.currentPageNumberChanged.connect(view.setCurrentPageNumber)
                view.currentPageNumberChanged.connect(self.slotCurrentPageNumberChanged)
                view.pageLayoutUpdated.connect(self.slotLayoutUpdated)

    def slotLayoutUpdated(self) -> None:
        """Called when the layout of the connected view is updated."""
        self.pageLayout()[:] = (p.copy(self) for p in self._view.pageLayout())
        self.pageLayout().rotation = self._view.pageLayout().rotation
        self.updatePageLayout()

    def slotCurrentPageNumberChanged(self, num: int) -> None:
        """Called when the page number in the connected view changes.

        Does not scroll but updates the current page mark in our View.

        """
        self._currentPageNumber = num
        self.viewport().update()

    def paintEvent(self, ev: QPaintEvent) -> None:
        """Reimplemented to print page numbers and a selection box."""
        painter = QPainter(self.viewport())
        layout = self.pageLayout()
        for p, rect in self.pagesToPaint(ev.rect(), painter):
            ## draw selection background on current page
            if p is self.currentPage():
                bg = rect + layout.pageMargins()
                painter.fillRect(bg, self.palette().highlight())
                painter.setPen(self.palette().highlightedText().color())
            else:
                painter.setPen(self.palette().text().color())
            # draw text
            textr = QRect(rect.x(), rect.bottom(), rect.width(), layout.pageMargins().bottom())
            painter.drawText(textr, Qt.AlignmentFlag.AlignCenter, str(layout.index(p) + self.firstPageNumber))
        super().paintEvent(ev)

    def wheelEvent(self, ev: QWheelEvent) -> None:
        """Reimplemented to page instead of scroll."""
        if ev.angleDelta().y() > 0:
            self.gotoPreviousPage()
        elif ev.angleDelta().y() < 0:
            self.gotoNextPage()

    def keyPressEvent(self, ev: QKeyEvent) -> None:
        """Reimplemented to page instead of scroll."""
        if ev.key() in (Qt.Key.Key_PageDown, Qt.Key.Key_Down):
            self.gotoNextPage()
        elif ev.key() in (Qt.Key.Key_PageUp, Qt.Key.Key_Up):
            self.gotoPreviousPage()
        elif ev.key() == Qt.Key.Key_End:
            self.setCurrentPageNumber(self.pageCount())
        elif ev.key() == Qt.Key.Key_Home:
            self.setCurrentPageNumber(1)
        else:
            super().keyPressEvent(ev)

    def resizeEvent(self, ev: QResizeEvent) -> None:
        """Reimplemented to auto-change the orientation if desired."""
        super().resizeEvent(ev)
        if self.autoOrientationEnabled:
            s = ev.size()
            if s.width() > s.height() and self.orientation() == Vertical:
                self.setOrientation(Horizontal)
            elif s.width() < s.height() and self.orientation() == Horizontal:
                self.setOrientation(Vertical)

    def changeEvent(self, ev: QEvent) -> None:
        """Reimplemented to set the correct font height for the page numbers."""
        super().changeEvent(ev)
        if ev.type() in (QEvent.Type.ApplicationFontChange, QEvent.Type.FontChange):
            self.setLayoutFontHeight()
