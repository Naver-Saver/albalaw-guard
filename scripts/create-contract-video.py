"""Render Saver's original 30-second educational video.

Requires Pillow, imageio-ffmpeg, and Korean regular/bold fonts (Malgun Gothic
on Windows, or set VIDEO_FONT_REGULAR / VIDEO_FONT_BOLD). Narration is fetched
once per scene from the running Saver /api/tts endpoint and cached outside git.
Usage: python scripts/create-contract-video.py --api http://127.0.0.1:8000/api
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request
import wave

from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend/public/videos"
W, H, FPS = 1280, 720, 24
GREEN, INK, MUTED = "#008647", "#183E2B", "#61756A"
SCENES = [
    (0, 3, "서명하기 전, 잠깐!", ["첫 알바의 시작", "계약서부터 차근차근"], "첫 알바 계약서, 서명하기 전 잠깐!"),
    (3, 9, "얼마를, 언제 받나요?", ["시급과 임금 계산방법", "지급일과 지급방법 확인"], "시급과 계산방법, 언제 어떻게 받는지 확인하세요."),
    (9, 16, "일하는 시간도 꼼꼼히", ["근무요일과 시작·종료 시간", "휴게시간과 휴일도 확인"], "근무요일과 일하는 시간, 휴게시간과 휴일도 약속한 내용과 같은지 살펴보세요."),
    (16, 22, "빈칸은 확인하고 서명", ["모르는 내용은 먼저 질문", "약속한 내용은 글로 남기기"], "모르는 내용은 먼저 물어보고, 약속한 내용과 빈칸을 확인한 뒤 서명하세요."),
    (22, 27, "계약서, 나도 한 부", ["작성한 계약서를 받아서", "다시 볼 수 있게 보관하기"], "작성한 계약서는 꼭 받아서, 다시 볼 수 있게 보관하세요."),
    (27, 30, "궁금할 땐 1350", ["고용노동부 상담 안내", "내 권리, 알고 시작해요"], "궁금할 땐 고용노동부, 일삼오공."),
]
FONT_REGULAR = os.environ.get("VIDEO_FONT_REGULAR", "C:/Windows/Fonts/malgun.ttf")
FONT_BOLD = os.environ.get("VIDEO_FONT_BOLD", "C:/Windows/Fonts/malgunbd.ttf")
FONTS = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in FONTS:
        FONTS[key] = ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size)
    return FONTS[key]


def txt(draw, xy, text, size=24, fill=INK, bold=False):
    draw.text(xy, text, font=font(size, bold), fill=fill)


def check(draw, x, y, color=GREEN, scale=1):
    draw.line([(x, y + 10*scale), (x + 8*scale, y + 18*scale), (x + 24*scale, y)], fill=color, width=max(3, int(4*scale)))


def frame(t):
    idx = next((i for i, s in enumerate(SCENES) if s[0] <= t < s[1]), 5)
    start, end, title, bullets, _ = SCENES[idx]
    age = t - start
    ease = 1 - (1 - min(age / .55, 1)) ** 3
    yoff = round(22 * (1 - ease))
    im = Image.new("RGB", (W, H), "#F3F8F4")
    d = ImageDraw.Draw(im)
    d.ellipse((880, -230, 1520, 410), fill="#E1F1E6")
    d.ellipse((-180, 510, 240, 930), fill="#E7F2EA")
    txt(d, (64, 34), "Saver", 31, GREEN, True)
    txt(d, (173, 47), "알바생 노동권 지킴이", 17, MUTED)
    d.rounded_rectangle((1076, 38, 1216, 78), 20, fill="#E0EFE5")
    txt(d, (1095, 45), "30초 체크", 20, GREEN, True)

    # Large editorial copy, readable when the player is scaled down.
    label = "BEFORE YOU SIGN" if idx == 0 else "CHECK COMPLETE" if idx == 5 else f"CHECK 0{idx} / 04"
    txt(d, (66, 159 + yoff), label, 19, GREEN, True)
    # Two-line titles intentionally fit within the left column.
    titles = [["서명하기 전,", "잠깐!"], ["얼마를,", "언제 받나요?"], ["일하는 시간도", "꼼꼼히"], ["빈칸은 확인하고", "서명"], ["계약서,", "나도 한 부"], ["궁금할 땐", "1350"]][idx]
    for j, line in enumerate(titles):
        txt(d, (62, 202 + 76*j + yoff), line, 58 if idx != 5 else (58 if j == 0 else 78), GREEN if j == 1 else INK, True)
    for j, line in enumerate(bullets):
        check(d, 68, 405 + 48*j + yoff, scale=.8)
        txt(d, (103, 396 + 48*j + yoff), line, 26)

    # Original document illustration; no real personal data or wage amounts.
    bob = round(3 * math.sin(age * 1.5))
    x, y = 745, 142 + bob
    d.rounded_rectangle((x+10, y+12, x+447, y+397), 23, fill="#DCE9E0")
    d.rounded_rectangle((x, y, x+437, y+385), 20, fill="white", outline="#C6DACE", width=2)
    txt(d, (x+30, y+24), "근로계약서", 31, INK, True)
    txt(d, (x+30, y+72), "서로의 약속을 글로 남겨요", 17, MUTED)
    rows = ["임금 · 지급일", "근무시간 · 휴일", "내용 확인 · 서명", "계약서 교부"]
    for j, row in enumerate(rows):
        yy = y+117 + j*57
        active = idx in (0, 5) or idx == j+1
        d.rounded_rectangle((x+24, yy, x+411, yy+46), 10, fill="#EAF6EE" if active else "#F6F8F6")
        txt(d, (x+41, yy+7), row, 21, INK if active else MUTED, active)
        if active and age > .25:
            check(d, x+363, yy+13, scale=.7)
    d.rounded_rectangle((x+48, y+362, x+389, y+417), 27, fill=GREEN)
    txt(d, (x+88, y+374), "알고 쓰면 더 든든해요", 21, "white", True)

    # Persistent context and progress. The full narration is also a WebVTT track.
    txt(d, (66, 576), "알바 계약서, 서명 전 네 가지 체크", 24, GREEN, True)
    txt(d, (66, 622), "Saver 제작 · 참고: 고용노동부 근로계약서 작성 안내", 16, MUTED)
    txt(d, (66, 651), "기본 교육 자료 · 개별 근로조건은 공식 안내와 상담으로 확인하세요", 15, MUTED)
    for i in range(6):
        xx = 1040 + i*29
        d.ellipse((xx, 586, xx+10, 596), fill=GREEN if i == idx else "#D0DED5")
    d.rectangle((0, H-6, W, H), fill="#DCEADF")
    d.rectangle((0, H-6, round(W * min(t/30, 1)), H), fill=GREEN)
    # Brief cross-fade from a plain background at each cut.
    if age < .16 and idx > 0:
        im = Image.blend(Image.new("RGB", (W, H), "#F3F8F4"), im, age/.16)
    return im


def duration(ffmpeg, path):
    probe = subprocess.run([ffmpeg, "-i", str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    found = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", probe.stderr)
    if not found:
        raise RuntimeError(f"Cannot probe audio duration: {path.name}")
    h, m, s = map(float, found.groups())
    return h*3600 + m*60 + s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://127.0.0.1:8000/api")
    ap.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "saver-contract-video")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    args.cache.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    clips = []
    for i, (start, end, _, _, text) in enumerate(SCENES):
        path = args.cache / (hashlib.sha256(text.encode()).hexdigest()[:16] + ".mp3")
        if not path.exists():
            req = urllib.request.Request(args.api.rstrip("/") + "/tts", data=json.dumps({"text": text, "lang": "ko"}).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as response:
                if "audio" not in response.headers.get("Content-Type", ""):
                    raise RuntimeError("TTS returned a non-audio response")
                path.write_bytes(response.read())
        length = duration(ffmpeg, path)
        speed = max(1.0, length / (end-start-.25))
        if speed > 1.5:
            raise RuntimeError(f"Scene {i}: narration too long; shorten the script")
        print(f"Narration {i+1}/6: {length:.2f}s, speed {speed:.2f}", flush=True)
        clips.append((path, speed))

    silent = args.cache / "silent.mp4"
    command = [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "22", "-pix_fmt", "yuv420p", str(silent)]
    encoder = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        for n in range(30*FPS):
            encoder.stdin.write(frame(n/FPS).tobytes())
            if n % (5*FPS) == 0:
                print(f"Rendered {n//FPS}/30 seconds", flush=True)
    finally:
        encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError("Video encoding failed")
    # Place each decoded mono PCM clip directly on the timeline. Scenes never
    # overlap, so this avoids a complex streaming mixer and fixes total duration.
    rate = 24000
    pcm = bytearray(30 * rate * 2)
    for (path, speed), scene in zip(clips, SCENES):
        start, end = scene[:2]
        decoded = subprocess.run([ffmpeg, "-nostdin", "-loglevel", "error", "-i", str(path), "-af", f"atempo={speed:.6f}", "-f", "s16le", "-ac", "1", "-ar", str(rate), "-"], capture_output=True, check=True).stdout
        offset = round((start+.1)*rate)*2
        limit = round((end-.05)*rate)*2
        decoded = decoded[:limit-offset]
        pcm[offset:offset+len(decoded)] = decoded
    audio = args.cache / "narration.wav"
    with wave.open(str(audio), "wb") as wav:
        wav.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        wav.writeframes(pcm)
    command = [ffmpeg, "-nostdin", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-t", "30", "-movflags", "+faststart", str(OUT / "contract-check.mp4")]
    subprocess.run(command, check=True)
    frame(1.5).save(OUT / "contract-check-poster.jpg", quality=92)
    frames = [frame((s[0]+s[1])/2).resize((640, 360)) for s in SCENES]
    sheet = Image.new("RGB", (1280, 1080), "white")
    for i, im in enumerate(frames):
        sheet.paste(im, ((i%2)*640, (i//2)*360))
    sheet.save(args.cache / "contact-sheet.jpg", quality=94)
    vtt = "WEBVTT\n\n"
    for start, end, _, _, text in SCENES:
        vtt += f"00:00:{start:02}.000 --> 00:00:{end:02}.000\n{text}\n\n"
    (OUT / "contract-check.ko.vtt").write_text(vtt, encoding="utf-8")
    print(f"Saved 30-second MP4, poster and captions to {OUT}")
    print(f"Review contact sheet: {args.cache / 'contact-sheet.jpg'}")


if __name__ == "__main__":
    main()
