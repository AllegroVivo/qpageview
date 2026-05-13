from dataclasses import dataclass

import pytest

from qpageview.rectangles import Rectangles, Left, Top, Right, Bottom

@dataclass(frozen=True)
class _RectObj:
    id: str
    coords: tuple[float, float, float, float]

class _Rectangles(Rectangles):
    def get_coords(self, obj):
        return obj.coords

@pytest.fixture(scope="function")
def sample_rects():
    return [
        _RectObj("a", (0.0, 0.0, 10.0, 10.0)),
        _RectObj("b", (5.0, 5.0, 15.0, 15.0)),
        _RectObj("c", (20.0, 20.0, 30.0, 30.0)),
        _RectObj("d", (12.0, 0.0, 18.0, 6.0)),
    ]


def test_rectangles_constructor_bulk_add(sample_rects):
    rects = _Rectangles(sample_rects)

    assert len(rects) == 4
    assert sample_rects[0] in rects
    assert sample_rects[3] in rects

def test_rectangles_bool_always_true():
    rects = _Rectangles()

    assert bool(rects) is True
    assert len(rects) == 0

def test_rectangles_ignore_duplicates(sample_rects):
    rects = _Rectangles()
    rects.add(sample_rects[0])
    rects.add(sample_rects[0])

    assert len(rects) == 1

def test_rectangles_bulk_add_replaces_search_index(sample_rects):
    rects = _Rectangles(sample_rects[:2])
    _ = rects.at(1, 1)

    rects.bulk_add(sample_rects[2:])

    assert len(rects) == 4
    hit_ids = {obj.id for obj in rects.at(25, 25)}
    assert hit_ids == {"c"}

def test_rectangles_remove(sample_rects):
    rects = _Rectangles(sample_rects)
    rects.remove(sample_rects[1])

    assert len(rects) == 3
    assert sample_rects[1] not in rects
    hit_ids = {obj.id for obj in rects.at(7, 7)}
    assert hit_ids == {"a"}

def test_rectangles_clear(sample_rects):
    rects = _Rectangles(sample_rects)
    _ = rects.at(1, 1)

    rects.clear()

    assert len(rects) == 0
    assert list(rects) == []
    assert rects.at(1, 1) == set()

def test_rectangles_at(sample_rects):
    rects = _Rectangles(sample_rects)
    hit_ids = {obj.id for obj in rects.at(6, 6)}

    assert hit_ids == {"a", "b"}

def test_rectangles_at_boundary_points(sample_rects):
    rects = _Rectangles(sample_rects)
    hit_ids = {obj.id for obj in rects.at(10, 10)}

    assert hit_ids == {"a", "b"}

def test_rectangles_inside(sample_rects):
    rects = _Rectangles(sample_rects)
    hit_ids = {obj.id for obj in rects.inside(0, 0, 16, 16)}

    assert hit_ids == {"a", "b"}

def test_rectangles_intersecting(sample_rects):
    rects = _Rectangles(sample_rects)
    hit_ids = {obj.id for obj in rects.intersecting(9, 9, 21 , 21)}

    assert hit_ids == {"a", "b", "c"}

def test_rectangles_width_and_height(sample_rects):
    rects = _Rectangles(sample_rects)

    assert rects.width(sample_rects[0]) == pytest.approx(10.0)
    assert rects.height(sample_rects[0]) == pytest.approx(10.0)
    assert rects.width(sample_rects[3]) == pytest.approx(6.0)
    assert rects.height(sample_rects[3]) == pytest.approx(6.0)

def test_rectangles_closest(sample_rects):
    rects = _Rectangles(sample_rects)

    closest_right = rects.closest(sample_rects[0], Right)
    closest_bottom = rects.closest(sample_rects[0], Bottom)
    closest_left = rects.closest(sample_rects[2], Left)

    assert closest_right in {sample_rects[1], sample_rects[3]}
    assert closest_bottom in {sample_rects[1]}
    assert closest_left in {sample_rects[1], sample_rects[3]}

def test_rectangles_nearest_empty():
    rects = _Rectangles()

    assert rects.nearest(16, 8) is None

def test_rectangles_nearest(sample_rects):
    rects = _Rectangles(sample_rects)

    nearest = rects.nearest(16, 8)

    assert nearest in {sample_rects[1], sample_rects[3]}

def test_rectangles_iter(sample_rects):
    rects = _Rectangles(sample_rects)

    iterated_ids = {obj.id for obj in rects}

    assert iterated_ids == {"a", "b", "c", "d"}
