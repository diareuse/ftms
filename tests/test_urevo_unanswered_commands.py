import asyncio

import pytest
from urevo import retry_unanswered_commands


class FakeFitnessMachine:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    async def _write_command(self, code=None, **kwargs):
        self.calls.append(code)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def write(machine, code):
    return asyncio.run(machine._write_command(code))


def test_command_that_times_out_once_succeeds_on_the_second_attempt():
    machine = FakeFitnessMachine([TimeoutError(), "success"])
    retry_unanswered_commands(machine)

    result = write(machine, "start")

    assert result == "success"
    assert machine.calls == ["start", "start"]


def test_answered_command_is_sent_only_once():
    machine = FakeFitnessMachine(["success"])
    retry_unanswered_commands(machine)

    result = write(machine, "start")

    assert result == "success"
    assert machine.calls == ["start"]


def test_command_that_never_gets_an_answer_still_times_out():
    machine = FakeFitnessMachine([TimeoutError(), TimeoutError()])
    retry_unanswered_commands(machine)

    with pytest.raises(TimeoutError):
        write(machine, "set_speed")

    assert machine.calls == ["set_speed", "set_speed"]


def test_errors_other_than_timeouts_are_not_retried():
    machine = FakeFitnessMachine([ValueError("boom"), "success"])
    retry_unanswered_commands(machine)

    with pytest.raises(ValueError):
        write(machine, "start")

    assert machine.calls == ["start"]


def test_wrapping_twice_does_not_multiply_attempts():
    machine = FakeFitnessMachine([TimeoutError(), TimeoutError(), TimeoutError()])
    retry_unanswered_commands(machine)
    retry_unanswered_commands(machine)

    with pytest.raises(TimeoutError):
        write(machine, "start")

    assert machine.calls == ["start", "start"]
