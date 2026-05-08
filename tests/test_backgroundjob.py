import time
from typing import Any

import pytest

import qpageview.backgroundjob as bj  # lol


@pytest.fixture(autouse=True)
def _reset_globals():
    old_running = set(bj._runningJobs)
    old_pending = list(bj._pendingJobs)
    old_max = bj.maxjobs

    bj._runningJobs.clear()
    bj._pendingJobs.clear()
    bj.maxjobs = 1

    yield

    bj._runningJobs.clear()
    bj._runningJobs.update(old_running)
    bj._pendingJobs.clear()
    bj._pendingJobs.extend(old_pending)
    bj.maxjobs = old_max

def test_job_runs_and_finalize(qtbot):
    j = bj.Job()
    res = {}

    j.work = lambda: 42
    j.finalize = lambda result: res.setdefault('result', result)

    j.start()

    qtbot.waitUntil(lambda: j.done, timeout=2000)

    assert j.running is False
    assert j.done is True
    assert j.result == 42
    assert res['result'] == 42

def test_job_finalize_called_on_main_thread(qtbot, qapp):
    j = bj.Job()
    main_thread = qapp.thread()
    res = {}

    j.work = lambda: 42

    def finalize(result):
        res['result'] = result
        res['thread'] = (j.thread() == main_thread)

    j.finalize = finalize
    j.start()

    qtbot.waitUntil(lambda: j.done, timeout=2000)

    assert res['result'] == 42
    assert res['thread'] is True

def test_job_queueing(qtbot):
    bj.maxjobs = 1
    res = []

    class _MockJob(bj.Job):
        def __init__(self, name, delay):
            super().__init__()
            self.name = name
            self.delay = delay

        def work(self) -> Any:
            time.sleep(self.delay)
            return self.name

    def make_job(name, delay):
        j = _MockJob(name, delay)
        j.finalize = lambda result: res.append(result)
        return j

    j1 = make_job('first', 0.1)
    j2 = make_job('second', 0.01)

    j1.start()
    j2.start()

    # Second job should be pending until the first one finishes
    assert j1 in bj._runningJobs and j1.running is True
    assert j2 in bj._pendingJobs and j2.running is True  # pending jobs are still marked running by start()
    assert len(bj._runningJobs) == 1

    qtbot.waitUntil(lambda: j1.done and j2.done, timeout=3000)

    # Jobs should run in order and both should be done
    assert res == ['first', 'second']
    assert j1.done is True and j2.done is True

def test_singlerun_cancel(qtbot):
    sr = bj.SingleRun()
    res = {"called": False}

    sr(lambda: time.sleep(0.05) or 1, callback=lambda _: res.__setitem__("called", not res["called"]))
    sr.cancel()

    qtbot.wait(120)
    assert res["called"] is False

def test_singlerun_overwrite_callback(qtbot):
    sr = bj.SingleRun()
    res = []

    sr(lambda: time.sleep(0.06) or "old", callback=lambda r: res.append(r))
    sr(lambda: "new", callback=lambda r: res.append(r))

    qtbot.waitUntil(lambda: "new" in res, timeout=2000)
    qtbot.wait(120)  # Wait a bit more to ensure the old callback would have been called if not canceled

    assert res == ["new"]

def test_run_executes_and_calls_callback(qtbot):
    res = {}
    bj.run(lambda: 123, callback=lambda r: res.setdefault('result', r))

    qtbot.waitUntil(lambda: 'result' in res, timeout=2000)
    assert res['result'] == 123
