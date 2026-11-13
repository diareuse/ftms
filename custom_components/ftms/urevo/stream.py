from collections.abc import Callable

from .reading import TreadmillReading, decode_reading

VENDOR_SERVICE = "0000fff0-0000-1000-8000-00805f9b34fb"
NOTIFY_CHAR = "0000fff1-0000-1000-8000-00805f9b34fb"
WRITE_CHAR = "0000fff2-0000-1000-8000-00805f9b34fb"
START_STREAMING = bytes.fromhex("02510b03")

ReadingSink = Callable[[TreadmillReading], None]


async def attach_vendor_stream(client, sink: ReadingSink) -> bool:
    if not any(s.uuid == VENDOR_SERVICE for s in client.services):
        return False

    def on_notify(_, data: bytearray) -> None:
        if (reading := decode_reading(bytes(data))) is not None:
            sink(reading)

    await client.start_notify(NOTIFY_CHAR, on_notify)
    await client.write_gatt_char(WRITE_CHAR, START_STREAMING, response=False)

    return True
