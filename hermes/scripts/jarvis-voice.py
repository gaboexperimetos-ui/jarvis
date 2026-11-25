#!/usr/bin/env python3
"""JARVIS de voz local: «hey jarvis» -> graba -> STT -> modelo local -> voz.

Reutiliza los motores que ya trae Hermes (sherpa-onnx para la palabra de
activación y para la voz local Piper «Miro», faster-whisper para el oído) y
habla con el router local de llama.cpp en http://127.0.0.1:8004/v1. Si la voz
local falla, cae a Edge TTS.
"""

from __future__ import annotations

import asyncio
import fcntl
import json
import logging
import os
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
import wave
from collections import deque
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd
import sherpa_onnx
import edge_tts
from faster_whisper import WhisperModel

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
HERMES_AGENT = HERMES_HOME / "hermes-agent"
if str(HERMES_AGENT) not in sys.path:
    sys.path.insert(0, str(HERMES_AGENT))

from tools import wake_word_engines as we  # noqa: E402

SAMPLE_RATE = 16000
FRAME = 1280
WAKE_PHRASE = os.environ.get("JARVIS_WAKE", "hey jarvis")
SENSITIVITY = float(os.environ.get("JARVIS_SENSITIVITY", "0.6"))
VOICE = os.environ.get("JARVIS_VOICE", "es-ES-AlvaroNeural")
RATE = os.environ.get("JARVIS_RATE", "-10%")
PITCH = os.environ.get("JARVIS_PITCH", "-2Hz")
BASE_URL = os.environ.get("JARVIS_BASE_URL", "http://127.0.0.1:8004/v1").rstrip("/")
MODEL = os.environ.get("JARVIS_MODEL", "deepseek-v4pro")
MAX_ANSWER_CHARS = 800

TTS_DIR = Path(os.environ.get(
    "JARVIS_TTS_DIR",
    str(HERMES_HOME / "cache" / "piper-voices" / "vits-piper-es_ES-miro-high"),
))
TTS_LENGTH_SCALE = float(os.environ.get("JARVIS_TTS_LENGTH_SCALE", "1.15"))
TTS_SPEED = float(os.environ.get("JARVIS_TTS_SPEED", "0.9"))

_DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
_MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre")

SYSTEM_PROMPT = (
    "Eres JARVIS, el asistente personal de Gabo. Hablas español de España y le "
    "tratas siempre de usted, con un tono breve, cálido y directo, como un mayordomo "
    "competente. Tus respuestas se leen en voz alta: no uses markdown, listas, "
    "viñetas, emojis ni símbolos raros. Responde en una o dos frases, salvo que le "
    "pidan explícitamente más detalle. Si no sabes algo o te falta un dato, dilo con "
    "naturalidad en lugar de inventarlo. No tienes acceso a internet ni a datos en "
    "tiempo real: la única referencia temporal fiable es la fecha y hora del equipo que "
    "se te indica abajo. Si te preguntan por la hora de otra ciudad, calcula el desfase "
    "solo si lo conoces con certeza; si no, dilo en vez de inventar la hora."
)

log = logging.getLogger("jarvis-voice")
_running = True
_beep_path: Path | None = None
_tts = None


def _setup_logging() -> None:
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
    stream = logging.StreamHandler(sys.stderr)
    stream.setFormatter(fmt)
    log.addHandler(stream)
    logdir = HERMES_HOME / "logs"
    logdir.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(logdir / "jarvis-voice.log", encoding="utf-8")
    fh.setFormatter(fmt)
    log.addHandler(fh)


def _acquire_lock():
    rundir = HERMES_HOME / "run"
    rundir.mkdir(parents=True, exist_ok=True)
    handle = open(rundir / "jarvis-voice.lock", "w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log.error("ya hay otra instancia de jarvis-voice en marcha")
        raise SystemExit(1)
    return handle


def _build_engine():
    cfg = {
        "phrase": WAKE_PHRASE,
        "sensitivity": SENSITIVITY,
        "profile_routing": False,
        "capture": "local",
        "sherpa": {"model_dir": ""},
    }
    engine = we._SherpaKwsEngine.__new__(we._SherpaKwsEngine)
    engine.last_match = None
    engine._build(cfg, cfg["sherpa"], we._ww())
    return engine


def _rms(frame: np.ndarray) -> float:
    if frame.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(frame.astype(np.float64) ** 2)))


def _make_beep(path: Path) -> None:
    rate = 44100
    dur = 0.12
    t = np.linspace(0, dur, int(rate * dur), endpoint=False)
    tone = (0.25 * np.sin(2 * np.pi * 880 * t) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(tone.tobytes())


def _play_wav(path: Path) -> None:
    for cmd in (["paplay", str(path)], ["pw-play", str(path)],
                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)]):
        try:
            subprocess.run(cmd, check=False, timeout=15)
            return
        except FileNotFoundError:
            continue


def _beep() -> None:
    if _beep_path and _beep_path.exists():
        _play_wav(_beep_path)


def _record(stream, floor: float) -> np.ndarray | None:
    speech_thr = max(floor * 2.0, 500.0)
    silence_thr = max(floor * 1.5, 350.0)
    silence_needed = int(1.2 * SAMPLE_RATE / FRAME)
    max_frames = int(20 * SAMPLE_RATE / FRAME)
    onset_deadline = time.monotonic() + 6.0
    frames: list[np.ndarray] = []
    onset = False
    silence_run = 0
    while len(frames) < max_frames and _running:
        data, _ = stream.read(FRAME)
        frame = data[:, 0]
        level = _rms(frame)
        if not onset:
            if level > speech_thr:
                onset = True
                frames.append(frame)
            elif time.monotonic() > onset_deadline:
                return None
            continue
        frames.append(frame)
        if level < silence_thr:
            silence_run += 1
            if silence_run >= silence_needed:
                break
        else:
            silence_run = 0
    if not onset or len(frames) < int(0.3 * SAMPLE_RATE / FRAME):
        return None
    return np.concatenate(frames)


def _write_wav(audio: np.ndarray, path: Path) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(audio.astype(np.int16).tobytes())


def _transcribe(model: WhisperModel, wav_path: Path) -> str:
    segments, _ = model.transcribe(str(wav_path), language="es", vad_filter=True, beam_size=1)
    return " ".join(seg.text.strip() for seg in segments).strip()


def _now_text() -> str:
    now = datetime.now().astimezone()
    offset = now.strftime("%z")
    offset = f"UTC{offset[:3]}:{offset[3:]}" if offset else "UTC"
    return (
        f"{_DIAS[now.weekday()]}, {now.day} de {_MESES[now.month - 1]} de {now.year}, "
        f"{now.hour:02d}:{now.minute:02d} ({offset})"
    )


def _ask(text: str) -> str:
    system = f"{SYSTEM_PROMPT}\n\nFecha y hora actuales en el equipo: {_now_text()}."
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ],
        "max_tokens": 220,
        "temperature": 0.4,
    }
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return str(data["choices"][0]["message"]["content"]).strip()


def _clean_for_speech(text: str) -> str:
    for ch in ("*", "#", "`", "_", "~", "|"):
        text = text.replace(ch, "")
    text = " ".join(text.split())
    if len(text) > MAX_ANSWER_CHARS:
        cut = text[:MAX_ANSWER_CHARS]
        stop = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"))
        text = cut[: stop + 1] if stop > 0 else cut
    return text


def _build_tts():
    cfg = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                model=str(TTS_DIR / "es_ES-miro-high.onnx"),
                tokens=str(TTS_DIR / "tokens.txt"),
                data_dir=str(TTS_DIR / "espeak-ng-data"),
                length_scale=TTS_LENGTH_SCALE,
                noise_scale=0.667,
                noise_scale_w=0.8,
            ),
            num_threads=2,
            provider="cpu",
        ),
        max_num_sentences=1,
    )
    if not cfg.validate():
        raise RuntimeError("configuración TTS local inválida")
    return sherpa_onnx.OfflineTts(cfg)


def _speak_local(text: str, workdir: Path) -> None:
    global _tts
    if _tts is None:
        log.info("cargando voz local Miro…")
        _tts = _build_tts()
    gen = sherpa_onnx.GenerationConfig()
    gen.sid = 0
    gen.speed = TTS_SPEED
    gen.silence_scale = 0.25
    audio = _tts.generate(text, gen)
    if len(audio.samples) == 0:
        raise RuntimeError("la voz local no generó audio")
    pcm = np.clip(np.asarray(audio.samples, dtype=np.float32), -1, 1)
    wav = workdir / "answer.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(audio.sample_rate)
        w.writeframes((pcm * 32767).astype(np.int16).tobytes())
    _play_wav(wav)


def _speak_edge(text: str, workdir: Path) -> None:
    mp3 = workdir / "answer.mp3"
    asyncio.run(
        edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH).save(str(mp3))
    )
    subprocess.run(
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(mp3)],
        check=False,
        timeout=120,
    )


def _speak(text: str, workdir: Path) -> None:
    clean = _clean_for_speech(text)
    if not clean:
        return
    try:
        _speak_local(clean, workdir)
        return
    except Exception as exc:
        log.warning("voz local falló (%s); usando Edge", exc)
    _speak_edge(clean, workdir)


def _handle(stream, floor: float, engine, whisper: WhisperModel, workdir: Path) -> None:
    _beep()
    flush_until = time.monotonic() + 0.25
    while time.monotonic() < flush_until:
        stream.read(FRAME)
    audio = _record(stream, floor)
    if audio is None:
        log.info("no se detectó voz tras la activación")
        return
    wav = workdir / "utterance.wav"
    _write_wav(audio, wav)
    text = _transcribe(whisper, wav)
    if not text:
        log.info("transcripción vacía")
        return
    log.info("usted: %s", text)
    answer = _ask(text)
    log.info("jarvis: %s", answer)
    try:
        _speak(answer, workdir)
    except Exception as exc:
        log.warning("TTS falló: %s", exc)


def _selftest(engine, whisper: WhisperModel, workdir: Path) -> int:
    hey = workdir / "hey_jarvis.wav"
    _synth_wav("Hey Jarvis", "en-US-GuyNeural", hey)
    with wave.open(str(hey), "rb") as w:
        raw = w.readframes(w.getnframes())
    audio = np.frombuffer(raw, dtype=np.int16)
    fired = False
    for i in range(0, len(audio) - FRAME + 1, FRAME):
        if engine.process(audio[i:i + FRAME]):
            fired = True
            break
    engine.reset()
    log.info("autotest activación: %s", "OK" if fired else "FALLO")
    silence = np.zeros(SAMPLE_RATE * 2, dtype=np.int16)
    false_fire = any(engine.process(silence[i:i + FRAME])
                     for i in range(0, len(silence) - FRAME + 1, FRAME))
    engine.reset()
    log.info("autotest silencio: %s", "OK (no dispara)" if not false_fire else "FALLO (disparó)")

    question = workdir / "question.wav"
    _synth_wav("¿Qué hora es en Tokio ahora mismo?", VOICE, question)
    text = _transcribe(whisper, question)
    log.info("autotest STT: %s", text or "FALLO")
    if not text:
        return 1
    answer = _ask(text)
    log.info("autotest modelo: %s", answer or "FALLO")
    if not answer:
        return 1
    try:
        _speak(answer, workdir)
        log.info("autotest TTS: OK (debería haber sonado)")
    except Exception as exc:
        log.warning("autotest TTS falló: %s", exc)
    return 0 if (fired and not false_fire) else 1


def _synth_wav(text: str, voice: str, out_wav: Path) -> None:
    mp3 = out_wav.with_suffix(".mp3")
    asyncio.run(edge_tts.Communicate(text, voice).save(str(mp3)))
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-ar", str(SAMPLE_RATE),
         "-ac", "1", "-c:a", "pcm_s16le", str(out_wav)],
        check=True,
    )


def _on_signal(signum, _frame) -> None:
    global _running
    _running = False
    log.info("señal %s recibida, cerrando", signum)


def main() -> int:
    global _beep_path
    _setup_logging()
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    _lock = _acquire_lock()

    workdir = Path(tempfile.mkdtemp(prefix="jarvis-voice-", dir="/tmp/opencode"))
    _beep_path = workdir / "beep.wav"
    _make_beep(_beep_path)

    log.info("cargando oído (faster-whisper base)…")
    whisper = WhisperModel("base", device="cpu", compute_type="int8")
    log.info("cargando detector «%s»…", WAKE_PHRASE)
    engine = _build_engine()

    if "--selftest" in sys.argv:
        try:
            return _selftest(engine, whisper, workdir)
        finally:
            engine.close()

    log.info("escuchando «%s»…", WAKE_PHRASE)
    floor_hist: deque[float] = deque(maxlen=40)
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                            blocksize=FRAME) as stream:
            while _running:
                data, _ = stream.read(FRAME)
                frame = data[:, 0]
                floor_hist.append(_rms(frame))
                floor = float(np.median(floor_hist)) if len(floor_hist) >= 10 else 400.0
                if engine.process(frame):
                    log.info("«%s» detectado", WAKE_PHRASE)
                    engine.reset()
                    try:
                        _handle(stream, floor, engine, whisper, workdir)
                    except Exception as exc:
                        log.exception("error atendiendo la petición: %s", exc)
                    engine.reset()
                    log.info("escuchando «%s»…", WAKE_PHRASE)
    finally:
        engine.close()
        log.info("detenido")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
