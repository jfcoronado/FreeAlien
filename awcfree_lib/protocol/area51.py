"""Encoders for the Alienware 16 Area-51 (AA16250), as worked out on that laptop.

Two controllers, neither addressed the way the m16 R2's are:

  * Chassis AW-ELC (187c:0551): the same v4 transport as `protocol.v4`, but the
    lights are numeric ids 0-40 selected as one group with `03 23` and coloured by
    a single static action, not the m16's three named zones.  Ids, from the
    owner's visual mapping (alienware-lights `lighting-map.json`):

        0-26   rear light bar            27  power button      28  lid logo
        29/30  right / left fan          31-40  touchpad edge

  * Keyboard (0d62:1bbc): whole-keyboard colour only.  A v5 global static effect
    (`cc 80 01 ...`) sent as 64-byte feature reports; per-key records are not
    known to work on this controller, so none are encoded here.

Volatile only: nothing here saves to firmware.  Provenance is in CREDITS.md.
"""
from __future__ import annotations

from collections.abc import Sequence

from . import v4, v5

MODEL = "Alienware 16 Area-51 AA16250"

#: Chassis ids by role.
BAR = tuple(range(0, 27))
POWER = (27,)
LOGO = (28,)
FANS = (29, 30)
TOUCHPAD = tuple(range(31, 41))
CHASSIS_LIGHTS = BAR + POWER + LOGO + FANS + TOUCHPAD

#: The controller accepts at most this many ids per `03 23` selection.
MAX_GROUP = 28

Rgb = tuple[int, int, int]


def _check(rgb: Rgb) -> None:
    if len(rgb) != 3 or any(not 0 <= c <= 255 for c in rgb):
        raise ValueError("RGB channels must be between 0 and 255")


def chassis_group(lights: Sequence[int], rgb: Rgb) -> list[bytes]:
    """Colour 1-28 distinct light ids statically, without saving."""
    if not 1 <= len(lights) <= MAX_GROUP or len(set(lights)) != len(lights):
        raise ValueError(f"choose 1 to {MAX_GROUP} distinct light ids")
    if any(not 0 <= n <= 255 for n in lights):
        raise ValueError("light ids must be between 0 and 255")
    _check(rgb)
    n = len(lights)
    return [
        v4._pad([v4.PREAMBLE, 0x26, 0, 0, n, *lights]),      # undim
        v4._pad([v4.PREAMBLE, 0x21, 0, 1, 0, 0]),            # open animation 0
        v4._pad([v4.PREAMBLE, 0x23, 1, 0, n, *lights]),      # select group
        v4._pad([v4.PREAMBLE, 0x24, 0, 0, 1, 0, 2, *rgb]),   # static colour
        v4._pad([v4.PREAMBLE, 0x21, 0, 3, 0, 0]),            # play, no save
    ]


def chassis_all(rgb: Rgb, lights: Sequence[int] = CHASSIS_LIGHTS) -> list[list[bytes]]:
    """Every chassis light, split into groups the controller accepts."""
    return [chassis_group(lights[i:i + MAX_GROUP], rgb)
            for i in range(0, len(lights), MAX_GROUP)]


def keyboard_static(rgb: Rgb, brightness: int = 100) -> list[bytes]:
    """Whole-keyboard static colour.

    `cc 83 38 9c <b>` is the master enable that `v5.turn_on` warns about: its last
    byte is brightness here, and zero means off.  It is sent with a non-zero
    value only, as on the laptop this was verified on.
    """
    _check(rgb)
    if not 1 <= brightness <= 100:
        raise ValueError("brightness must be between 1 and 100")
    pad = v5._pad
    return [
        pad([v5.REPORT_ID, 0x94]),
        pad([v5.REPORT_ID, 0x83, 0x38, 0x9C, brightness]),
        pad([v5.REPORT_ID, 0x80, 1, 7, 0, 0, 1, 1, 1, 0, *rgb, *rgb]),
        pad([v5.REPORT_ID, 0x8B, 1, 0xFF]),
    ]
