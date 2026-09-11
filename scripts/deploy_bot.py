"""
Build and deploy the Telegram bot to Cloud Run WITHOUT building a container locally.

Cloud Build does the work, so nothing heavy runs on the laptop — no Docker Desktop,
no image pull, no node_modules install. The source archive holds only the paths
`bot/Dockerfile` actually COPYs, which keeps it under a megabyte (the repo root
holds gigabytes of media).

Auth reuses the firebase CLI's own login — whatever `firebase login` stored in
~/.config/configstore/firebase-tools.json — so there is nothing extra to set up
and no key file. The account must be Owner/Editor on the project.

Usage:
  uv run python scripts/deploy_bot.py v4          # build :v4 and point Cloud Run at it
  uv run python scripts/deploy_bot.py v4 --build-only

After deploying, sanity-check it:
  curl https://<service-url>/health                       -> ok
  curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"  -> 0 pending, no error
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import tarfile
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "kargin-archive"
PROJECT_NUMBER = "708563817336"
REGION = "europe-west3"
SERVICE = "kargin-bot"
BUCKET = f"{PROJECT}_cloudbuild"

# The firebase CLI's public OAuth client; the stored refresh token belongs to it.
CLIENT_ID = "563584335869-fgrhgmd47bqnekij5i8b5pr03ho849e6.apps.googleusercontent.com"
CLIENT_SECRET = "j9iVZfS8kkCEFUPaAeJV0sAi"
FIREBASE_CONFIG = Path.home() / ".config" / "configstore" / "firebase-tools.json"

# Exactly what bot/Dockerfile references. Anything else is dead weight in the upload.
INCLUDE = [
    "bot/Dockerfile", "bot/package.json", "bot/package-lock.json", "bot/tsconfig.json",
    "bot/src", "web/lib", "web/public/data/sketches.json",
]

(ROOT / "logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(ROOT / "logs" / "deploy_bot.log", encoding="utf-8")],
)
log = logging.getLogger("deploy_bot")


def access_token() -> str:
    if not FIREBASE_CONFIG.exists():
        raise RuntimeError(f"no firebase CLI login at {FIREBASE_CONFIG} — run `firebase login` first")
    refresh = json.loads(FIREBASE_CONFIG.read_text(encoding="utf-8"))["tokens"]["refresh_token"]
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
              "refresh_token": refresh, "grant_type": "refresh_token"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def auth() -> dict:
    return {"Authorization": f"Bearer {access_token()}", "Content-Type": "application/json"}


def build_archive() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for rel in INCLUDE:
            path = ROOT / rel
            if not path.exists():
                raise RuntimeError(f"missing build input: {rel}")
            if path.is_dir():
                for f in sorted(path.rglob("*")):
                    if f.is_file() and "__tests__" not in f.parts and "node_modules" not in f.parts:
                        tar.add(f, arcname=str(f.relative_to(ROOT)).replace("\\", "/"))
            else:
                tar.add(path, arcname=rel)
    return buf.getvalue()


def ensure_prerequisites(h: dict) -> None:
    r = requests.post(
        f"https://serviceusage.googleapis.com/v1/projects/{PROJECT}/services/cloudbuild.googleapis.com:enable",
        headers=h, json={}, timeout=120,
    )
    if not r.ok:
        raise RuntimeError(f"could not enable Cloud Build: {r.status_code} {r.text[:300]}")
    r = requests.post(
        "https://storage.googleapis.com/storage/v1/b",
        params={"project": PROJECT}, headers=h,
        json={"name": BUCKET, "location": REGION, "storageClass": "STANDARD"}, timeout=60,
    )
    if r.status_code not in (200, 409):  # 409 = the bucket is already there
        raise RuntimeError(f"could not create {BUCKET}: {r.status_code} {r.text[:300]}")


def submit_build(h: dict, obj: str, image: str) -> str:
    # A build MUST name a service account. The legacy
    # {number}@cloudbuild.gserviceaccount.com is still in this project's IAM policy
    # but Google no longer creates it, and a build without `serviceAccount` fails
    # with a bare "The caller does not have permission" that says nothing about
    # which account is missing. Naming one also makes the logging option required.
    body = {
        "source": {"storageSource": {"bucket": BUCKET, "object": obj}},
        "steps": [{"name": "gcr.io/cloud-builders/docker",
                   "args": ["build", "-f", "bot/Dockerfile", "-t", image, "."]}],
        "images": [image],
        "timeout": "1200s",
        "serviceAccount": f"projects/{PROJECT}/serviceAccounts/{PROJECT_NUMBER}-compute@developer.gserviceaccount.com",
        "options": {"logging": "CLOUD_LOGGING_ONLY"},
    }
    r = requests.post(f"https://cloudbuild.googleapis.com/v1/projects/{PROJECT}/builds",
                      headers=h, json=body, timeout=120)
    if not r.ok:
        raise RuntimeError(f"build submit failed: {r.status_code} {r.text[:500]}")
    return r.json()["metadata"]["build"]["id"]


def wait_for_build(build_id: str) -> None:
    for _ in range(120):
        time.sleep(10)
        b = requests.get(f"https://cloudbuild.googleapis.com/v1/projects/{PROJECT}/builds/{build_id}",
                         headers=auth(), timeout=60).json()
        status = b.get("status", "?")
        log.info(f"build {status}")
        if status in ("QUEUED", "WORKING"):
            continue
        if status != "SUCCESS":
            raise RuntimeError(f"build {status} — logs: {b.get('logUrl')}")
        return
    raise RuntimeError("build did not finish within 20 minutes")


def point_service_at(image: str) -> str:
    url = f"https://run.googleapis.com/v2/projects/{PROJECT}/locations/{REGION}/services/{SERVICE}"
    svc = requests.get(url, headers=auth(), timeout=60).json()
    svc["template"]["containers"][0]["image"] = image
    # Read-only/server-managed fields a PATCH must not echo back. Env vars and the
    # webhook config live in `template` and are carried through untouched.
    for key in ["uid", "generation", "createTime", "updateTime", "creator", "lastModifier",
                "latestReadyRevision", "latestCreatedRevision", "observedGeneration",
                "terminalCondition", "conditions", "reconciling", "etag", "trafficStatuses", "urls"]:
        svc.pop(key, None)
    svc["template"].pop("revision", None)  # let Cloud Run name the new revision
    r = requests.patch(url, headers=auth(), json=svc, timeout=120)
    if not r.ok:
        raise RuntimeError(f"cloud run patch failed: {r.status_code} {r.text[:500]}")

    for _ in range(30):
        time.sleep(10)
        svc = requests.get(url, headers=auth(), timeout=60).json()
        state = svc.get("terminalCondition", {}).get("state")
        live = svc["template"]["containers"][0]["image"]
        log.info(f"cloud run {state} {svc.get('latestReadyRevision', '').split('/')[-1]}")
        if state == "CONDITION_SUCCEEDED" and live == image:
            return svc.get("uri", "")
    raise RuntimeError("the new revision did not become ready within 5 minutes")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tag", help="image tag, e.g. v4 — bump it every deploy")
    ap.add_argument("--build-only", action="store_true", help="build the image, leave Cloud Run alone")
    args = ap.parse_args()

    image = f"{REGION}-docker.pkg.dev/{PROJECT}/bots/{SERVICE}:{args.tag}"
    h = auth()
    ensure_prerequisites(h)

    blob = build_archive()
    obj = f"{SERVICE}-{args.tag}.tar.gz"
    log.info(f"uploading {len(blob) / 1024:.0f} KB of build context as {obj}")
    r = requests.post(
        f"https://storage.googleapis.com/upload/storage/v1/b/{BUCKET}/o",
        params={"uploadType": "media", "name": obj},
        headers={"Authorization": h["Authorization"], "Content-Type": "application/gzip"},
        data=blob, timeout=300,
    )
    r.raise_for_status()

    build_id = submit_build(h, obj, image)
    log.info(f"build {build_id} submitted for {image}")
    wait_for_build(build_id)

    if args.build_only:
        log.info(f"built {image}; Cloud Run left on its current revision")
        return
    log.info(f"deployed: {point_service_at(image)}")


if __name__ == "__main__":
    main()
