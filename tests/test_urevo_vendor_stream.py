import asyncio
from types import SimpleNamespace

from urevo import attach_vendor_stream, reading_to_update_event

VENDOR_SERVICE = "0000fff0-0000-1000-8000-00805f9b34fb"
NOTIFY_CHAR = "0000fff1-0000-1000-8000-00805f9b34fb"
WRITE_CHAR = "0000fff2-0000-1000-8000-00805f9b34fb"

FRAME_SLOW = "0251030a003a023e004e01b20300000000d103"
FRAME_FAST = "0251032d00d8001b008a008b0100000000 6303".replace(" ", "")


class FakeBleakClient:
    def __init__(self, service_uuids):
        self.services = [SimpleNamespace(uuid=u) for u in service_uuids]
        self.handlers = {}
        self.writes = []

    async def start_notify(self, uuid, handler):
        self.handlers[uuid] = handler

    async def write_gatt_char(self, uuid, data, response=None):
        self.writes.append((uuid, bytes(data)))

    def deliver(self, uuid, hex_frame):
        self.handlers[uuid](None, bytearray.fromhex(hex_frame))


def attach(client):
    readings = []
    attached = asyncio.run(attach_vendor_stream(client, readings.append))
    return attached, readings


def test_streamed_frame_is_reported_as_treadmill_reading():
    client = FakeBleakClient([VENDOR_SERVICE])
    attached, readings = attach(client)

    client.deliver(NOTIFY_CHAR, FRAME_SLOW)

    assert attached is True
    assert len(readings) == 1
    reading = readings[0]
    assert reading.speed_kmh == 1.0
    assert reading.elapsed_s == 570
    assert reading.distance_m == 620
    assert reading.energy_kcal == 33.4
    assert reading.steps == 946


def test_faster_frame_is_decoded_with_its_own_values():
    client = FakeBleakClient([VENDOR_SERVICE])
    _, readings = attach(client)

    client.deliver(NOTIFY_CHAR, FRAME_FAST)

    reading = readings[0]
    assert reading.speed_kmh == 4.5
    assert reading.elapsed_s == 216
    assert reading.distance_m == 270
    assert reading.energy_kcal == 13.8
    assert reading.steps == 395


def test_attaching_asks_the_treadmill_to_start_streaming():
    client = FakeBleakClient([VENDOR_SERVICE])

    attach(client)

    assert client.writes == [(WRITE_CHAR, bytes.fromhex("02510b03"))]


def test_machine_without_vendor_service_is_left_alone():
    client = FakeBleakClient(["00001826-0000-1000-8000-00805f9b34fb"])

    attached, readings = attach(client)

    assert attached is False
    assert client.writes == []
    assert client.handlers == {}
    assert readings == []


def test_frames_that_are_not_treadmill_data_are_ignored():
    client = FakeBleakClient([VENDOR_SERVICE])
    _, readings = attach(client)

    client.deliver(NOTIFY_CHAR, "00")
    client.deliver(NOTIFY_CHAR, "0251020a003a023e004e01b20300000000d103")
    client.deliver(NOTIFY_CHAR, FRAME_SLOW[:-2])

    assert readings == []


def test_streamed_reading_becomes_a_sensor_update_event():
    client = FakeBleakClient([VENDOR_SERVICE])
    _, readings = attach(client)
    client.deliver(NOTIFY_CHAR, FRAME_SLOW)

    event = reading_to_update_event(readings[0])

    assert event.event_id == "update"
    assert event.event_data == {
        "speed_instant": 1.0,
        "time_elapsed": 570,
        "distance_total": 620,
        "energy_total": 33.4,
        "step_count": 946,
    }


def test_connection_requests_vendor_service_in_addition_to_requested_ones():
    from urevo import widen_service_filter

    seen = []

    async def establish_connection(*args, services=None, **kwargs):
        seen.append(list(services))

    module = SimpleNamespace(establish_connection=establish_connection)

    widen_service_filter(module)
    asyncio.run(module.establish_connection(services=["ftms", "dis"]))

    assert seen == [["ftms", "dis", VENDOR_SERVICE]]


def test_widening_the_service_filter_twice_adds_vendor_service_once():
    from urevo import widen_service_filter

    seen = []

    async def establish_connection(*args, services=None, **kwargs):
        seen.append(list(services))

    module = SimpleNamespace(establish_connection=establish_connection)

    widen_service_filter(module)
    widen_service_filter(module)
    asyncio.run(module.establish_connection(services=["ftms"]))

    assert seen == [["ftms", VENDOR_SERVICE]]
