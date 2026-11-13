import dataclasses as dc

HEADER = bytes.fromhex("025103")
TRAILER = 0x03
FRAME_LENGTH = 19


@dc.dataclass(frozen=True, kw_only=True)
class TreadmillReading:
    speed_kmh: float
    elapsed_s: int
    distance_m: int
    energy_kcal: float
    steps: int


def decode_reading(data: bytes) -> TreadmillReading | None:
    if len(data) != FRAME_LENGTH or data[:3] != HEADER or data[-1] != TRAILER:
        return None

    return TreadmillReading(
        speed_kmh=data[3] / 10,
        elapsed_s=int.from_bytes(data[5:7], "little"),
        distance_m=int.from_bytes(data[7:9], "little") * 10,
        energy_kcal=int.from_bytes(data[9:11], "little") / 10,
        steps=int.from_bytes(data[11:13], "little"),
    )
