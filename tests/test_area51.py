"""Area-51 encoders must match the bytes the owner's verified tool sends."""
import sys
from pathlib import Path

import pytest

from awcfree_lib.protocol import area51, v4, v5


def test_chassis_group_matches_alienrgb():
    ref = Path(__file__).parents[2] / "Alienware"
    if not (ref / "alienrgb.py").exists():
        pytest.skip("reference tool not present")
    sys.path.insert(0, str(ref))
    import alienrgb
    for lights in (list(range(28)), list(range(28, 41)), [27]):
        want = [r[1:] for r in alienrgb.group_action_reports(lights, (1, 2, 3))]
        assert area51.chassis_group(lights, (1, 2, 3)) == want


def test_chassis_covers_every_light_in_valid_groups():
    groups = area51.chassis_all((0, 255, 0))
    assert len(groups) == 2
    assert all(len(g) == 5 for g in groups)
    assert area51.CHASSIS_LIGHTS == tuple(range(41))


def test_group_limits():
    with pytest.raises(ValueError):
        area51.chassis_group(list(range(29)), (0, 0, 0))
    with pytest.raises(ValueError):
        area51.chassis_group([1, 1], (0, 0, 0))


def test_keyboard_static_bytes_and_never_off():
    pk = area51.keyboard_static((255, 0, 0))
    assert [p[:2] for p in pk] == [b"\xcc\x94", b"\xcc\x83", b"\xcc\x80", b"\xcc\x8b"]
    assert pk[1][2:5] == bytes([0x38, 0x9C, 100])
    assert pk[2][10:16] == bytes([255, 0, 0, 255, 0, 0])
    assert all(len(p) == v5.LEN for p in pk)
    with pytest.raises(ValueError):
        area51.keyboard_static((0, 0, 0), brightness=0)
