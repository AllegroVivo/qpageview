# -*- coding: utf-8 -*-
#
# This file is part of the qpageview package.
#
# Copyright (c) 2010 - 2019 by Wilbert Berendsen
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
Highlight rectangular areas inside a View.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Dict

import collections
from weakref import WeakKeyDictionary, ref
from typing import Optional, Sequence, Tuple

from PySide6.QtCore import QRect, QRectF, QTimer, QMargins
from PySide6.QtGui import QPainter, QPen, QColor, QPaintEvent
from PySide6.QtWidgets import QApplication, QWidget

if TYPE_CHECKING:
    from .page import AbstractPage
    from . import View

class Highlighter:
    """A Highlighter can draw rectangles to highlight e.g. links in a View.

    An instance represents a certain type of highlighting, e.g. of a particular
    style. The paintRects() method is called with a list of rectangles that
    need to be drawn.

    To implement different highlighting behaviour just inherit paintRects().
    The default implementation of paintRects() uses the `color` attribute to get
    the color to use and the `lineWidth` (default: 2) and `radius` (default: 3)
    attributes.

    `lineWidth` specifies the thickness in pixels of the border drawn, `radius`
    specifies the distance in pixels the border is drawn (by default with
    rounded corners) around the area to be highlighted. `color` is set to None
    by default, causing the paintRects method to choose the application's
    palette highlight color.

    """

    lineWidth: int = 2
    radius: int = 3
    color: Optional[QColor] = None

    def paintRects(self, painter: QPainter, rects: Sequence[QRectF]):
        """Override this method to implement different drawing behaviour."""
        color = self.color if self.color is not None else QApplication.palette().highlight().color()
        pen = QPen(color)
        pen.setWidth(self.lineWidth)
        painter.setPen(pen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rad = self.radius
        for r in rects:
            r.adjust(-rad, -rad, rad, rad)
            painter.drawRoundedRect(r, rad, rad)


class HighlightViewMixin:
    """Mixin methods vor view.View for highlighting areas.

    This mixin allows for highlighting rectangular areas on pages. You
    can highlight different sets of areas independently, using different
    Highlighter instances.

    Highlighting can be set to stay on forever or to disappear after a
    certain amount of microseconds.

    If desired, the View can be scrolled to show the highlighted areas.
    How the highlighting is drawn is determined by the paintRects() method
    of Highlighter.

    """
    def __init__(self, parent: Optional[QWidget] = None, **kwargs: Any):
        self._highlights: WeakKeyDictionary[Highlighter, Tuple[WeakKeyDictionary[AbstractPage, List[QRectF]], Optional[QTimer]]] = WeakKeyDictionary()
        self._defaultHighlighter: Optional[Highlighter] = None
        super().__init__(parent, **kwargs)

    def defaultHighlighter(self) -> Highlighter:
        """Return a default highlighter, creating it if necessary."""
        if self._defaultHighlighter is None:
            self._defaultHighlighter = Highlighter()
        assert self._defaultHighlighter is not None  # for type checker - SP
        return self._defaultHighlighter

    def setDefaultHighlighter(self, highlighter: Highlighter) -> None:
        """Set a Highlighter to use as the default highlighter."""
        self._defaultHighlighter = highlighter

    # noinspection PyMethodMayBeStatic
    def highlightRect(self, areas: Dict[AbstractPage, List[QRectF]]) -> QRect:
        """Return the bounding rect of the areas."""
        boundingRect = QRect()
        for page, rects in areas.items():
            f = page.mapToPage(1, 1).rect
            pbound = QRect()
            for r in rects:
                pbound |= f(r)
            boundingRect |= pbound.translated(page.pos())
        return boundingRect

    def highlight(
        self: View,
        areas: Dict[AbstractPage, List[QRectF]],
        highlighter: Optional[Highlighter] = None,
        msec: int = 0,
        scroll: bool = False,
        margins: Optional[QMargins] = None,
        allowKinetic: bool = True
    ) -> None:
        """Highlight the areas dict using the given or default highlighter.

        The areas dict maps Page objects to lists of rectangles, where the
        rectangle is a QRectF() inside (0, 0, 1, 1) like the area attribute of
        a Link.

        If the highlighter is not specified, the default highlighter will be
        used.

        If msec > 0, the highlighting will vanish after that many microseconds.

        If scroll is True, the View will be scrolled to show the areas to
        highlight if needed, using View.ensureVisible(highlightRect(areas),
        margins, allowKinetic).

        """
        if highlighter is None:
            highlighter = self.defaultHighlighter()

        if scroll:
            self.ensureVisible(self.highlightRect(areas), margins, allowKinetic)
            if msec:
                msec += self.remainingScrollTime()

        d = WeakKeyDictionary(areas)
        if msec:
            selfref = ref(self)
            def clear():
                # noinspection PyMethodFirstArgAssignment
                self = selfref()
                if self:
                    self.clearHighlight(highlighter)
            t = QTimer(singleShot=True)
            t.timeout.connect(clear)
            t.start(msec)
        else:
            t = None
        self.clearHighlight(highlighter)
        self._highlights[highlighter] = (d, t)
        self.viewport().update()

    def clearHighlight(self: View, highlighter: Optional[Highlighter] = None) -> None:
        """Removes the highlighted areas of the given or default highlighter."""
        if highlighter is None:
            highlighter = self.defaultHighlighter()
        assert highlighter is not None  # for type checker - SP
        try:
            (d, t) = self._highlights[highlighter]
        except KeyError:
            return
        if t is not None: t.stop()
        del self._highlights[highlighter]
        self.viewport().update()

    def isHighlighting(self, highlighter: Optional[Highlighter] = None) -> bool:
        """Return True if the given or default highlighter is active."""
        if highlighter is None:
            highlighter = self.defaultHighlighter()
        return highlighter in self._highlights

    def highlightUrls(
        self,
        urls: Sequence[str],
        highlighter: Optional[Highlighter] = None,
        msec: int = 0,
        scroll: bool = False,
        margins: Optional[QMargins] = None,
        allowKinetic: bool = True
    ) -> None:
        """Convenience method highlighting the specified urls in the Document.

        The urls argument is a list of urls (str); the other arguments
        are used for calling highlight() on the areas returned by
        getUrlHighlightAreas(urls).

        """
        areas = self.getUrlHighlightAreas(urls)
        if areas:
            self.highlight(areas, highlighter, msec, scroll, margins, allowKinetic)

    def getUrlHighlightAreas(self: View, urls: Sequence[str]) -> Optional[Dict[AbstractPage, List[QRectF]]]:
        """Return the areas to highlight all occurrences of the specified URLs.

        The areas are found in the dictionary returned by document().urls().
        URLs that are not in that dictionary are silently skipped.
        If there is no document set this method returns nothing.

        """
        doc = self.document()
        if doc:
            u = doc.urls()
            if u:
                pages = doc.pages()
                areas = collections.defaultdict(list)
                for url in urls:
                    d = u.get(url)
                    if d:
                        for n, linkareas in d.items():
                            rects = []
                            for a in linkareas:
                                r = QRectF()
                                r.setCoords(*a)
                                rects.append(r)
                            areas[pages[n]].extend(rects)
                return areas

    def paintEvent(self: View, ev: QPaintEvent) -> None:
        """Paint the highlighted areas in the viewport."""
        super().paintEvent(ev)  # first paint the contents
        painter = QPainter(self.viewport())
        for highlighter, (d, t) in self._highlights.items():
            for page, rect in self.pagesToPaint(ev.rect(), painter):
                try:
                    areas = d[page]
                except KeyError:
                    continue
                rectarea = page.mapFromPage(1, 1).rect(rect)
                f = page.mapToPage(1, 1).rect
                rects = [f(area) for area in areas if area & rectarea]
                highlighter.paintRects(painter, rects)
