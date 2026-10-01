"""Alienware 16 Area-51 lighting: whole-keyboard colour plus the chassis lights."""
from __future__ import annotations

from pathlib import Path

from ..errors import DeviceNotFound, ProtocolError
from ..protocol import area51, v4, v5
from ..transport import HidrawDevice, find_hidraw

KEYBOARD_VID, KEYBOARD_PID = 0x0D62, 0x1BBC
CHASSIS_VID, CHASSIS_PID = 0x187C, 0x0551

Rgb = tuple[int, int, int]


def check_model() -> None:
    """Refuse hardware writes on anything but the laptop this was mapped on."""
    try:
        model = Path("/sys/class/dmi/id/product_name").read_text().strip()
    except OSError as exc:
        raise ProtocolError(f"cannot read the laptop model: {exc}") from exc
    if model != area51.MODEL:
        raise ProtocolError(f"Area-51 lighting is only enabled on {area51.MODEL}, not {model!r}")


class Area51:
    """Keyboard (`0d62:1bbc`) and chassis (`187c:0551`) of the AA16250."""

    def __init__(self, keyboard: HidrawDevice | None = None,
                 chassis: HidrawDevice | None = None) -> None:
        if keyboard is None:
            path = find_hidraw(KEYBOARD_VID, KEYBOARD_PID, descriptor_contains=b"\x85\xcc")
            if path is None:
                raise DeviceNotFound("no hidraw node for the keyboard 0d62:1bbc")
            keyboard = HidrawDevice(path, v5.LEN, label="keyboard")
        if chassis is None:
            path = find_hidraw(CHASSIS_VID, CHASSIS_PID)
            if path is None:
                raise DeviceNotFound("no hidraw node for the chassis 187c:0551")
            chassis = HidrawDevice(path, v4.LEN, label="chassis")
        self.keyboard, self.chassis = keyboard, chassis

    def set_chassis(self, rgb: Rgb, lights=area51.CHASSIS_LIGHTS) -> int:
        sent = 0
        self.chassis.open()
        try:
            for group in area51.chassis_all(rgb, tuple(lights)):
                for pkt in group:
                    self.chassis.send_output(pkt)
                    sent += 1
        finally:
            self.chassis.close()
        return sent

    def set_keyboard(self, rgb: Rgb) -> int:
        packets = area51.keyboard_static(rgb)
        self.keyboard.open()
        try:
            for pkt in packets:
                self.keyboard.send_feature(pkt)
        finally:
            self.keyboard.close()
        return len(packets)

    def set_all(self, rgb: Rgb) -> int:
        """Chassis first, then keyboard.  Stops at the first failure."""
        return self.set_chassis(rgb) + self.set_keyboard(rgb)
