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


def test_effect_off_resets_static_first_on_area51_only():
    from unittest.mock import Mock
    from awcfree_lib.devices.keyboard import Keyboard
    for is_area51, first in ((True, b"\xcc\x94"), (False, b"\xcc\x94")):
        kb = Keyboard("/dev/fake")
        kb.dev = Mock()
        kb._area51 = is_area51
        kb.effect_off()
        sent = [c.args[0] for c in kb.dev.send_feature.call_args_list]
        assert sent[-1] == v5.EFFECT_OFF
        assert (any(p[:2] == b"\xcc\x80" and p[2] == 1 and p[3] == 7 for p in sent)) == is_area51


def test_chassis_zones_translate_to_area51_lights():
    from unittest.mock import Mock
    from awcfree_lib.devices.chassis import Chassis
    ch = Chassis("/dev/fake")
    ch.dev = Mock()
    ch.area51 = True
    assert ch._lights(v4.ZONE_TOUCHPAD) == tuple(range(31, 41))
    assert ch._lights(v4.ZONE_LOGO) == (28,)
    assert ch._lights(v4.ZONE_POWER) == (27,)
    ch.set_touchpad((0, 255, 0))
    sent = [c.args[0] for c in ch.dev.send_output.call_args_list]
    assert sent == area51.chassis_group(tuple(range(31, 41)), (0, 255, 0))
    ch.dev.reset_mock()
    ch.set_logo((0, 0, 255), persist=True)  # persist is ignored on this laptop
    assert [c.args[0][:2] for c in ch.dev.send_output.call_args_list][3] == b"\x03\x24"
    ch.dev.reset_mock()
    ch.area51 = False
    assert ch._lights(v4.ZONE_LOGO) == (v4.ZONE_LOGO,)


def test_bar_and_fan_zones_map_to_their_lights():
    from unittest.mock import Mock
    from awcfree_lib.devices.chassis import Chassis
    ch = Chassis("/dev/fake")
    ch.dev = Mock()
    ch.area51 = True
    assert ch._lights(area51.ZONE_BAR) == tuple(range(27))
    assert ch._lights(area51.ZONE_FANS) == (29, 30)
    assert area51.ZONE_BAR not in (v4.ZONE_TOUCHPAD, v4.ZONE_LOGO, v4.ZONE_POWER)
