#!/usr/bin/env python
"""Identify songs in a local audio or video file with AudD and/or ACRCloud.

The script extracts short, compact MP3 clips before sending them to a provider.
This makes it suitable for long videos containing several songs and respects the
providers' small-file recognition endpoints.

Credentials (keep these out of this file and Git):
  AUDD_API_TOKEN
  ACRCLOUD_HOST               e.g. identify-eu-west-1.acrcloud.com
  ACRCLOUD_ACCESS_KEY
  ACRCLOUD_ACCESS_SECRET

Optional no-key provider:
  ShazamIO is an unofficial, reverse-engineered Shazam client. Install and run
  it with: uv run --with shazamio python .\\recognize_songs.py --provider shazamio
  It can stop working if Shazam changes its private service.

Examples:
  $env:AUDD_API_TOKEN = '...'
  python .\recognize_songs.py

  $env:ACRCLOUD_HOST = 'identify-eu-west-1.acrcloud.com'
  $env:ACRCLOUD_ACCESS_KEY = '...'
  $env:ACRCLOUD_ACCESS_SECRET = '...'
  python .\recognize_songs.py --provider acrcloud --starts 30,90,150

The AudD and ACRCloud paths use only the Python standard library. ffmpeg must
be on PATH; ShazamIO is an optional dependency as shown above.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import hmac
import json
import mimetypes
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


HERE = Path(__file__).resolve().parent
DEFAULT_INPUT = HERE / "Kargin Haghordum sketch 142 (Hayko Mko) [AXFZ8ymj--w].mp3"
AUDD_URL = "https://api.audd.io/"


def parse_starts(value: str) -> list[float]:
    """Parse comma-separated clip offsets and reject invalid values early."""
    try:
        starts = [float(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--starts must be comma-separated seconds") from exc
    if not starts or any(start < 0 for start in starts):
        raise argparse.ArgumentTypeError("--starts must contain one or more non-negative seconds")
    return starts


def make_clip(source: Path, start: float, duration: float, output: Path) -> None:
    """Extract a small MP3 sample from audio or video without changing the source."""
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        str(start),
        "-i",
        str(source),
        "-t",
        str(duration),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "44100",
        "-b:a",
        "128k",
        str(output),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode:
        detail = completed.stderr.strip() or "ffmpeg did not produce a clip"
        raise RuntimeError(f"Could not extract {start:g}s clip: {detail}")
    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError(f"ffmpeg produced an empty clip at {start:g}s")


def multipart_body(fields: dict[str, str], file_field: str, path: Path) -> tuple[bytes, str]:
    """Build an RFC 7578 body without adding a third-party HTTP dependency."""
    boundary = f"----song-recognition-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode(),
                b"\r\n",
            ]
        )

    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    chunks.extend(
        [
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; name="{file_field}"; '
                f'filename="{path.name}"\r\nContent-Type: {mime_type}\r\n\r\n'
            ).encode(),
            path.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def post_multipart(url: str, fields: dict[str, str], file_field: str, path: Path) -> dict[str, Any]:
    body, content_type = multipart_body(fields, file_field, path)
    request = Request(url, data=body, method="POST", headers={"Content-Type": content_type})
    try:
        with urlopen(request, timeout=45) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{exc.code} {exc.reason}: {raw}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error: {exc.reason}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Provider returned non-JSON data: {raw[:500]}") from exc


def recognize_audd(clip: Path, token: str) -> dict[str, Any]:
    return post_multipart(
        AUDD_URL,
        {
            "api_token": token,
            "return": "apple_music,spotify,musicbrainz",
        },
        "file",
        clip,
    )


def recognize_acrcloud(clip: Path, host: str, access_key: str, access_secret: str) -> dict[str, Any]:
    """Call ACRCloud Identification API v1 using its documented HMAC-SHA1 signature."""
    timestamp = str(int(time.time()))
    data_type = "audio"
    string_to_sign = "\n".join(
        ["POST", "/v1/identify", access_key, data_type, "1", timestamp]
    )


def recognize_shazamio(clip: Path) -> dict[str, Any]:
    """Recognize a clip with the optional, unofficial ShazamIO client."""
    try:
        from shazamio import Shazam
    except ImportError as exc:
        raise RuntimeError(
            "ShazamIO is not installed. Run: uv run --with shazamio python "
            ".\\recognize_songs.py --provider shazamio"
        ) from exc

    async def recognize() -> dict[str, Any]:
        return await Shazam().recognize(str(clip))

    try:
        return asyncio.run(recognize())
    except Exception as exc:  # ShazamIO returns provider-specific failures.
        raise RuntimeError(f"ShazamIO request failed: {exc}") from exc
    signature = base64.b64encode(
        hmac.new(access_secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha1).digest()
    ).decode("ascii")
    return post_multipart(
        f"https://{host}/v1/identify",
        {
            "access_key": access_key,
            "sample_bytes": str(clip.stat().st_size),
            "timestamp": timestamp,
            "signature": signature,
            "data_type": data_type,
            "signature_version": "1",
        },
        "sample",
        clip,
    )


def get_acrcloud_credentials() -> tuple[str, str, str]:
    names = ("ACRCLOUD_HOST", "ACRCLOUD_ACCESS_KEY", "ACRCLOUD_ACCESS_SECRET")
    values = tuple(os.environ.get(name, "") for name in names)
    missing = [name for name, value in zip(names, values) if not value]
    if missing:
        raise RuntimeError("Missing environment variable(s): " + ", ".join(missing))
    return values  # type: ignore[return-value]


def extract_match(provider: str, response: dict[str, Any]) -> str:
    """Produce a short console line while preserving the full raw JSON in the file."""
    if provider == "audd":
        result = response.get("result")
        if isinstance(result, dict):
            return f"{result.get('artist', 'Unknown artist')} — {result.get('title', 'Unknown title')}"
        return "no match"

    if provider == "shazamio":
        track = response.get("track")
        if isinstance(track, dict):
            return f"{track.get('subtitle', 'Unknown artist')} — {track.get('title', 'Unknown title')}"
        return "no match"

    metadata = response.get("metadata")
    music = metadata.get("music") if isinstance(metadata, dict) else None
    if isinstance(music, list) and music:
        match = music[0]
        artists = ", ".join(a.get("name", "") for a in match.get("artists", []))
        return f"{artists or 'Unknown artist'} — {match.get('title', 'Unknown title')}"
    return "no match"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, default=DEFAULT_INPUT, help="audio or video file")
    parser.add_argument(
        "--provider",
        choices=("audd", "acrcloud", "shazamio", "both", "all"),
        default="both",
        help="both means AudD + ACRCloud; all also includes unofficial ShazamIO",
    )
    parser.add_argument(
        "--starts",
        type=parse_starts,
        # Covers the known music: 0–20s and 3:24–3:55 (204–235s).
        default=[0.0, 8.0, 204.0, 216.0, 223.0],
    )
    parser.add_argument("--duration", type=float, default=12.0, help="clip length in seconds (default: 12)")
    parser.add_argument("--output", type=Path, default=HERE / "song_recognition_results.json")
    args = parser.parse_args()

    source = args.input.expanduser().resolve()
    if not source.is_file():
        parser.error(f"input file does not exist: {source}")
    if args.duration <= 0:
        parser.error("--duration must be positive")
    if not shutil.which("ffmpeg"):
        parser.error("ffmpeg was not found on PATH; install it or add it to PATH")

    requested = {
        "both": ("audd", "acrcloud"),
        "all": ("audd", "acrcloud", "shazamio"),
    }.get(args.provider, (args.provider,))
    providers: dict[str, Any] = {}
    if "audd" in requested:
        token = os.environ.get("AUDD_API_TOKEN")
        if token:
            providers["audd"] = lambda clip: recognize_audd(clip, token)
        else:
            print("Skipping AudD: set AUDD_API_TOKEN to enable it.", file=sys.stderr)
    if "acrcloud" in requested:
        try:
            host, access_key, access_secret = get_acrcloud_credentials()
            providers["acrcloud"] = lambda clip: recognize_acrcloud(clip, host, access_key, access_secret)
        except RuntimeError as exc:
            print(f"Skipping ACRCloud: {exc}", file=sys.stderr)
    if "shazamio" in requested:
        try:
            import shazamio  # noqa: F401 - check the optional dependency before extraction.

            providers["shazamio"] = recognize_shazamio
        except ImportError:
            print(
                "Skipping ShazamIO: install it with `uv run --with shazamio python "
                ".\\recognize_songs.py --provider shazamio`.",
                file=sys.stderr,
            )
    if not providers:
        parser.error("No provider credentials found. See the script header for required environment variables.")

    results: dict[str, Any] = {
        "input": str(source),
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "clip_duration_seconds": args.duration,
        "clips": [],
    }
    with tempfile.TemporaryDirectory(prefix="song_recognition_") as temporary:
        temp_dir = Path(temporary)
        for index, start in enumerate(args.starts, start=1):
            clip = temp_dir / f"clip_{index:02d}_{start:g}s.mp3"
            print(f"Extracting clip {index}/{len(args.starts)} at {start:g}s …")
            try:
                make_clip(source, start, args.duration, clip)
            except RuntimeError as exc:
                print(f"  Skipped: {exc}", file=sys.stderr)
                results["clips"].append({"start_seconds": start, "error": str(exc)})
                continue

            clip_result: dict[str, Any] = {"start_seconds": start, "providers": {}}
            for provider, recognizer in providers.items():
                try:
                    response = recognizer(clip)
                    clip_result["providers"][provider] = response
                    print(f"  {provider}: {extract_match(provider, response)}")
                except RuntimeError as exc:
                    clip_result["providers"][provider] = {"error": str(exc)}
                    print(f"  {provider}: error — {exc}", file=sys.stderr)
            results["clips"].append(clip_result)

    output = args.output.expanduser().resolve()
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved full responses to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
