#!/usr/bin/env python3
"""orquestar-freebuff.py - conduce la TUI de freebuff por un pseudo-terminal.

freebuff no tiene modo headless: solo TUI. Este driver la lanza con --cwd,
escribe el brief, espera a que la pantalla se quede quieta y devuelve el texto
visible sin secuencias ANSI. Es scraping de pantalla: fragil por naturaleza.

Uso: orquestar-freebuff.py <dir> <brief|archivo|-> [segundos_espera]
"""
import os
import pty
import re
import select
import signal
import subprocess
import sys
import time


def strip_ansi(s: str) -> str:
    s = re.sub(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)", "", s)
    s = re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", s)
    s = re.sub(r"\x1b[()][A-Za-z0-9]", "", s)
    s = s.replace("\r", "")
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s


def main() -> int:
    if len(sys.argv) < 3:
        print("uso: orquestar-freebuff.py <dir> <brief|archivo|-> [espera]", file=sys.stderr)
        return 2
    workdir = os.path.abspath(sys.argv[1])
    brief = sys.argv[2]
    settle = float(sys.argv[3]) if len(sys.argv) > 3 else 8.0

    if not os.path.isdir(workdir):
        print(f"directorio inexistente: {workdir}", file=sys.stderr)
        return 2
    if brief == "-":
        prompt = sys.stdin.read()
    elif os.path.isfile(brief):
        prompt = open(brief, encoding="utf-8").read()
    else:
        prompt = brief
    if not prompt.strip():
        print("brief vacio", file=sys.stderr)
        return 2

    env = os.environ.copy()
    env.setdefault("TERM", "xterm-256color")
    env["COLUMNS"] = env.get("COLUMNS", "120")
    env["LINES"] = env.get("LINES", "40")

    master, slave = pty.openpty()
    proc = subprocess.Popen(
        ["freebuff", "--cwd", workdir],
        stdin=slave, stdout=slave, stderr=slave,
        env=env, start_new_session=True, close_fds=True,
    )
    os.close(slave)

    buf = bytearray()

    def pump(seconds: float, quiet: float) -> None:
        end = time.time() + seconds
        last = time.time()
        while time.time() < end:
            r, _, _ = select.select([master], [], [], 0.2)
            if r:
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                buf.extend(chunk)
                last = time.time()
            elif time.time() - last >= quiet:
                break

    try:
        pump(12, 2)                    # arranque de la TUI
        os.write(master, (prompt.strip() + "\r").encode())
        pump(settle + 180, settle)     # respuesta + asentamiento
    finally:
        for _ in range(2):
            try:
                os.write(master, b"\x03")
                time.sleep(0.3)
            except OSError:
                break
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                pass
        os.close(master)

    text = strip_ansi(buf.decode("utf-8", "replace"))
    lines = [ln.rstrip() for ln in text.splitlines()]
    out = "\n".join(ln for ln in lines if ln.strip())
    print(out[-8000:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
