from functools import wraps

from .stream import VENDOR_SERVICE


def widen_service_filter(module) -> None:
    original = module.establish_connection

    if getattr(original, "widens_service_filter", False):
        return

    @wraps(original)
    async def establish_connection(*args, services=None, **kwargs):
        wanted = [*(services or [])]
        if VENDOR_SERVICE not in wanted:
            wanted.append(VENDOR_SERVICE)
        return await original(*args, services=wanted, **kwargs)

    establish_connection.widens_service_filter = True
    module.establish_connection = establish_connection
