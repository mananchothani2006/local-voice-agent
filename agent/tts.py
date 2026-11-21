"""Cross-platform TTS helper (Kokoro-ONNX on CPU, with Piper fallback)."""

import os
import shutil
import subprocess
import sys


def speak(text: str, voice: str = "af_bella", kokoro_dir: str = "", piper_bin: str = "", piper_model: str = "") -> None:
    if not text:
        return

    k_model = os.path.join(kokoro_dir, "kokoro-v1.0.onnx") if kokoro_dir else ""
    k_voices = os.path.join(kokoro_dir, "voices-v1.0.bin") if kokoro_dir else ""

    if k_model and os.path.isfile(k_model) and os.path.isfile(k_voices) and shutil.which("pw-play"):
        try:
            import numpy as np
            from kokoro_onnx import Kokoro

            k = Kokoro(k_model, k_voices)
            samples, sr = k.create(text, voice=voice, speed=1.0, lang="en-us")
            pcm = (np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
            subprocess.run(
                ["pw-play", "--raw", f"--rate={sr}", "--channels=1", "--format=s16", "-"],
                input=pcm,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
        except Exception:
            pass

    if piper_bin and os.path.isfile(piper_bin) and piper_model and os.path.isfile(piper_model) and shutil.which("pw-play"):
        p1 = subprocess.Popen(
            [piper_bin, "--model", piper_model, "--output-raw"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        p2 = subprocess.Popen(
            ["pw-play", "--raw", "--rate=22050", "--channels=1", "--format=s16", "-"],
            stdin=p1.stdout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if p1.stdin:
            p1.stdin.write((text + "\n").encode())
            p1.stdin.close()
        p2.wait()
        p1.wait()
