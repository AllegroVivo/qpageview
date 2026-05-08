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
Small utilities and simple base classes for the qpageview module.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple, Iterator

import collections
from contextlib import contextmanager
from typing import Union, Any

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt, QEvent, QObject
from PySide6.QtGui import QBitmap, QMouseEvent, QRegion, QTransform, QPainter, QImage
from PySide6.QtWidgets import QApplication

from .constants import Rotation, Rotate_90, Rotate_270

if TYPE_CHECKING:
    from .sidebarview import SidebarView


class Rectangular:
    """Defines a Qt-inspired and -based interface for rectangular objects.

    The attributes x, y, width and height default to 0 at the class level
    and can be set and read directly.

    For convenience, Qt-styled methods are available to access and modify these
    attributes.

    """
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

    def setPos(self, point: QPoint) -> None:
        """Set the x and y coordinates from the given QPoint point."""
        self.x = point.x()
        self.y = point.y()

    def pos(self) -> QPoint:
        """Return our x and y coordinates as a QPoint(x, y)."""
        return QPoint(self.x, self.y)

    def setSize(self, size: QSize) -> None:
        """Set the height and width attributes from the given QSize size."""
        self.width = size.width()
        self.height = size.height()

    def size(self) -> QSize:
        """Return the height and width attributes as a QSize(width, height)."""
        return QSize(self.width, self.height)

    def setGeometry(self, rect: QRect) -> None:
        """Set our x, y, width and height directly from the given QRect."""
        self.x, self.y, self.width, self.height = rect.getRect()

    def geometry(self) -> QRect:
        """Return our x, y, width and height as a QRect."""
        return QRect(self.x, self.y, self.width, self.height)

    def rect(self) -> QRect:
        """Return QRect(0, 0, width, height)."""
        return QRect(0, 0, self.width, self.height)


class MapToPage:
    """Simple class wrapping a QTransform to map rect and point to page coordinates."""
    def __init__(self, transform: QTransform):
        self.t: QTransform = transform

    def rect(self, rect: Union[QRect, QRectF]) -> QRect:
        """Convert QRect or QRectF to a QRect in page coordinates."""
        return self.t.mapRect(QRectF(rect)).toRect()  # type: ignore - typechecker can't figure out the overloads - SP

    def point(self, point: Union[QPoint, QPointF]) -> QPoint:
        """Convert QPointF or QPoint to a QPoint in page coordinates."""
        return self.t.map(QPointF(point)).toPoint()  # type: ignore - typechecker can't figure out the overloads - SP


class MapFromPage(MapToPage):
    """Simple class wrapping a QTransform to map rect and point from page to original coordinates."""
    def rect(self, rect: Union[QRect, QRectF]) -> QRectF:
        """Convert QRect or QRectF to a QRectF in original coordinates."""
        return self.t.mapRect(QRectF(rect))  # type: ignore - typechecker can't figure out the overloads - SP

    def point(self, point: Union[QPoint, QPointF]) -> QPointF:
        """Convert QPointF or QPoint to a QPointF in original coordinates."""
        return self.t.map(QPointF(point))  # type: ignore - typechecker can't figure out the overloads - SP

LongPressAttrs = Tuple[
    QEvent.Type,
    QPointF,
    QPointF,
    QPointF,
    Qt.MouseButton,
    Qt.MouseButton,
    Qt.KeyboardModifier
]

class LongMousePressMixin:
    """Mixin class to add support for long mouse press to a QWidget.

    To handle a long mouse press event, implement longMousePressEvent().

    """

    #: Whether to enable handling of long mouse presses; set to False to disable
    longMousePressEnabled: bool = True

    #: Allow moving some pixels before a long mouse press is considered a drag
    longMousePressTolerance: int = 3

    #: How long to press a mouse button (in msec) for a long press
    longMousePressTime: int = 800

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._longPressTimer: Optional[int] = None
        self._longPressAttrs: Optional[LongPressAttrs] = None
        self._longPressPos: Optional[QPoint] = None

    def _startLongMousePressEvent(self: SidebarView, ev: QMouseEvent) -> None:
        """Start the timer for a QMouseEvent mouse press event."""
        self._cancelLongMousePressEvent()
        self._longPressTimer = self.startTimer(self.longMousePressTime)
        # copy the event's attributes because Qt might reuse the event
        self._longPressAttrs = (
            ev.type(), ev.position(), ev.scenePosition(),
            ev.globalPosition(), ev.button(), ev.buttons(),
            ev.modifiers()
        )
        self._longPressPos = ev.position().toPoint()

    def _checkLongMousePressEvent(self, ev: QMouseEvent) -> None:
        """Cancel the press event if the current event has moved more than 3 pixels."""
        if self._longPressTimer is not None:
            dist = (self._longPressPos - ev.position().toPoint()).manhattanLength()
            if dist > self.longMousePressTolerance:
                self._cancelLongMousePressEvent()

    def _cancelLongMousePressEvent(self: SidebarView) -> None:
        """Stop the timer for a long mouse press event."""
        if self._longPressTimer is not None:
            self.killTimer(self._longPressTimer)
            self._longPressTimer = None
            self._longPressAttrs = None
            self._longPressPos = None

    def longMousePressEvent(self, ev: QMouseEvent) -> None:
        """Implement this to handle a long mouse press event."""
        pass

    def timerEvent(self, ev):
        """Implemented to check for a long mouse button press."""
        if ev.timerId() == self._longPressTimer:
            assert self._longPressAttrs is not None  # for type checker - SP
            event = QMouseEvent(*self._longPressAttrs)
            self._cancelLongMousePressEvent()
            self.longMousePressEvent(event)
        super().timerEvent(ev)

    def mousePressEvent(self, ev: QMouseEvent) -> None:
        """Reimplemented to check for a long mouse button press."""
        if self.longMousePressEnabled:
            self._startLongMousePressEvent(ev)
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev: QMouseEvent) -> None:
        """Reimplemented to check for moves during a long press."""
        self._checkLongMousePressEvent(ev)
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev: QMouseEvent) -> None:
        """Reimplemented to cancel a long press."""
        self._cancelLongMousePressEvent()
        super().mouseReleaseEvent(ev)


class Point(QPoint):
    """An overflow-safe QPoint.

    This works around an oversight in PyQt, which does not
    constrain integer arguments to fixed sizes as used in C++,
    causing an OverflowError when those limits are exceeded.

    """
    def __init__(self, x: int, y: int):
        super().__init__(clamp_int32(x), clamp_int32(y))

    def setX(self, x: int) -> None:
        super().setX(clamp_int32(x))

    def setY(self, y: int) -> None:
        super().setY(clamp_int32(y))


def rotate(
    matrix: Union[QPainter, QTransform],
    rotation: Rotation,
    width: int,
    height: int,
    dest: bool = False
) -> None:
    """Rotate matrix inside a rectangular area of width x height.

    The ``matrix`` can be either a QPainter or a QTransform. The ``rotation``
    is 0, 1, 2 or 3, etc. (``Rotate_0``, ``Rotate_90``, etc...). If ``dest`` is
    True, ``width`` and ``height`` refer to the destination, otherwise to the
    source.

    """
    if rotation & Rotate_270:
        if dest or not rotation & Rotate_90:
            matrix.translate(width / 2, height / 2)
        else:
            matrix.translate(height / 2, width / 2)
        matrix.rotate(rotation * 90)
        if not dest or not rotation & Rotate_90:
            matrix.translate(width / -2, height / -2)
        else:
            matrix.translate(height / -2, width / -2)


def align(
    w: int,
    h: int,
    ow: int,
    oh: int,
    alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignCenter
) -> Tuple[int, int]:
    """Return (x, y) to align a rect w x h in an outer rectangle ow x oh.

    The alignment can be a combination of Qt.AlignmentFlag values.
    If w > ow, x = -1; and if h > oh, y = -1.

    """
    if w > ow:
        x = -1
    elif alignment & Qt.AlignmentFlag.AlignHCenter:
        x = (ow - w) // 2
    elif alignment & Qt.AlignmentFlag.AlignRight:
        x = ow - w
    else:
        x = 0
    if h > oh:
        y = -1
    elif alignment & Qt.AlignmentFlag.AlignVCenter:
        y = (oh - h) // 2
    elif alignment & Qt.AlignmentFlag.AlignBottom:
        y = oh - h
    else:
        y = 0
    return x, y


def alignrect(
    rect: QRect,
    point: QPoint,
    alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignCenter
) -> None:
    """Align rect with point according to the alignment.

    The alignment can be a combination of Qt.AlignmentFlag values.

    """
    rect.moveCenter(point)
    if alignment & Qt.AlignmentFlag.AlignLeft:
        rect.moveLeft(point.x())
    elif alignment & Qt.AlignmentFlag.AlignRight:
        rect.moveRight(point.x())
    if alignment & Qt.AlignmentFlag.AlignTop:
        rect.moveTop(point.y())
    elif alignment & Qt.AlignmentFlag.AlignBottom:
        rect.moveBottom(point.y())


def clamp[T](x: T, lower: T, upper: T) -> T:
    """Return x bounded such that lower <= x <= upper."""
    return lower if x < lower else upper if x > upper else x

def clamp_int32(x) -> int:
    """Return x bounded to the range of a 32-bit signed integer."""
    return clamp(x, -2**31, 2**31 - 1)


# Found at: https://stackoverflow.com/questions/1986152/why-doesnt-python-have-a-sign-function
def sign(x: int) -> int:
    """Return the sign of x: -1 if x < 0, 0 if x == 0, or 1 if x > 0."""
    return bool(x > 0) - bool(x < 0)


@contextmanager
def signalsBlocked(*objs: QObject) -> Iterator[None]:
    """Block the Signals of the given QObjects during the context."""
    blocks = [obj.blockSignals(True) for obj in objs]
    try:
        yield
    finally:
        for obj, block in zip(objs, blocks):
            obj.blockSignals(block)


def autoCropRect(image: QImage) -> QRect:
    """Return a QRect specifying the contents of the QImage.

    Edges of the image are trimmed if they have the same color.

    """
    # pick the color at most of the corners
    colors = collections.defaultdict(int)
    w, h = image.width(), image.height()
    for x, y in (0, 0), (w - 1, 0), (w - 1, h - 1), (0, h - 1):
        colors[image.pixel(x, y)] += 1
    most = max(colors, key=colors.get)
    # let Qt do the masking work
    mask = image.createMaskFromColor(most)
    return QRegion(QBitmap.fromImage(mask)).boundingRect()


def tempdir() -> str:
    """Return a temporary directory that is erased on app quit."""
    import tempfile
    global _tempdir
    try:
        _tempdir
    except NameError:
        name = QApplication.applicationName().translate({ord('/'): None}) or 'qpageview'
        _tempdir = tempfile.mkdtemp(prefix=name + '-')
        import atexit
        import shutil
        @atexit.register
        def remove():
            shutil.rmtree(_tempdir, ignore_errors=True)
    return tempfile.mkdtemp(dir=_tempdir)
