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
Run jobs in the background using QThread.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Set, List, Optional, Any, Callable

from PySide6.QtCore import QThread, QObject

if TYPE_CHECKING:
    from .page import AbstractPage

# as soon as a Job start()s, it is saved here, to prevent it being
# destroyed while running
_runningJobs: Set["Job"] = set()
_pendingJobs: List["Job"] = []
maxjobs: int = 12

class Job(QThread):
    """A simple wrapper around QThread.

    Before calling start() you should put the work function in the work
    attribute, and an optional finalize function (which will be called with the
    result) in the finalize attribute.

    Or alternatively, inherit from this class and implement work() and finish()
    yourself. The result of the work function is stored in the result attribute.

    """
    callbacks: Set[Optional[Callable[[AbstractPage], None]]]
    mutex: Any

    finalize: Optional[Callable[[Any], None]] = None
    running: bool = False
    done: bool = False
    result: Optional[Any] = None

    def __init__(self, parent: Optional[QObject] = None):
        """Init ourselves; the parent can be a QObject which will be our parent."""
        super().__init__(parent)
        self.finished.connect(self._slotFinished)

    def start(self, **kwargs: Any) -> None:
        self.result = None
        self.running = True     # this is more robust than isRunning()
        self.done = False
        if len(_runningJobs) < maxjobs:
            _runningJobs.add(self)
            super().start()
        else:
            _pendingJobs.append(self)

    def run(self) -> None:
        """Call the work function in the background thread."""
        self.result = self.work()

    def work(self) -> Any:
        """Implement this to get the work done.

        If you have long tasks you can use Qt's isInterruptionRequested()
        functionality.

        Instead of implementing this method, you can put the work function in
        the work instance attribute.

        """
        pass

    def finish(self) -> None:
        """This slot is called in the main thread when the work is done.

        The default implementation calls the finalize function with the result.

        """
        if self.finalize:
            self.finalize(self.result)

    def _slotFinished(self) -> None:
        _runningJobs.discard(self)
        if _pendingJobs:
            _pendingJobs.pop().start()
        self.running = False
        self.done = True
        self.finish()


class SingleRun:
    """Run a function in a background thread.

    The outcome is silently discarded if another function is called before the
    old one finishes.

    """
    def __init__(self):
        self._job: Optional[Job] = None

    def cancel(self) -> None:
        """Forgets the running job.

        The job is not terminated but the callback is not called.

        """
        j = self._job
        if j:
            j.finalize = None
            self._job = None

    def __call__(
        self,
        func: Callable[[], Any],
        callback: Optional[Callable[[Any], None]] = None
    ) -> None:
        self.cancel()
        j = self._job = Job()
        j.work = func
        def finalize(result):
            self.cancel()
            if callback:
                callback(result)
        j.finalize = finalize
        j.start()


def run(
    func: Callable[[], Any],
    callback: Optional[Callable[[Any], None]] = None
) -> None:
    """Run specified function in a background thread.

    The thread is immediately started. If a callback is specified, it is called
    in the main thread with the result when the function is ready.

    """
    j = Job()
    j.work = func
    j.finalize = callback
    j.start()
