"""음성 파일 길이 확인 (API-07 BR-12: 60초 이하). 외부 도구 없이 wav·mp3만 정확히 잰다.

그 밖의 형식은 길이를 알 수 없어 None 을 돌려주고, 긴 파일은 CSR 이 거부한다(STT006).
"""

import io
import wave

_MP3_BITRATES_V1_L3 = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320]
_MP3_SAMPLE_RATES_V1 = [44100, 48000, 32000]
_MP3_SAMPLES_PER_FRAME = 1152


def wav_seconds(data: bytes) -> float | None:
    try:
        with wave.open(io.BytesIO(data)) as w:
            rate = w.getframerate()
            return w.getnframes() / rate if rate else None
    except (wave.Error, EOFError):
        return None


def mp3_seconds(data: bytes) -> float | None:
    """MPEG-1 Layer III 프레임을 세어 길이를 구한다 (ID3 태그는 건너뜀). 읽을 수 없으면 None."""
    i = 0
    if data[:3] == b"ID3" and len(data) >= 10:
        size = (
            ((data[6] & 0x7F) << 21) | ((data[7] & 0x7F) << 14) | ((data[8] & 0x7F) << 7) | (data[9] & 0x7F)
        )
        i = 10 + size
    seconds = 0.0
    frames = 0
    n = len(data)
    while i + 4 <= n:
        header = int.from_bytes(data[i : i + 4], "big")
        version, layer = (header >> 19) & 3, (header >> 17) & 3
        bitrate_idx, rate_idx, pad = (header >> 12) & 15, (header >> 10) & 3, (header >> 9) & 1
        if (
            (header >> 21) & 0x7FF != 0x7FF
            or version != 3
            or layer != 1
            or bitrate_idx in (0, 15)
            or rate_idx == 3
        ):
            i += 1
            continue
        rate = _MP3_SAMPLE_RATES_V1[rate_idx]
        i += 144000 * _MP3_BITRATES_V1_L3[bitrate_idx] // rate + pad
        seconds += _MP3_SAMPLES_PER_FRAME / rate
        frames += 1
    return seconds if frames else None


def duration_seconds(data: bytes, ext: str) -> float | None:
    ext = ext.lower().lstrip(".")
    if ext == "wav":
        return wav_seconds(data)
    if ext == "mp3":
        return mp3_seconds(data)
    return None
