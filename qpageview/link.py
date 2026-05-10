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
Generic Link class and handling of links (clickable areas on a Page).

The link area is in coordinates between 0.0 and 1.0, like Poppler does it.
This way we can easily compute where the link area is on a page in different
sizes or rotations.

"""
from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple, Optional, Any, Tuple

from PySide6.QtCore import Signal, QEvent, QRectF, Qt, QPoint
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QWidget

from .page import AbstractPage
from .rectangles import Rectangles

if TYPE_CHECKING:
    from .highlight import Highlighter
    from . import View

class Area(NamedTuple):
    left: float
    top: float
    right: float
    bottom: float

class Link:
    fileName: str = ""
    isExternal: bool = False
    targetPage: int = -1
    url: str = ""
    tooltip: str = ""
    area: Area = Area(0, 0, 0, 0)

    def __init__(
        self,
        left: float,
        top: float,
        right: float,
        bottom: float,
        url: Optional[str] = None,
        tooltip: Optional[str] = None
    ):
        self.area = Area(left, top, right, bottom)
        if url:
            self.url = url
            if "://" in url:
                self.isExternal = True
        if tooltip:
            self.tooltip = tooltip

    def rect(self) -> QRectF:
        """Return the area attribute as a QRectF()."""
        r = QRectF()
        r.setCoords(*self.area)
        return r


class Links(Rectangles):
    """Manages a list of Link objects.

    See the rectangles documentation for how to access the links.

    """
    def get_coords(self, link: Link) -> Area:
        return link.area

class LinkViewMixin:
    """Mixin class to enhance view.View with link capabilities."""

    #: (page, link) emitted when the user hovers a link
    linkHovered: Signal = Signal(AbstractPage, Link)

    #: (no args) emitted when the user does not hover a link anymore
    linkLeft: Signal = Signal()

    #: (event, page, link) emitted when the user clicks a link
    linkClicked: Signal = Signal(QEvent, AbstractPage, Link)

    #: (event, page, link) emitted when a What's This or Tooltip is requested.
    #: The event's type determines the type of this help event.
    linkHelpRequested: Signal = Signal(QEvent, AbstractPage, Link)

    #: whether to actually enable Link handling
    linksEnabled: bool = True

    def __init__(self, parent: Optional[QWidget] = None, **kwargs: Any):
        self._currentLinkId: Optional[int] = None
        self._linkHighlighter: Optional[Highlighter] = None
        super().__init__(parent, **kwargs)

    def setLinkHighlighter(self, highlighter: Optional[Highlighter]) -> None:
        """Sets a Highlighter (see highlight.py) to highlight a link on hover.

        Use None to remove an active Highlighter. By default, no highlighter is
        set to highlight links on hover.

        To be able to actually *use* highlighting, be sure to also mix in the
        HighlightViewMixin class from the highlight module.

        """
        self._linkHighlighter = highlighter

    def linkHighlighter(self) -> Optional[Highlighter]:
        """Return the currently set Highlighter, if any.

        By default, no highlighter is set to highlight links on hover, and None
        is returned in that case.

        """
        return self._linkHighlighter

    def adjustCursor(self, pos: QPoint) -> None:
        """Adjust the cursor if pos is on a link (and linksEnabled is True).

        Also emits signals when the cursor enters or leaves a link.

        """
        if self.linksEnabled:
            page, link = self.linkAt(pos)
            if link:
                lid = id(link)
            else:
                lid = None
            if lid != self._currentLinkId:
                if self._currentLinkId is not None:
                    self.linkHoverLeave()
                self._currentLinkId = lid
                if lid is not None:
                    assert page and link  # for type checker - SP
                    self.linkHoverEnter(page, link)
            if link:
                return  # do not call super() if we are on a link
        super().adjustCursor(pos)

    def linkAt(self: View, pos: QPoint) -> Tuple[Optional[AbstractPage], Optional[Link]]:
        """If the pos (in the viewport) is over a link, return a (page, link) tuple.

        Otherwise, returns (None, None).

        """
        pos = pos - self.layoutPosition()
        page = self._pageLayout.pageAt(pos)
        if page:
            links = page.linksAt(pos - page.pos())
            if links:
                return page, links[0]
        return None, None

    def linkHoverEnter(self: View, page: AbstractPage, link: Link) -> None:
        """Called when the mouse hovers over a link.

        The default implementation emits the linkHovered(page, link) signal,
        sets a pointing hand mouse cursor, and, if a Highlighter was set using
        setLinkHighlighter(), highlights the link. You can reimplement this
        method to do something different.

        """
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.linkHovered.emit(page, link)
        if self._linkHighlighter:
            self.highlight({page: [link.rect()]}, self._linkHighlighter, 3000)

    def linkHoverLeave(self) -> None:
        """Called when the mouse does not hover a link anymore.

        The default implementation emits the linkLeft() signal, sets a default
        mouse cursor, and, if a Highlighter was set using setLinkHighlighter(),
        removes the highlighting of the current link. You can reimplement this
        method to do something different.

        """
        self.unsetCursor()
        self.linkLeft.emit()
        if self._linkHighlighter:
            self.clearHighlight(self._linkHighlighter)

    def linkClickEvent(self, ev: QMouseEvent, page: AbstractPage, link: Link) -> None:
        """Called when a link is clicked.

        The default implementation emits the linkClicked(event, page, link)
        signal. The event can be used for things like determining which button
        was used, and which keyboard modifiers were in effect.

        """
        self.linkClicked.emit(ev, page, link)

    def linkHelpEvent(self, ev: QMouseEvent, page: AbstractPage, link: Link) -> None:
        """Called when a ToolTip or WhatsThis wants to appear.

        The default implementation emits the linkHelpRequested(event, page, link)
        signal. Using the event you can find the position, and the type of the
        help event.

        """
        self.linkHelpRequested.emit(ev, page, link)

    def event(self, ev: QMouseEvent) -> bool:
        """Reimplemented to handle HelpEvent for links."""
        if self.linksEnabled and ev.type() in (QEvent.Type.ToolTip, QEvent.Type.WhatsThis):
            page, link = self.linkAt(ev.position().toPoint())
            if link:
                self.linkHelpEvent(ev, page, link)  # type: ignore - page is valid if link is valid - SP
                return True
        return super().event(ev)

    def mousePressEvent(self, ev: QMouseEvent) -> None:
        """Implemented to detect clicking a link and calling linkClickEvent()."""
        if self.linksEnabled:
            page, link = self.linkAt(ev.position().toPoint())
            if link:
                self.linkClickEvent(ev, page, link)  # type: ignore - page is valid if link is valid - SP
                return
        super().mousePressEvent(ev)

    def leaveEvent(self, ev: QMouseEvent) -> None:
        """Implemented to leave a link, might there still be one hovered."""
        if self.linksEnabled and self._currentLinkId is not None:
            self.linkHoverLeave()
            self._currentLinkId = None
        super().leaveEvent(ev)
