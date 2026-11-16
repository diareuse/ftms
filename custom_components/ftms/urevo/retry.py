import logging
from functools import wraps

_LOGGER = logging.getLogger(__name__)


def retry_unanswered_commands(machine) -> None:
    original = machine._write_command

    if getattr(original, "retries_unanswered", False):
        return

    @wraps(original)
    async def write_command(*args, **kwargs):
        try:
            return await original(*args, **kwargs)
        except TimeoutError:
            _LOGGER.debug("Command was not answered, sending it again")
            return await original(*args, **kwargs)

    write_command.retries_unanswered = True
    machine._write_command = write_command
