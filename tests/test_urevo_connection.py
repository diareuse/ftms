import asyncio
from types import SimpleNamespace

from bleak.exc import BleakError
from urevo import attach_stream_on_connect

VENDOR_SERVICE = "0000fff0-0000-1000-8000-00805f9b34fb"
WRITE_CHAR = "0000fff2-0000-1000-8000-00805f9b34fb"
NOTIFY_CHAR = "0000fff1-0000-1000-8000-00805f9b34fb"
FRAME = "0251030a003a023e004e01b20300000000d103"


class FakeBleakClient:
    def __init__(self, fail=None):
        self.services = [SimpleNamespace(uuid=VENDOR_SERVICE)]
        self.handlers = {}
        self.writes = []
        self.fail = fail

    async def start_notify(self, uuid, handler):
        if self.fail:
            raise self.fail
        self.handlers[uuid] = handler

    async def write_gatt_char(self, uuid, data, response=None):
        self.writes.append((uuid, bytes(data)))


class FakeFitnessMachine:
    def __init__(self, *clients):
        self.clients = list(clients)
        self.connected = False

    @property
    def is_connected(self):
        return self.connected

    async def _connect(self):
        if self.connected:
            return
        self._cli = self.clients.pop(0)
        self.connected = True

    async def send_command(self):
        await self._connect()

    def drop_connection(self):
        self.connected = False
        del self._cli


def connect(machine):
    asyncio.run(machine._connect())


def test_stream_starts_whenever_the_machine_connects():
    client = FakeBleakClient()
    machine = FakeFitnessMachine(client)
    readings = []
    attach_stream_on_connect(machine, readings.append)

    connect(machine)
    client.handlers[NOTIFY_CHAR](None, bytearray.fromhex(FRAME))

    assert client.writes == [(WRITE_CHAR, bytes.fromhex("02510b03"))]
    assert [r.steps for r in readings] == [946]


def test_stream_restarts_after_the_machine_reconnects():
    first, second = FakeBleakClient(), FakeBleakClient()
    machine = FakeFitnessMachine(first, second)
    attach_stream_on_connect(machine, lambda reading: None)

    connect(machine)
    machine.drop_connection()
    connect(machine)

    assert len(first.writes) == 1
    assert len(second.writes) == 1


def test_connecting_while_already_connected_does_not_start_a_second_stream():
    client = FakeBleakClient()
    machine = FakeFitnessMachine(client)
    attach_stream_on_connect(machine, lambda reading: None)

    connect(machine)
    connect(machine)

    assert len(client.writes) == 1


def test_connection_succeeds_even_when_the_stream_cannot_start():
    client = FakeBleakClient(fail=BleakError("no notify"))
    machine = FakeFitnessMachine(client)
    attach_stream_on_connect(machine, lambda reading: None)

    connect(machine)

    assert machine.is_connected is True


def test_stream_starts_when_a_command_reconnects_the_machine_lazily():
    client = FakeBleakClient()
    machine = FakeFitnessMachine(client)
    attach_stream_on_connect(machine, lambda reading: None)

    asyncio.run(machine.send_command())

    assert len(client.writes) == 1
