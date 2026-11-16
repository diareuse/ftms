import logging
from functools import wraps

from bleak.exc import BleakError

from .stream import ReadingSink, attach_vendor_stream

_LOGGER = logging.getLogger(__name__)


def attach_stream_on_connect(machine, sink: ReadingSink) -> None:
    original = machine._connect
    streamed = []

    @wraps(original)
    async def connect() -> None:
        await original()

        cli = getattr(machine, "_cli", None)

        if not machine.is_connected or cli is None or cli in streamed:
            return

        streamed[:] = [cli]

        try:
            await attach_vendor_stream(cli, sink)
        except (BleakError, TimeoutError):
            _LOGGER.exception("Vendor data stream could not be started")

    machine._connect = connect
