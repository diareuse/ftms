from functools import wraps

from pyftms import ResultCode
from pyftms.models import ControlCode, StopPauseCode

from .stream import VENDOR_SERVICE, WRITE_CHAR

CHECKSUM_KEY = 0x5A
SYS_CONTROL = 0x53
CONTROL_START = 0x01
CONTROL_SPEED = 0x02
CONTROL_STOP = 0x03
CONTROL_PAUSE = 0x06
NO_INCLINE = 0


def vendor_frame(payload: list[int]) -> bytes:
    return bytes([0x02, *payload, (sum(payload) & 0xFF) ^ CHECKSUM_KEY, 0x03])


def _vendor_payload(code, kwargs) -> list[int] | None:
    if code == ControlCode.START_RESUME:
        return [SYS_CONTROL, CONTROL_START, *[0] * 8]

    if (speed := kwargs.get("target_speed")) is not None:
        return [SYS_CONTROL, CONTROL_SPEED, round(speed * 10), NO_INCLINE]

    if (stop_pause := kwargs.get("stop_pause")) == StopPauseCode.STOP:
        return [SYS_CONTROL, CONTROL_STOP]

    if stop_pause == StopPauseCode.PAUSE:
        return [SYS_CONTROL, CONTROL_PAUSE]

    return None


def route_control_to_vendor(machine) -> None:
    original = machine._write_command

    if getattr(original, "routes_to_vendor", False):
        return

    @wraps(original)
    async def write_command(code=None, **kwargs):
        await machine._connect()
        cli = getattr(machine, "_cli", None)

        if cli is None or not any(s.uuid == VENDOR_SERVICE for s in cli.services):
            return await original(code, **kwargs)

        if code == ControlCode.REQUEST_CONTROL:
            return ResultCode.SUCCESS

        if (payload := _vendor_payload(code, kwargs)) is None:
            return await original(code, **kwargs)

        await cli.write_gatt_char(WRITE_CHAR, vendor_frame(payload), response=False)
        return ResultCode.SUCCESS

    write_command.routes_to_vendor = True
    machine._write_command = write_command
