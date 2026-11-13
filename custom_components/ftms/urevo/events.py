from pyftms import UpdateEvent
from pyftms.client import const as c

from .reading import TreadmillReading


def reading_to_update_event(reading: TreadmillReading) -> UpdateEvent:
    return UpdateEvent(
        event_id="update",
        event_data={
            c.SPEED_INSTANT: reading.speed_kmh,
            c.TIME_ELAPSED: reading.elapsed_s,
            c.DISTANCE_TOTAL: reading.distance_m,
            c.ENERGY_TOTAL: reading.energy_kcal,
            c.STEP_COUNT: reading.steps,
        },
    )
