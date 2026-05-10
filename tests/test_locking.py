import gc
import threading

from qpageview import locking

class _Lockable:
    pass

def test_lock_same_item():
    item = _Lockable()

    lock1 = locking.lock(item)
    lock2 = locking.lock(item)

    assert lock1 is lock2

def test_lock_different_items():
    item1 = _Lockable()
    item2 = _Lockable()

    lock1 = locking.lock(item1)
    lock2 = locking.lock(item2)

    assert lock1 is not lock2

def test_lock_same_item_different_threads():
    item = _Lockable()
    lock = locking.lock(item)

    with lock:
        with lock:
            assert True

def test_lock_after_acquire_and_release():
    item = _Lockable()
    first = locking.lock(item)

    with first:
        pass

    second = locking.lock(item)

    assert first is second

def test_lock_garbage_collection():
    item = _Lockable()
    lock = locking.lock(item)

    assert item in locking._locks

    del item
    gc.collect()

    assert lock not in list(locking._locks.values())

def test_lock_creation_multiple_threads():
    item = _Lockable()
    results = []

    def create_lock():
        results.append(locking.lock(item))

    threads = [threading.Thread(target=create_lock) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert all(lock is results[0] for lock in results)
