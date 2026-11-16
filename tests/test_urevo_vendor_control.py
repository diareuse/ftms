import asyncio
from types import SimpleNamespace

from pyftms import ResultCode
from pyftms.models import ControlCode, StopPauseCode
from urevo import route_control_to_vendor

VENDOR_SERVICE = "0000fff0-0000-1000-8000-00805f9b34fb"
WRITE_CHAR = "0000fff2-0000-1000-8000-00805f9b34fb"


class FakeBleakClient:
    def __init__(self, service_uuids):
        self.services = [SimpleNamespace(uuid=u) for u in service_uuids]
        self.writes = []

    async def write_gatt_char(self, uuid, data, response=None):
        self.writes.append((uuid, bytes(data).hex(), response))


class FakeFitnessMachine:
    def __init__(self, client):
        self._cli = client
        self.delegated = []

    async def _connect(self):
        return None

    async def _write_command(self, code=None, **kwargs):
        self.delegated.append((code, kwargs))
        return "delegated"


def routed(service_uuids=(VENDOR_SERVICE,)):
    client = FakeBleakClient(service_uuids)
    machine = FakeFitnessMachine(client)
    route_control_to_vendor(machine)
    return machine, client


def write(machine, code=None, **kwargs):
    return asyncio.run(machine._write_command(code, **kwargs))


def test_speed_setting_is_sent_as_vendor_speed_frame():
    machine, client = routed()

    result = write(machine, target_speed=4.5)

    assert result == ResultCode.SUCCESS
    assert client.writes == [(WRITE_CHAR, "0253022d00d803", False)]
    assert machine.delegated == []


def test_speed_is_rounded_to_tenths_of_a_kilometre_per_hour():
    machine, client = routed()

    write(machine, target_speed=0.1 * 30)

    assert client.writes == [(WRITE_CHAR, "0253021e002903", False)]


def test_start_is_sent_as_vendor_start_frame():
    machine, client = routed()

    result = write(machine, ControlCode.START_RESUME)

    assert result == ResultCode.SUCCESS
    assert client.writes == [(WRITE_CHAR, "02530100000000000000000e03", False)]


def test_stop_is_sent_as_vendor_stop_frame():
    machine, client = routed()

    write(machine, stop_pause=StopPauseCode.STOP)

    assert client.writes == [(WRITE_CHAR, "0253030c03", False)]


def test_pause_is_sent_as_vendor_pause_frame():
    machine, client = routed()

    write(machine, stop_pause=StopPauseCode.PAUSE)

    assert client.writes == [(WRITE_CHAR, "0253060303", False)]


def test_request_control_needs_no_vendor_frame():
    machine, client = routed()

    result = write(machine, ControlCode.REQUEST_CONTROL)

    assert result == ResultCode.SUCCESS
    assert client.writes == []


def test_commands_without_a_vendor_equivalent_go_to_the_machine():
    machine, client = routed()

    result = write(machine, target_inclination=2)

    assert result == "delegated"
    assert client.writes == []


def test_machine_without_vendor_service_keeps_standard_control():
    machine, client = routed(["00001826-0000-1000-8000-00805f9b34fb"])

    result = write(machine, target_speed=4.5)

    assert result == "delegated"
    assert client.writes == []


def test_routing_twice_still_writes_one_frame():
    machine, client = routed()
    route_control_to_vendor(machine)

    write(machine, target_speed=4.5)

    assert len(client.writes) == 1
