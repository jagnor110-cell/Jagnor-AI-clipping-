#!/usr/bin/env python3
"""
jagnor_master_worker.py — Unified Master Execution, 4-Brain Free AI Council, Trend Discovery & Publishing Engine
Orchestration Layer: Paperclip & GitHub Actions (`clipping_company.yml`)
All-in-One Standalone Script: Built-in Social Publisher (YouTube Shorts + Instagram Graph API v22.0) & Gmail SMTP Reporter (no separate py required)

4-Brain Free AI Council (`AICouncil` — 100% Free-Tier Stack):
1. Gemini (`GEMINI_API_KEY` / `gemini-2.5-flash`)                       — Transcript & Viral Script Strategist
2. Groq (`GROQ_API_KEY` / `llama-3.3-70b-versatile`)                    — Narrative Pacing, 3s Hook & IG Captioner
3. NVIDIA NIM (`NVIDIA_API_KEY` / `nvidia/nemotron-3-super-120b-a12b`)  — YouTube Shorts Title, SEO & Hashtag Polisher
4. OpenRouter (`OPENROUTER_API_KEY` / `openrouter/free`)                — Chief Consensus Judge & Universal Fallback Router

Free Visual Engines (`--engine ai_faceless` with selectable `--art-style` & `--theme`):
- Pollinations.ai (`POLLINATIONS_API_KEY`) -> Pexels HD Portrait Photos (`PEXELS_API_KEY`) -> Clean Branded Fallback
"""

from __future__ import annotations

import argparse
import base64
import fcntl
import gc
import json
import logging
import math
import os
import random
import re
import shutil
import smtplib
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import asdict, dataclass, field
from email.message import EmailMessage
from fractions import Fraction
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("jagnor_master_worker")


# ============================================================================
# 0. BUILT-IN SOCIAL PUBLISHER, ATOMIC I/O, RATE LIMITS & GMAIL SMTP REPORTER
#    (Merged from py — YouTube Data API v3, IG Graph v22.0)
# ============================================================================

IG_GRAPH_BASE = "https://graph.facebook.com/v22.0"
YT_TOKEN_URL = "https://oauth2.googleapis.com/token"
YT_UPLOAD_INIT_URL = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}


# ============================================================================
# 1. ATOMIC JSON I/O, HTTP RETRY & GMAIL SMTP REPORTING
# ============================================================================

def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    payload = json.dumps(data, indent=2, ensure_ascii=False)

    with lock_path.open("w", encoding="utf-8") as lock_f:
        fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
        try:
            fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as tmp_f:
                    tmp_f.write(payload)
                    tmp_f.flush()
                    os.fsync(tmp_f.fileno())
                os.replace(tmp_name, path)
            except Exception:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
                raise
        finally:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)


def urlopen_with_retry(
    req: urllib.request.Request,
    timeout: int = 60,
    max_attempts: int = 3,
    base_backoff: float = 2.0,
) -> tuple[bytes, dict[str, str]]:
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                headers = {k.lower(): v for k, v in resp.headers.items()}
                return resp.read(), headers
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="replace")
            if err.code in RETRYABLE_HTTP_CODES and attempt < max_attempts:
                sleep_s = base_backoff * (2 ** (attempt - 1))
                log.warning("HTTP %d (attempt %d/%d); retrying in %.1fs...", err.code, attempt, max_attempts, sleep_s)
                time.sleep(sleep_s)
                last_exc = RuntimeError(f"HTTP {err.code}: {err_body}")
                continue
            raise RuntimeError(f"HTTP {err.code}: {err_body}") from err
        except urllib.error.URLError as err:
            if attempt < max_attempts:
                sleep_s = base_backoff * (2 ** (attempt - 1))
                log.warning("Network error %s (attempt %d/%d); retrying in %.1fs...", err, attempt, max_attempts, sleep_s)
                time.sleep(sleep_s)
                last_exc = err
                continue
            raise RuntimeError(f"Network error after {max_attempts} attempts: {err}") from err
    raise RuntimeError(f"Request failed: {last_exc}")


def format_manifest_report(
    manifest: dict[str, Any] | None,
    stage: str,
    error_msg: str | None = None,
) -> tuple[str, str]:
    """
    Builds a concise, high-signal email subject and plain-text body with status,
    4-Brain Free AI Council details, public preview links, and YouTube/Instagram receipts.
    """
    m = manifest or {}
    engine = m.get("source_mode") or m.get("engine", "unknown")
    status = "FAILED" if error_msg else m.get("status", "UNKNOWN")
    public_base = os.environ.get("PUBLIC_VIDEO_BASE_URL", "").strip().rstrip("/")

    subject = f"[Jagnor AI | {engine}] {status} (stage={stage})"
    lines: list[str] = [
        f"Pipeline Stage: {stage}",
        f"Business Engine: {engine}",
        f"Status: {status}",
        f"Timestamp (UTC): {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        "",
    ]

    if error_msg:
        lines.extend([
            "--- ERROR DETAILS ---",
            error_msg,
            "",
        ])

    if m.get("source_url"):
        lines.append(f"Source Video: {m['source_url']}")
    if m.get("product_title"):
        lines.append(f"Product Title: {m['product_title']} (${m.get('price_usd', 0):.2f})")
    if m.get("whop_checkout_url"):
        lines.append(f"Whop Checkout URL: {m['whop_checkout_url']}")
    if m.get("client_name"):
        lines.append(f"B2B Client: {m['client_name']} (Invoice {m.get('invoice_id', 'N/A')} - ${m.get('amount_due_usd', 0):.2f})")
    if m.get("council_models_used"):
        lines.append(f"AI Council Models: {', '.join(m['council_models_used'])}")
    lines.append("")

    # Public Preview Links & Clip Details
    clips = m.get("clips", [])
    if clips:
        lines.append("--- RENDERED CLIPS ---")
        for c in clips:
            mp4_name = Path(c.get("mp4_path", "")).name
            preview_url = f"{public_base}/{mp4_name}" if (public_base and mp4_name) else c.get("mp4_path", "")
            lines.append(
                f"* {c.get('clip_id')} ({c.get('duration_sec')}s | {c.get('layout_mode')}): {c.get('yt_title')}"
            )
            lines.append(f"  Hook Banner: {c.get('hook_overlay', '')}")
            lines.append(f"  Preview URL: {preview_url}")
        lines.append("")

    if m.get("promo_mp4_path") and public_base:
        lines.append(f"Promo Video URL: {public_base}/{Path(m['promo_mp4_path']).name}")
    if m.get("slide_paths") and public_base:
        slide_urls = [f"{public_base}/{Path(p).name}" for p in m["slide_paths"]]
        lines.append("Carousel Slides:")
        lines.extend(f"  - {u}" for u in slide_urls)
        lines.append("")

    # Published Receipts
    receipts = m.get("published_receipts", [])
    if receipts:
        lines.append("--- PUBLISHED RECEIPTS ---")
        for r in receipts:
            yt_id = r.get("youtube") or r.get("youtube_video_id")
            ig_id = r.get("instagram") or r.get("instagram_media_id")
            ig_car = r.get("instagram_carousel_id")
            if yt_id:
                lines.append(f"YouTube Shorts: https://youtube.com/shorts/{yt_id}")
            if ig_car:
                lines.append(f"Instagram Carousel Media ID: {ig_car}")
            elif ig_id:
                label = "Instagram Carousel Media ID" if engine == "carousel_funnel" else "Instagram Reel Media ID"
                lines.append(f"{label}: {ig_id}")
            if r.get("release_status"):
                lines.append(f"B2B Release: {r['release_status']} ({r.get('proposal_path', '')})")
        lines.append("")

    return subject, "\n".join(lines).strip() + "\n"


def send_gmail_report(
    subject: str,
    body_text: str,
    to_email: str | None = None,
    dry_run: bool = False,
) -> bool:
    """
    Sends a plain-text status report via Gmail SMTP SSL (smtp.gmail.com:465)
    using `COMPANY_GMAIL` and `GMAIL_APP_PASSWORD`.
    """
    sender = os.environ.get("COMPANY_GMAIL", "").strip()
    app_password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    recipient = (to_email or os.environ.get("REPORT_TO_EMAIL", "")).strip() or sender

    if dry_run:
        log.info("[DRY-RUN] Gmail report prepared -> To: %s | Subject: %s", recipient or "unset", subject)
        return True

    if not sender or not app_password:
        log.info("COMPANY_GMAIL / GMAIL_APP_PASSWORD not set; skipping Gmail report.")
        return False

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body_text)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
            smtp.login(sender, app_password)
            smtp.send_message(msg)
        log.info("Gmail report sent to %s (%s)", recipient, subject)
        return True
    except Exception as exc:
        log.warning("Failed to send Gmail report: %s", exc)
        return False


# ============================================================================
# 2. RATE LIMITING & LEDGER AUDIT TRAIL (`05_memory_ledger.json`)
# ============================================================================

def load_ledger(brain_dir: Path) -> tuple[dict[str, Any], Path]:
    brain_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = brain_dir / "05_memory_ledger.json"
    today_utc = time.strftime("%Y-%m-%d", time.gmtime())

    if not ledger_path.exists():
        default_data: dict[str, Any] = {
            "spend_date_utc": today_utc,
            "processed_items": [],
            "allowlisted_channels": [],
            "daily_spend_usd": 0.0,
            "daily_budget_cap_usd": 5.0,
            "publish_log": [],
            "history": [],
        }
        atomic_write_json(ledger_path, default_data)
        return default_data, ledger_path

    try:
        data = json.loads(ledger_path.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    if data.get("spend_date_utc") != today_utc:
        data["spend_date_utc"] = today_utc
        data["daily_spend_usd"] = 0.0

    data.setdefault("publish_log", [])
    return data, ledger_path


def check_platform_pacing(
    ledger_data: dict[str, Any],
    platform: str,
    max_daily_posts: int = 4,
    min_gap_hours: float = 4.0,
    skip_spacing_check: bool = False,
) -> None:
    now = time.time()
    rolling_24h = [
        entry for entry in ledger_data.get("publish_log", [])
        if entry.get("platform") == platform and (now - float(entry.get("timestamp", 0))) < 86400
    ]

    if len(rolling_24h) >= max_daily_posts:
        raise RuntimeError(
            f"RATE_LIMIT_GUARD: {platform} has already published {len(rolling_24h)}/{max_daily_posts} posts in the last 24h."
        )

    if not skip_spacing_check and rolling_24h:
        last_ts = max(float(e["timestamp"]) for e in rolling_24h)
        elapsed_hours = (now - last_ts) / 3600.0
        if elapsed_hours < min_gap_hours:
            wait_min = max(1, int((min_gap_hours - elapsed_hours) * 60))
            raise RuntimeError(
                f"SPACING_GUARD: Last {platform} post was {elapsed_hours:.2f}h ago (min gap {min_gap_hours}h). Retry in ~{wait_min}m."
            )


def record_publish_event(
    ledger_data: dict[str, Any],
    ledger_path: Path,
    platform: str,
    post_id: str,
    title_or_caption: str,
) -> None:
    ledger_data.setdefault("publish_log", []).append({
        "timestamp": int(time.time()),
        "platform": platform,
        "post_id": post_id,
        "title": title_or_caption[:80],
    })
    ledger_data["publish_log"] = ledger_data["publish_log"][-200:]
    atomic_write_json(ledger_path, ledger_data)


# ============================================================================
# 3. YOUTUBE DATA API v3 (`videos.insert` RESUMABLE UPLOAD)
# ============================================================================

def get_youtube_access_token() -> str:
    client_id = os.environ.get("YT_CLIENT_ID", "").strip()
    client_secret = os.environ.get("YT_CLIENT_SECRET", "").strip()
    refresh_token = os.environ.get("YT_REFRESH_TOKEN", "").strip()
    if not (client_id and client_secret and refresh_token):
        raise EnvironmentError("Missing YT_CLIENT_ID, YT_CLIENT_SECRET, or YT_REFRESH_TOKEN environment variables.")

    payload = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode("utf-8")

    req = urllib.request.Request(
        YT_TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    raw, _ = urlopen_with_retry(req, timeout=30)
    data = json.loads(raw.decode("utf-8"))
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"Failed to refresh YouTube OAuth token: {data}")
    return str(token)


def upload_youtube_short(
    mp4_path: Path,
    title: str,
    description: str,
    contains_synthetic_media: bool = False,
    privacy_status: str = "public",
    dry_run: bool = False,
) -> str:
    if not mp4_path.exists() or mp4_path.stat().st_size == 0:
        raise FileNotFoundError(f"YouTube MP4 missing or empty: {mp4_path}")

    file_size = mp4_path.stat().st_size
    if file_size > 256 * 1024 * 1024:
        raise ValueError(f"MP4 file exceeds 256MB safety cap ({file_size} bytes)")

    clean_title = title.strip()
    if "#shorts" not in clean_title.lower():
        clean_title = f"{clean_title[:90].strip()} #Shorts"
    clean_title = clean_title[:100]

    if dry_run:
        fake_id = f"yt_dryrun_{int(time.time())}"
        log.info("[DRY-RUN] YouTube Short uploaded: %s (%s)", clean_title, fake_id)
        return fake_id

    access_token = get_youtube_access_token()

    body_meta = {
        "snippet": {
            "title": clean_title,
            "description": description.strip(),
            "categoryId": "28",
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": bool(contains_synthetic_media),
        },
    }
    meta_bytes = json.dumps(body_meta).encode("utf-8")

    init_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Length": str(file_size),
        "X-Upload-Content-Type": "video/mp4",
    }
    init_req = urllib.request.Request(
        YT_UPLOAD_INIT_URL,
        data=meta_bytes,
        headers=init_headers,
        method="POST",
    )
    _, resp_headers = urlopen_with_retry(init_req, timeout=60)
    upload_url = resp_headers.get("location")
    if not upload_url:
        raise RuntimeError("YouTube resumable init did not return a Location header.")

    with mp4_path.open("rb") as f:
        video_bytes = f.read()

    put_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Length": str(file_size),
        "Content-Type": "video/mp4",
    }
    put_req = urllib.request.Request(upload_url, data=video_bytes, headers=put_headers, method="PUT")
    put_raw, _ = urlopen_with_retry(put_req, timeout=300)
    resp_data = json.loads(put_raw.decode("utf-8"))
    video_id = resp_data.get("id")
    if not video_id:
        raise RuntimeError(f"YouTube upload returned no video ID: {resp_data}")
    log.info("Published YouTube Short: https://youtube.com/shorts/%s", video_id)
    return str(video_id)


# ============================================================================
# 4. INSTAGRAM GRAPH API v22.0 (`REELS` & `CAROUSEL` CONTAINERS)
# ============================================================================

def _ig_api_call(url: str, method: str = "GET", params: dict[str, Any] | None = None) -> dict[str, Any]:
    if method == "GET" and params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
        data = None
    elif params:
        data = urllib.parse.urlencode(params).encode("utf-8")
    else:
        data = None

    req = urllib.request.Request(url, data=data, method=method)
    raw, _ = urlopen_with_retry(req, timeout=60)
    return json.loads(raw.decode("utf-8"))


def check_ig_publishing_quota(ig_user_id: str, access_token: str, max_api_quota: int = 20) -> int:
    res = _ig_api_call(
        f"{IG_GRAPH_BASE}/{ig_user_id}/content_publishing_limit",
        method="GET",
        params={"fields": "quota_usage,config", "access_token": access_token},
    )
    items = res.get("data", [])
    usage = int(items[0].get("quota_usage", 0)) if items else 0
    log.info("Instagram Graph API rolling 24h quota_usage: %d", usage)
    if usage >= max_api_quota:
        raise RuntimeError(f"IG_QUOTA_GUARD: quota_usage={usage} exceeds safe threshold ({max_api_quota}).")
    return usage


def poll_ig_container_until_finished(
    container_id: str,
    access_token: str,
    max_attempts: int = 20,
    base_sleep_sec: float = 6.0,
) -> None:
    for attempt in range(1, max_attempts + 1):
        res = _ig_api_call(
            f"{IG_GRAPH_BASE}/{container_id}",
            method="GET",
            params={"fields": "status_code,status", "access_token": access_token},
        )
        code = res.get("status_code", "")
        log.info("IG container %s poll %d/%d -> status_code=%s", container_id, attempt, max_attempts, code)
        if code == "FINISHED":
            return
        if code in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"IG container {container_id} failed with status_code={code}: {res}")
        time.sleep(min(base_sleep_sec * (1.25 ** (attempt - 1)), 30.0))
    raise TimeoutError(f"IG container {container_id} did not reach FINISHED after {max_attempts} polls.")


def publish_instagram_reel(
    mp4_path: Path,
    caption: str,
    dry_run: bool = False,
) -> str:
    if not mp4_path.exists() or mp4_path.stat().st_size == 0:
        raise FileNotFoundError(f"Instagram Reel MP4 missing or empty: {mp4_path}")

    if dry_run:
        fake_id = f"ig_reel_dryrun_{int(time.time())}"
        log.info("[DRY-RUN] Instagram Reel published: %s (%s)", mp4_path.name, fake_id)
        return fake_id

    ig_user_id = os.environ.get("IG_USER_ID", "").strip()
    access_token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    public_base = os.environ.get("PUBLIC_VIDEO_BASE_URL", "").strip().rstrip("/")
    if not (ig_user_id and access_token and public_base):
        raise EnvironmentError("Missing IG_USER_ID, IG_ACCESS_TOKEN, or PUBLIC_VIDEO_BASE_URL.")

    check_ig_publishing_quota(ig_user_id, access_token)
    video_url = f"{public_base}/{mp4_path.name}"

    create_res = _ig_api_call(
        f"{IG_GRAPH_BASE}/{ig_user_id}/media",
        method="POST",
        params={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption.strip(),
            "share_to_feed": "true",
            "access_token": access_token,
        },
    )
    container_id = str(create_res["id"])
    poll_ig_container_until_finished(container_id, access_token)

    pub_res = _ig_api_call(
        f"{IG_GRAPH_BASE}/{ig_user_id}/media_publish",
        method="POST",
        params={"creation_id": container_id, "access_token": access_token},
    )
    media_id = str(pub_res["id"])
    log.info("Published Instagram Reel media_id=%s", media_id)
    return media_id


def publish_instagram_carousel(
    slide_paths: list[Path],
    caption: str,
    dry_run: bool = False,
) -> str:
    if len(slide_paths) < 2 or len(slide_paths) > 10:
        raise ValueError(f"Instagram Carousel requires 2..10 slides, got {len(slide_paths)}")
    for sp in slide_paths:
        if not sp.exists() or sp.stat().st_size == 0:
            raise FileNotFoundError(f"Carousel slide missing or empty: {sp}")

    if dry_run:
        fake_id = f"ig_carousel_dryrun_{int(time.time())}"
        log.info("[DRY-RUN] Instagram Carousel (%d slides) published: %s", len(slide_paths), fake_id)
        return fake_id

    ig_user_id = os.environ.get("IG_USER_ID", "").strip()
    access_token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    public_base = os.environ.get("PUBLIC_VIDEO_BASE_URL", "").strip().rstrip("/")
    if not (ig_user_id and access_token and public_base):
        raise EnvironmentError("Missing IG_USER_ID, IG_ACCESS_TOKEN, or PUBLIC_VIDEO_BASE_URL.")

    check_ig_publishing_quota(ig_user_id, access_token)

    child_ids: list[str] = []
    for sp in slide_paths:
        img_url = f"{public_base}/{sp.name}"
        child_res = _ig_api_call(
            f"{IG_GRAPH_BASE}/{ig_user_id}/media",
            method="POST",
            params={
                "image_url": img_url,
                "is_carousel_item": "true",
                "access_token": access_token,
            },
        )
        cid = str(child_res["id"])
        poll_ig_container_until_finished(cid, access_token)
        child_ids.append(cid)

    parent_res = _ig_api_call(
        f"{IG_GRAPH_BASE}/{ig_user_id}/media",
        method="POST",
        params={
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption.strip(),
            "access_token": access_token,
        },
    )
    parent_id = str(parent_res["id"])
    poll_ig_container_until_finished(parent_id, access_token)

    pub_res = _ig_api_call(
        f"{IG_GRAPH_BASE}/{ig_user_id}/media_publish",
        method="POST",
        params={"creation_id": parent_id, "access_token": access_token},
    )
    media_id = str(pub_res["id"])
    log.info("Published Instagram Carousel media_id=%s", media_id)
    return media_id


# ============================================================================
# 5. MANIFEST ROUTER WITH PER-PLATFORM CHECKPOINTING
# ============================================================================

def _resolve_media_path(raw_path: str, public_dir: Path | None = None) -> Path:
    """Resolve media file path, falling back to public/<filename> for two-stage CI runs."""
    p = Path(raw_path)
    if p.exists():
        return p
    if public_dir is not None:
        candidate = public_dir / p.name
        if candidate.exists():
            log.info("Resolved %s via public_dir fallback -> %s", p, candidate)
            return candidate
    default_pub = Path("public") / p.name
    if default_pub.exists():
        log.info("Resolved %s via ./public fallback -> %s", p, default_pub)
        return default_pub
    return p


def process_manifest(
    manifest_path: Path,
    brain_dir: Path,
    approve_manifest: bool = False,
    platforms: set[str] = frozenset({"youtube", "instagram"}),
    max_daily_posts: int = 4,
    min_gap_hours: float = 4.0,
    skip_spacing_check: bool = False,
    apply_jitter: bool = False,
    dry_run: bool = False,
    public_dir: Path | None = None,
) -> dict[str, Any]:
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if approve_manifest and manifest.get("status") == "APPROVAL_PENDING":
        manifest["status"] = "APPROVED"
        manifest["approved_at"] = int(time.time())
        atomic_write_json(manifest_path, manifest)
        log.info("Paperclip Human-Approval Gate passed -> manifest marked APPROVED.")

    status = manifest.get("status")
    if status == "PUBLISHED":
        log.info("Manifest %s is already PUBLISHED; skipping.", manifest_path)
        return manifest
    if status != "APPROVED":
        raise PermissionError(
            f"GOVERNANCE_GATE_BLOCKED: Manifest status is '{status}' (must be 'APPROVED' before publishing)."
        )

    ledger_data, ledger_path = load_ledger(brain_dir)
    engine = manifest.get("engine", "clipping")
    published_receipts: list[dict[str, Any]] = []

    if apply_jitter and not dry_run:
        jitter_sec = random.randint(0, 10 * 60)
        log.info("Applying anti-ban random jitter sleep: %d seconds...", jitter_sec)
        time.sleep(jitter_sec)

    if engine == "digital_product":
        if not manifest.get("qa_verified", False):
            raise ValueError("QA_GATE_BLOCKED: digital_product promo MP4 is not qa_verified.")
        mp4_path = _resolve_media_path(manifest["promo_mp4_path"], public_dir)
        yt_title = manifest.get("yt_title", f"{manifest['product_title']} #Shorts")
        ig_caption = manifest.get("ig_caption", manifest["product_title"])
        checkout_url = manifest.get("whop_checkout_url", "")
        done_platforms: dict[str, str] = manifest.setdefault("published_platforms", {})

        if "youtube" in platforms and "youtube" not in done_platforms:
            check_platform_pacing(ledger_data, "youtube", max_daily_posts, min_gap_hours, skip_spacing_check)
            yt_id = upload_youtube_short(
                mp4_path,
                title=yt_title,
                description=f"{ig_caption}\n\nGet it here: {checkout_url}",
                contains_synthetic_media=False,
                dry_run=dry_run,
            )
            record_publish_event(ledger_data, ledger_path, "youtube", yt_id, yt_title)
            done_platforms["youtube"] = yt_id
            atomic_write_json(manifest_path, manifest)

        if "instagram" in platforms and "instagram" not in done_platforms:
            check_platform_pacing(ledger_data, "instagram", max_daily_posts, min_gap_hours, skip_spacing_check)
            ig_id = publish_instagram_reel(mp4_path, caption=ig_caption, dry_run=dry_run)
            record_publish_event(ledger_data, ledger_path, "instagram", ig_id, ig_caption)
            done_platforms["instagram"] = ig_id
            atomic_write_json(manifest_path, manifest)

        published_receipts.append({"item": manifest["product_title"], **done_platforms})

    elif engine in {"clipping", "ai_faceless", "raw_video_drop", "motion_story"}:
        clips = manifest.get("clips", [])
        if not clips:
            raise ValueError("No clips found in clipping manifest.")

        for clip in clips:
            if clip.get("published"):
                continue
            if not clip.get("qa_verified", False):
                raise ValueError(f"QA_GATE_BLOCKED: Clip {clip.get('clip_id')} failed qa_verified check.")

            mp4_path = _resolve_media_path(clip["mp4_path"], public_dir)
            yt_title = clip.get("yt_title") or f"Highlight {clip['clip_id']} #Shorts"
            ig_caption = clip.get("ig_caption") or "Key takeaway from today's episode. Full breakdown in bio."
            synthetic = bool(clip.get("contains_synthetic_media", False))
            clip_done: dict[str, str] = clip.setdefault("published_platforms", {})

            if "youtube" in platforms and "youtube" not in clip_done:
                check_platform_pacing(ledger_data, "youtube", max_daily_posts, min_gap_hours, skip_spacing_check)
                yt_id = upload_youtube_short(
                    mp4_path,
                    title=yt_title,
                    description=ig_caption,
                    contains_synthetic_media=synthetic,
                    dry_run=dry_run,
                )
                record_publish_event(ledger_data, ledger_path, "youtube", yt_id, yt_title)
                clip_done["youtube"] = yt_id
                atomic_write_json(manifest_path, manifest)

            if "instagram" in platforms and "instagram" not in clip_done:
                check_platform_pacing(ledger_data, "instagram", max_daily_posts, min_gap_hours, skip_spacing_check)
                ig_id = publish_instagram_reel(mp4_path, caption=ig_caption, dry_run=dry_run)
                record_publish_event(ledger_data, ledger_path, "instagram", ig_id, ig_caption)
                clip_done["instagram"] = ig_id
                atomic_write_json(manifest_path, manifest)

            if platforms.issubset(clip_done.keys()):
                clip["published"] = True
            receipt = {"clip_id": clip["clip_id"], **clip_done}
            clip["receipt"] = receipt
            published_receipts.append(receipt)
            break

    elif engine == "carousel_funnel":
        slide_paths = [_resolve_media_path(p, public_dir) for p in manifest.get("slide_paths", [])]
        ig_caption = manifest.get("ig_caption", manifest.get("topic", ""))
        done_platforms = manifest.setdefault("published_platforms", {})
        if "instagram" in platforms and "instagram" not in done_platforms:
            check_platform_pacing(ledger_data, "instagram", max_daily_posts, min_gap_hours, skip_spacing_check)
            ig_id = publish_instagram_carousel(slide_paths, caption=ig_caption, dry_run=dry_run)
            record_publish_event(ledger_data, ledger_path, "instagram", ig_id, ig_caption)
            done_platforms["instagram"] = ig_id
            atomic_write_json(manifest_path, manifest)
        published_receipts.append({"topic": manifest.get("topic"), **done_platforms})

    elif engine == "b2b_agency":
        published_receipts.append({
            "client_name": manifest.get("client_name"),
            "invoice_id": manifest.get("invoice_id"),
            "proposal_path": manifest.get("proposal_path"),
            "release_status": "CLEARED_FOR_CLIENT_DELIVERY",
        })

    if engine in {"clipping", "ai_faceless", "raw_video_drop", "motion_story"}:
        all_done = all(c.get("published", False) for c in manifest.get("clips", []))
    elif engine == "digital_product":
        all_done = platforms.issubset(manifest.get("published_platforms", {}).keys())
    elif engine == "carousel_funnel":
        all_done = ("instagram" not in platforms) or ("instagram" in manifest.get("published_platforms", {}))
    else:
        all_done = True

    if all_done:
        manifest["status"] = "PUBLISHED"
        manifest["published_at"] = int(time.time())
    manifest["published_receipts"] = published_receipts
    atomic_write_json(manifest_path, manifest)
    return manifest


# ============================================================================
# 1. UNIVERSAL DATA STRUCTURES & COMPANY BRAIN (`brain/`)
# ============================================================================

@dataclass
class WordToken:
    word: str
    start: float
    end: float
    speaker: str = "SPEAKER_00"


@dataclass
class IndexedSegment:
    segment_id: int
    speaker: str
    start: float
    end: float
    text: str
    words: list[WordToken]


@dataclass
class ClipSpec:
    clip_id: str
    start_segment_id: int
    end_segment_id: int
    start_sec: float
    end_sec: float
    duration_sec: float
    mp4_path: str
    layout_mode: str
    qa_verified: bool
    yt_title: str = ""
    ig_caption: str = ""
    hook_overlay: str = ""
    council_score: float = 0.0
    council_models_used: list[str] = field(default_factory=list)
    contains_synthetic_media: bool = False
    source_url: str = ""


@dataclass
class CompanyBrain:
    brain_dir: Path
    spend_date_utc: str = ""
    identity_icp: str = ""
    brand_style: str = ""
    offers_pricing: str = ""
    sops_guardrails: str = ""
    processed_items: set[str] = field(default_factory=set)
    allowlisted_channels: set[str] = field(default_factory=set)
    daily_spend_usd: float = 0.0
    daily_budget_cap_usd: float = 5.0
    ledger_path: Path | None = None

    @classmethod
    def load(cls, brain_dir: Path | None) -> "CompanyBrain":
        today_utc = time.strftime("%Y-%m-%d", time.gmtime())
        if brain_dir is None:
            return cls(brain_dir=Path("."), spend_date_utc=today_utc)
        brain_dir.mkdir(parents=True, exist_ok=True)

        def _read_md(name: str, default: str) -> str:
            p = brain_dir / name
            if not p.exists():
                p.write_text(default, encoding="utf-8")
            return p.read_text(encoding="utf-8")

        icp = _read_md("01_identity_icp.md", "# Identity & ICP\nTarget high-value digital buyers and AI/tech enthusiasts.\n")
        style = _read_md("02_brand_style.md", "# Brand Style\nPrimary: #0F172A | Accent: #38BDF8 | Highlight: #FACC15\n")
        pricing = _read_md("03_offers_pricing.md", "# Offers & Pricing\n- Pro Bundle: $17\n- B2B Automation Retainer: $1,500\n")
        sops = _read_md("04_sops_guardrails.md", "# SOPs & Guardrails\nMax 4 posts/day. Human approval required before publish.\n")

        ledger_path = brain_dir / "05_memory_ledger.json"
        if not ledger_path.exists():
            default_ledger = {
                "spend_date_utc": today_utc,
                "processed_items": [],
                "allowlisted_channels": [],
                "daily_spend_usd": 0.0,
                "daily_budget_cap_usd": 5.0,
                "publish_log": [],
                "history": [],
            }
            atomic_write_json(ledger_path, default_ledger)

        try:
            data = json.loads(ledger_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}

        if data.get("spend_date_utc") != today_utc:
            data["spend_date_utc"] = today_utc
            data["daily_spend_usd"] = 0.0
            atomic_write_json(ledger_path, data)

        items = set(data.get("processed_items", [])) | set(data.get("processed_urls", []))
        return cls(
            brain_dir=brain_dir,
            spend_date_utc=today_utc,
            identity_icp=icp,
            brand_style=style,
            offers_pricing=pricing,
            sops_guardrails=sops,
            processed_items=items,
            allowlisted_channels=set(data.get("allowlisted_channels", [])),
            daily_spend_usd=float(data.get("daily_spend_usd", 0.0)),
            daily_budget_cap_usd=float(data.get("daily_budget_cap_usd", 5.0)),
            ledger_path=ledger_path,
        )

    def check_pre_flight(self, item_key: str, estimated_cost_usd: float = 0.10) -> None:
        if item_key in self.processed_items:
            raise ValueError(f"DEAD_LETTER: Item already processed in Company Brain ledger: {item_key}")
        if (self.daily_spend_usd + estimated_cost_usd) > self.daily_budget_cap_usd:
            raise RuntimeError(
                f"DEAD_LETTER: Budget cap exceeded (${self.daily_spend_usd:.2f} + ${estimated_cost_usd:.2f} > ${self.daily_budget_cap_usd:.2f})"
            )

    def record_completion(self, item_key: str, engine: str, cost_usd: float, summary: dict[str, Any]) -> None:
        today_utc = time.strftime("%Y-%m-%d", time.gmtime())
        if self.spend_date_utc != today_utc:
            self.spend_date_utc = today_utc
            self.daily_spend_usd = 0.0

        self.processed_items.add(item_key)
        self.daily_spend_usd = round(self.daily_spend_usd + cost_usd, 4)
        if self.ledger_path is None:
            return
        try:
            data = json.loads(self.ledger_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        data["spend_date_utc"] = self.spend_date_utc
        data["processed_items"] = sorted(self.processed_items)
        data["allowlisted_channels"] = sorted(self.allowlisted_channels)
        data["daily_spend_usd"] = self.daily_spend_usd
        data["daily_budget_cap_usd"] = self.daily_budget_cap_usd
        data.setdefault("publish_log", [])
        history = list(data.get("history", []))
        history.append({
            "timestamp": int(time.time()),
            "engine": engine,
            "item_key": item_key,
            "cost_usd": cost_usd,
            "summary": summary,
        })
        data["history"] = history[-100:]
        atomic_write_json(self.ledger_path, data)


# ============================================================================
# 2. THE 4-BRAIN FREE AI COUNCIL (GEMINI -> GROQ -> NVIDIA NIM -> OPENROUTER)
# ============================================================================

ART_STYLE_PROMPTS: dict[str, str] = {
    "dark_cinematic": "dark moody cinematic photography, dramatic rim lighting, ultra detailed 8k, shallow depth of field, no text",
    "anime": "high-budget Japanese anime art style, vibrant cel shading, dynamic cinematic lighting, Makoto Shinkai aesthetic, no text",
    "cyberpunk": "futuristic cyberpunk neon noir aesthetic, glowing cyan and magenta reflections, rain-slicked sci-fi lighting, ultra detailed, no text",
    "3d_pixar": "stylized 3D animated film still, Pixar lighting quality, expressive cinematic render, global illumination, no text",
    "comic_book": "bold graphic novel comic book illustration, inked outlines, dramatic halftone shading, vibrant high-contrast colors, no text",
    "minimalist_sketch": "clean editorial minimalist ink and charcoal sketch illustration on dark slate paper, gold accent highlights, modern aesthetic, no text",
    "oil_painting": "dramatic classical oil painting, rich visible brushstrokes, chiaroscuro lighting, museum masterpiece aesthetic, no text",
}


class AICouncil:
    """
    Passes each video or product brief sequentially through 4 free-tier AI brains:
      Stage 1 (Gemini)     : Long-Context Transcript & Viral Script Strategist
      Stage 2 (Groq)       : Narrative Pacing, Viral 3-Second Hook & IG Captioner
      Stage 3 (NVIDIA NIM) : High-CTR YouTube Shorts Title, SEO & Hashtag Polisher
      Stage 4 (OpenRouter) : Chief Consensus Judge (`openrouter/free`) & Universal Fallback Router
    """

    def __init__(self) -> None:
        self.gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self.groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        self.nvidia_key = os.environ.get("NVIDIA_API_KEY", "").strip()
        self.openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        self.models_called: list[str] = []

    def _call_openai_compatible(
        self,
        url: str,
        api_key: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        extra_headers: dict[str, str] | None = None,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "JagnorAICouncil/2.0",
            **(extra_headers or {}),
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.35,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        raw, _ = urlopen_with_retry(req, timeout=45, max_attempts=2)
        data = json.loads(raw.decode("utf-8"))
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"Empty choices from {url} ({model}): {data}")
        return str(choices[0].get("message", {}).get("content") or "").strip()

    def _call_gemini_native(self, system_prompt: str, user_prompt: str) -> str:
        primary_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        for model in dict.fromkeys([primary_model, "gemini-2.5-flash", "gemini-2.0-flash"]):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_key}"
            payload = {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"parts": [{"text": user_prompt}]}],
                "generationConfig": {"temperature": 0.35},
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                raw, _ = urlopen_with_retry(req, timeout=45, max_attempts=2)
                data = json.loads(raw.decode("utf-8"))
                candidates = data.get("candidates") or []
                if candidates:
                    return str(candidates[0]["content"]["parts"][0]["text"]).strip()
            except Exception as exc:
                log.debug("Gemini model %s attempt failed: %s", model, exc)
                continue
        raise RuntimeError("All native Gemini model endpoints failed.")

    def _call_groq_native(self, system_prompt: str, user_prompt: str) -> str:
        """Calls Groq's ultra-fast free-tier OpenAI-compatible endpoint (`GROQ_API_KEY`)."""
        primary_model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
        for g_model in dict.fromkeys([primary_model, "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]):
            try:
                return self._call_openai_compatible(
                    "https://api.groq.com/openai/v1/chat/completions",
                    self.groq_key,
                    g_model,
                    system_prompt,
                    user_prompt,
                )
            except Exception as exc:
                log.debug("Groq model %s attempt failed: %s", g_model, exc)
                continue
        raise RuntimeError("All native Groq model endpoints failed.")

    def _call_nvidia_native(self, system_prompt: str, user_prompt: str) -> str:
        """Calls NVIDIA NIM OpenAI-compatible endpoint (`NVIDIA_API_KEY`)."""
        nv_url = os.environ.get("NVIDIA_API_URL", "https://integrate.api.nvidia.com/v1/chat/completions").strip()
        primary_model = os.environ.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b")
        fallback_models = [
            primary_model,
            "nvidia/nemotron-3-super-120b-a12b",
            "nvidia/nemotron-3.5-lightning-30b-a3b",
            "nvidia/llama-3.1-nemotron-70b-instruct",
        ]
        for nv_model in dict.fromkeys(fallback_models):
            try:
                return self._call_openai_compatible(
                    nv_url,
                    self.nvidia_key,
                    nv_model,
                    system_prompt,
                    user_prompt,
                )
            except Exception as exc:
                log.debug("NVIDIA NIM model %s attempt failed: %s", nv_model, exc)
                continue
        raise RuntimeError("All native NVIDIA NIM model endpoints failed.")

    def invoke_stage(self, provider: str, system_prompt: str, user_prompt: str) -> str | None:
        openrouter_candidates = {
            "gemini": ["google/gemini-2.5-flash", "openrouter/free", "openrouter/auto"],
            "groq": ["meta-llama/llama-3.3-70b-instruct:free", "openrouter/free", "openrouter/auto"],
            "nvidia": ["nvidia/llama-3.1-nemotron-70b-instruct", "openrouter/free", "openrouter/auto"],
            "openrouter": [os.environ.get("OPENROUTER_JUDGE_MODEL", "openrouter/free"), "openrouter/auto"],
        }

        try:
            if provider == "gemini" and self.gemini_key:
                res = self._call_gemini_native(system_prompt, user_prompt)
                self.models_called.append("gemini-native")
                return res
            if provider == "groq" and self.groq_key:
                res = self._call_groq_native(system_prompt, user_prompt)
                self.models_called.append("groq-native")
                return res
            if provider == "nvidia" and self.nvidia_key:
                res = self._call_nvidia_native(system_prompt, user_prompt)
                self.models_called.append("nvidia-nim-native")
                return res
        except Exception as native_exc:
            log.warning("Native [%s] API failed (%s); falling back to OpenRouter if configured...", provider, native_exc)

        if self.openrouter_key:
            for or_model in dict.fromkeys(openrouter_candidates.get(provider, ["openrouter/free", "openrouter/auto"])):
                try:
                    res = self._call_openai_compatible(
                        "https://openrouter.ai/api/v1/chat/completions",
                        self.openrouter_key,
                        or_model,
                        system_prompt,
                        user_prompt,
                        extra_headers={
                            "HTTP-Referer": "https://github.com/jagnor110-cell",
                            "X-Title": "Jagnor Free AI Council",
                        },
                    )
                    self.models_called.append(f"openrouter:{or_model}")
                    return res
                except Exception as or_exc:
                    log.debug("OpenRouter model %s failed (%s); trying next...", or_model, or_exc)
                    continue

        return None

    @staticmethod
    def _extract_json_dict(raw_text: str | None) -> dict[str, Any] | None:
        if not raw_text:
            return None
        cleaned = re.sub(r"```(?:json)?", "", raw_text, flags=re.IGNORECASE).replace("```", "").strip()
        decoder = json.JSONDecoder()
        for idx, ch in enumerate(cleaned):
            if ch in {"{", "["}:
                try:
                    obj, _ = decoder.raw_decode(cleaned[idx:])
                    if isinstance(obj, dict):
                        return obj
                    if isinstance(obj, list):
                        return {"clips": obj}
                except Exception:
                    continue
        return None

    @staticmethod
    def _clamp_window_to_valid_duration(
        s_id: int,
        e_id: int,
        seg_map: dict[int, IndexedSegment],
        min_dur: float = 12.0,
        max_dur: float = 58.0,
    ) -> tuple[int, int] | None:
        if not seg_map:
            return None
        all_ids = sorted(seg_map.keys())
        s_id = max(all_ids[0], min(s_id, all_ids[-1]))
        e_id = max(s_id, min(e_id, all_ids[-1]))
        if s_id not in seg_map:
            s_id = min(all_ids, key=lambda k: abs(k - s_id))
        if e_id not in seg_map:
            e_id = min(all_ids, key=lambda k: abs(k - e_id))
        if e_id < s_id:
            e_id = s_id

        while e_id > s_id and (seg_map[e_id].end - seg_map[s_id].start) > max_dur:
            e_id -= 1
            while e_id > s_id and e_id not in seg_map:
                e_id -= 1

        while e_id < all_ids[-1] and (seg_map[e_id].end - seg_map[s_id].start) < min_dur:
            next_id = e_id + 1
            while next_id <= all_ids[-1] and next_id not in seg_map:
                next_id += 1
            if next_id > all_ids[-1]:
                break
            if (seg_map[next_id].end - seg_map[s_id].start) > max_dur:
                break
            e_id = next_id

        return s_id, e_id

    def run_6_brain_clip_council(
        self,
        segments: list[IndexedSegment],
        brain: CompanyBrain,
        max_clips: int = 3,
    ) -> list[dict[str, Any]]:
        """Runs the 4-Brain Free AI Council (Gemini -> Groq -> NVIDIA NIM -> OpenRouter) for clipping."""
        deterministic_windows = select_candidate_windows(segments, max_clips=max_clips)
        if not deterministic_windows:
            return []

        seg_map = {s.segment_id: s for s in segments}
        transcript_digest = "\n".join(
            f"[{s.segment_id}] ({s.start:.1f}s..{s.end:.1f}s) {s.text}"
            for s in segments[:180]
        )

        # Stage 1: GEMINI — Hook Window Discovery
        gemini_out = self.invoke_stage(
            "gemini",
            "You are Stage 1 (Gemini Hook Analyst) in a 4-AI free video clipping council. Pick high-retention 30-55s segment ranges by integer segment_id.",
            f"Brand ICP:\n{brain.identity_icp}\n\nIndexed Transcript:\n{transcript_digest}\n\n"
            f"Propose up to {max_clips} clip windows as JSON: {{\"clips\": [{{\"start_segment_id\": int, \"end_segment_id\": int, \"reason\": str}}]}}",
        )

        # Stage 2: GROQ — Narrative Pacing, Viral 3-Second Hook & Instagram Caption
        groq_out = self.invoke_stage(
            "groq",
            "You are Stage 2 (Groq Viral Director). Refine the windows to start on a bold hook sentence and end cleanly (30-55s), adding a <=6-word ALL-CAPS `hook_overlay` and an engaging `ig_caption` (no raw URLs).",
            f"Brand Style:\n{brain.brand_style}\n\nTranscript:\n{transcript_digest}\n\nGemini Proposal:\n{gemini_out or json.dumps(deterministic_windows)}\n\n"
            "Return JSON with start_segment_id, end_segment_id, hook_overlay, and ig_caption.",
        )

        # Stage 3: NVIDIA NIM — YouTube Shorts High-CTR Title, SEO & Hashtags
        nvidia_out = self.invoke_stage(
            "nvidia",
            "You are Stage 3 (NVIDIA Nemotron Title & Retention Polisher). Add a high-CTR `yt_title` (<=60 chars including #Shorts), tighten `hook_overlay`, and add 3 niche hashtags to `ig_caption`.",
            f"Groq Draft:\n{groq_out or gemini_out or json.dumps(deterministic_windows)}\n\n"
            "Return JSON preserving start_segment_id and end_segment_id with polished hook_overlay, yt_title, and ig_caption.",
        )

        # Stage 4: OPENROUTER — Chief Consensus Judge & Final Schema Validator
        judge_out = self.invoke_stage(
            "openrouter",
            "You are Stage 4 (OpenRouter Chief Consensus Judge). Merge all 3 AI drafts into final strict JSON.",
            f"Gemini:\n{gemini_out}\nGroq:\n{groq_out}\nNVIDIA NIM:\n{nvidia_out}\n\n"
            "Output ONLY valid JSON: {\"clips\": [{\"start_segment_id\": int, \"end_segment_id\": int, "
            "\"hook_overlay\": str, \"yt_title\": str, \"ig_caption\": str, \"council_score\": float}]}",
        )

        parsed = (
            self._extract_json_dict(judge_out)
            or self._extract_json_dict(nvidia_out)
            or self._extract_json_dict(groq_out)
            or self._extract_json_dict(gemini_out)
        )

        final_specs: list[dict[str, Any]] = []
        if parsed and isinstance(parsed.get("clips"), list):
            for item in parsed["clips"]:
                if not isinstance(item, dict):
                    continue
                try:
                    raw_s = int(item["start_segment_id"])
                    raw_e = int(item["end_segment_id"])
                except Exception:
                    continue
                clamped = self._clamp_window_to_valid_duration(raw_s, raw_e, seg_map)
                if clamped is None:
                    continue
                s_id, e_id = clamped
                final_specs.append({
                    "start_segment_id": s_id,
                    "end_segment_id": e_id,
                    "hook_overlay": str(item.get("hook_overlay") or "WATCH THIS BREAKDOWN")[:42].upper(),
                    "yt_title": str(item.get("yt_title") or f"{seg_map[s_id].text[:48]} #Shorts")[:100],
                    "ig_caption": str(item.get("ig_caption") or f"{seg_map[s_id].text[:90]} — full details in bio."),
                    "council_score": float(item.get("council_score") or 9.5),
                })

        if not final_specs:
            for s_id, e_id in deterministic_windows:
                hook_text = seg_map[s_id].text[:48].strip() or "AI Automation Breakdown"
                final_specs.append({
                    "start_segment_id": s_id,
                    "end_segment_id": e_id,
                    "hook_overlay": " ".join(hook_text.split()[:5]).upper(),
                    "yt_title": f"{hook_text} #Shorts",
                    "ig_caption": f"{hook_text} — full breakdown via link in bio.",
                    "council_score": 8.5,
                })

        log.info(
            "4-Brain Free AI Council completed (%d models active: %s) -> selected %d clips.",
            len(self.models_called),
            ", ".join(self.models_called) if self.models_called else "deterministic-fallback",
            len(final_specs[:max_clips]),
        )
        return final_specs[:max_clips]

    def run_6_brain_copy_council(
        self,
        title_or_topic: str,
        raw_notes: str,
        brain: CompanyBrain,
    ) -> dict[str, Any]:
        s1 = self.invoke_stage(
            "gemini",
            "You are Stage 1 (Gemini Market Analyst). Extract the 3 highest-value takeaways for this topic/product.",
            f"ICP:\n{brain.identity_icp}\nTopic: {title_or_topic}\nNotes: {raw_notes}",
        )
        s2 = self.invoke_stage(
            "groq",
            "You are Stage 2 (Groq Viral Copywriter). Turn the 3 takeaways into crisp <=12-word bullets, add a 5-word hook badge, and write an engaging Instagram caption.",
            f"Gemini Draft:\n{s1 or raw_notes}",
        )
        s3 = self.invoke_stage(
            "nvidia",
            "You are Stage 3 (NVIDIA Nemotron SEO Polisher). Add a <=60-char YouTube Shorts title with #Shorts and 3 targeted hashtags to the Instagram caption.",
            f"Groq Copy:\n{s2 or raw_notes}",
        )
        s4 = self.invoke_stage(
            "openrouter",
            "You are Stage 4 (OpenRouter Chief Consensus Judge). Output strict JSON only.",
            f"Synthesize:\nGemini: {s1}\nGroq: {s2}\nNVIDIA NIM: {s3}\n"
            "Output ONLY JSON: {\"hook_badge\": str, \"points\": [str, str, str], \"yt_title\": str, \"ig_caption\": str}",
        )
        parsed = (
            self._extract_json_dict(s4)
            or self._extract_json_dict(s3)
            or self._extract_json_dict(s2)
            or self._extract_json_dict(s1)
            or {}
        )
        default_pts = [p.strip() for p in raw_notes.split(";") if p.strip()] or [
            "Centralize brand SOPs in a shared Company Brain.",
            "Pass every video through the 4-Brain Free AI Council.",
            "Gate every public post behind human approval.",
        ]
        pts = parsed.get("points") if isinstance(parsed.get("points"), list) and len(parsed["points"]) >= 3 else default_pts
        return {
            "hook_badge": str(parsed.get("hook_badge") or "AI COUNCIL VERIFIED")[:36].upper(),
            "points": [str(p) for p in pts[:3]],
            "yt_title": str(parsed.get("yt_title") or f"{title_or_topic[:48]} #Shorts")[:100],
            "ig_caption": str(parsed.get("ig_caption") or f"{title_or_topic} — full breakdown via the link in bio."),
            "council_models_used": list(self.models_called),
        }

    def run_6_brain_faceless_script(
        self,
        topic: str,
        brain: CompanyBrain,
        art_style: str = "dark_cinematic",
        theme: str = "AI & Tech Automation",
        character_desc: str = "",
        language_hint: str = "English",
    ) -> dict[str, Any]:
        """
        Passes a topic, theme, and art_style through the 4-Brain Free AI Council to produce
        a cohesive 5-scene motion-animated faceless Short script.
        """
        style_desc = ART_STYLE_PROMPTS.get(art_style, ART_STYLE_PROMPTS["dark_cinematic"])

        s1 = self.invoke_stage(
            "gemini",
            "You are Stage 1 (Gemini Viral Strategist). Outline a 5-scene 35-second faceless vertical video script tailored to the requested theme and art style.",
            f"Theme: {theme}\nArt Style: {art_style} ({style_desc})\nTopic: {topic}\nLanguage: {language_hint}\n"
            f"Character/Subject Lock: {character_desc or 'Topic-matched consistent visual subject'}\n"
            f"ICP:\n{brain.identity_icp}\n"
            "Give 5 short scenes with narration (12-16 words each), a vivid visual_prompt matching the Art Style, and a 2-3 word stock_keywords phrase for each scene.",
        )
        s2 = self.invoke_stage(
            "groq",
            "You are Stage 2 (Groq Viral Script Director). Tighten all 5 scenes so the first 3 seconds hook hard, every narration sentence flows cleanly, and add a <=6-word ALL-CAPS `hook_overlay` + engaging `ig_caption`.",
            f"Theme: {theme} | Art Style: {art_style}\nGemini Outline:\n{s1 or topic}",
        )
        s3 = self.invoke_stage(
            "nvidia",
            "You are Stage 3 (NVIDIA Nemotron SEO & Retention Polisher). Add a <=60-char `yt_title` with #Shorts, polish visual_prompt consistency for the chosen Art Style, and add 3 niche hashtags to `ig_caption`.",
            f"Art Style: {art_style} ({style_desc})\nGroq Draft:\n{s2 or topic}",
        )
        s4 = self.invoke_stage(
            "openrouter",
            "You are Stage 4 (OpenRouter Chief Consensus Judge). Output ONLY strict JSON.",
            f"Merge all 3 drafts:\nGemini:{s1}\nGroq:{s2}\nNVIDIA:{s3}\n"
            'Output ONLY valid JSON: {"hook_overlay": str, "yt_title": str, "ig_caption": str, '
            '"scenes": [{"narration": str, "visual_prompt": str, "stock_keywords": str}]} (exactly 5 scenes).',
        )
        parsed = (
            self._extract_json_dict(s4)
            or self._extract_json_dict(s3)
            or self._extract_json_dict(s2)
            or self._extract_json_dict(s1)
            or {}
        )
        raw_scenes = parsed.get("scenes")
        scenes: list[dict[str, str]] = []
        if isinstance(raw_scenes, list):
            for sc in raw_scenes[:5]:
                if isinstance(sc, dict) and sc.get("narration"):
                    scenes.append({
                        "narration": str(sc["narration"]).strip(),
                        "visual_prompt": str(sc.get("visual_prompt") or f"{topic}, {theme}").strip(),
                        "stock_keywords": str(sc.get("stock_keywords") or f"{theme} {topic}")[:40].strip(),
                    })

        if len(scenes) < 3:
            scenes = [
                {
                    "narration": f"Most people still overlook how {topic} is reshaping {theme} right now.",
                    "visual_prompt": f"dramatic opening scene representing {topic} in {theme}",
                    "stock_keywords": f"{theme} futuristic",
                },
                {
                    "narration": "The shift starts when one clear system replaces hours of repetitive manual work.",
                    "visual_prompt": f"glowing command hub illustrating {topic} workflow",
                    "stock_keywords": "technology workspace neon",
                },
                {
                    "narration": "Four specialized AI models collaborate in sequence to write, sharpen, and verify every angle.",
                    "visual_prompt": f"four luminous energy nodes connecting into a single beam, {theme}",
                    "stock_keywords": "abstract digital network",
                },
                {
                    "narration": "Every visual is locked to one cohesive aesthetic so viewers recognize your brand instantly.",
                    "visual_prompt": f"sleek futuristic studio screen displaying bold art frames, {theme}",
                    "stock_keywords": "creative studio lighting",
                },
                {
                    "narration": "Build the engine once, review the output, and let consistency compound every single week.",
                    "visual_prompt": f"rising golden horizon over futuristic cityscape symbolizing growth, {theme}",
                    "stock_keywords": "city skyline sunset",
                },
            ]

        return {
            "hook_overlay": str(parsed.get("hook_overlay") or topic[:36]).upper()[:42],
            "yt_title": str(parsed.get("yt_title") or f"{topic[:48]} #Shorts")[:100],
            "ig_caption": str(parsed.get("ig_caption") or f"{topic} — built automatically with our free AI studio. Follow for more! #AI #Automation #Shorts"),
            "scenes": scenes,
            "art_style": art_style,
            "theme": theme,
            "council_models_used": list(self.models_called),
        }



    def run_motion_story_council(
        self,
        topic: str,
        brain: CompanyBrain,
        art_style: str = "dark_cinematic",
        theme: str = "Universal Storytelling",
        character_desc: str = "",
        language_hint: str = "English",
    ) -> dict[str, Any]:
        """
        4-Brain Free AI Council for `--engine motion_story`:
        Generates topic-accurate visual_world (space/ocean/tech_ai/finance/history_myth/nature),
        per-scene visual prompts & stock keywords, plus 5 animated 2D motion-graphic scenes
        with clean short stats and auto-sized source quotes.
        """
        style_desc = ART_STYLE_PROMPTS.get(art_style, ART_STYLE_PROMPTS["dark_cinematic"])
        char_hint = character_desc.strip() or f"Topic-accurate central subject or protagonist for {topic}"
        s1 = self.invoke_stage(
            "gemini",
            "You are Stage 1 (Gemini Story Architect). Write a gripping 5-scene 45-second animated explainer/story script that is 100% visually accurate to the topic.",
            f"Topic: {topic}\nTheme: {theme}\nArt Style: {art_style} ({style_desc})\nLanguage: {language_hint}\n"
            f"Subject/Character Hint: {char_hint}\nICP:\n{brain.identity_icp}\n"
            "Pick visual_world from [space, ocean, tech_ai, finance, history_myth, nature]. "
            "Design 5 scenes using scene_type in [hero_intro, scale_comparison, action_flight, source_quote, zoom_callout]. "
            "For EVERY scene include: narration (14-20 words), top_label (<=4 words), visual_prompt (accurate to the topic & art style, no text), "
            "stock_keywords (2-4 concrete real-world nouns spoken in THIS scene narration for exact Wikimedia/Pexels photo matching, unique per scene), metric_value (number), metric_unit (SHORT 1-2 words like KM, AU, YEARS, USD, %, X), "
            "quote_title, quote_text (1-2 crisp sentences), and callout_label (<=3 words).",
        )
        s2 = self.invoke_stage(
            "groq",
            "You are Stage 2 (Groq Viral Storyteller). Sharpen the 3-second hook, keep every visual_prompt strictly accurate to the exact topic, end with a comment question, and add `hook_overlay` + `ig_caption`.",
            f"Topic: {topic} | Theme: {theme} | Language: {language_hint}\nGemini Draft:\n{s1 or topic}",
        )
        s3 = self.invoke_stage(
            "nvidia",
            "You are Stage 3 (NVIDIA Nemotron Polish & SEO). Add a <=60-char `yt_title` with #Shorts, keep metric_unit <= 8 chars (e.g. AU, KM, YEARS, B KM), and add 3 hashtags to `ig_caption`.",
            f"Groq Draft:\n{s2 or topic}",
        )
        s4 = self.invoke_stage(
            "openrouter",
            "You are Stage 4 (OpenRouter Chief Consensus Judge). Output ONLY strict valid JSON.",
            f"Merge all 3 drafts:\nGemini:{s1}\nGroq:{s2}\nNVIDIA:{s3}\n"
            'Output ONLY valid JSON: {"hook_overlay": str, "yt_title": str, "ig_caption": str, '
            '"visual_world": str, '
            '"character": {"name": str, "archetype": str, "primary_hex": str, "accent_hex": str, "skin_hex": str, "aura_hex": str}, '
            '"scenes": [{"scene_type": str, "narration": str, "top_label": str, "visual_prompt": str, "stock_keywords": str, '
            '"metric_value": float, "metric_unit": str, "quote_title": str, "quote_text": str, "callout_label": str}]} '
            "(exactly 5 scenes).",
        )
        parsed = (
            self._extract_json_dict(s4)
            or self._extract_json_dict(s3)
            or self._extract_json_dict(s2)
            or self._extract_json_dict(s1)
            or {}
        )

        def _safe_hex(val: Any, default: str) -> str:
            s = str(val or "").strip()
            return s if re.fullmatch(r"#[0-9a-fA-F]{6}", s) else default

        def _clean_unit(val: Any) -> str:
            raw = re.sub(r"\(.*?\)", "", str(val or "")).strip()
            parts = raw.split()[:2]
            out = " ".join(parts).upper()
            return out if len(out) <= 10 else parts[0][:10].upper()

        # Infer visual_world accurately from topic/theme if LLM omits or returns unknown value
        low_ctx = f"{topic} {theme} {character_desc}".lower()
        valid_worlds = {"space", "ocean", "tech_ai", "finance", "history_myth", "nature"}
        v_world = str(parsed.get("visual_world") or "").strip().lower()
        if v_world not in valid_worlds:
            if any(k in low_ctx for k in ("space", "voyager", "planet", "mars", "star", "orbit", "galaxy", "nasa", "moon", "sun", "universe", "rocket")):
                v_world = "space"
            elif any(k in low_ctx for k in ("ocean", "sea", "mariana", "trench", "submarine", "whale", "deep water", "titanic")):
                v_world = "ocean"
            elif any(k in low_ctx for k in ("ai", "agent", "robot", "code", "algorithm", "software", "tech", "cyber", "computer")):
                v_world = "tech_ai"
            elif any(k in low_ctx for k in ("money", "stock", "billion", "wealth", "finance", "crypto", "business", "economy", "gold", "market")):
                v_world = "finance"
            elif any(k in low_ctx for k in ("myth", "ramayan", "hanuman", "king", "empire", "roman", "pyramid", "war", "ancient", "history", "god")):
                v_world = "history_myth"
            else:
                v_world = "nature"

        raw_char = parsed.get("character") if isinstance(parsed.get("character"), dict) else {}
        character = {
            "name": str(raw_char.get("name") or topic[:24])[:32],
            "archetype": str(raw_char.get("archetype") or "hero").lower(),
            "primary_hex": _safe_hex(raw_char.get("primary_hex"), "#D94A38"),
            "accent_hex": _safe_hex(raw_char.get("accent_hex"), "#F5C451"),
            "skin_hex": _safe_hex(raw_char.get("skin_hex"), "#C68642"),
            "aura_hex": _safe_hex(raw_char.get("aura_hex"), "#38BDF8"),
            "visual_world": v_world,
        }

        default_types = ["hero_intro", "scale_comparison", "action_flight", "source_quote", "zoom_callout"]
        raw_scenes = parsed.get("scenes")
        scenes: list[dict[str, Any]] = []
        if isinstance(raw_scenes, list):
            for idx, sc in enumerate(raw_scenes[:5]):
                if isinstance(sc, dict) and sc.get("narration"):
                    st = str(sc.get("scene_type") or default_types[idx % 5]).lower()
                    if st not in set(default_types):
                        st = default_types[idx % 5]
                    try:
                        m_val = float(sc.get("metric_value") or 100)
                    except Exception:
                        m_val = 100.0
                    unit = _clean_unit(sc.get("metric_unit") or "X")
                    scenes.append({
                        "scene_type": st,
                        "narration": str(sc["narration"]).strip(),
                        "top_label": _trim_words(str(sc.get("top_label") or topic), 30).upper(),
                        "visual_prompt": str(sc.get("visual_prompt") or f"{topic}, {theme}, {art_style}").strip(),
                        "stock_keywords": str(sc.get("stock_keywords") or f"{v_world.replace('_', ' ')} {topic}")[:42].strip(),
                        "metric_value": m_val,
                        "metric_unit": unit,
                        "quote_title": _trim_words(str(sc.get("quote_title") or theme), 34),
                        "quote_text": str(sc.get("quote_text") or sc["narration"]).strip()[:200],
                        "callout_label": _trim_words(str(sc.get("callout_label") or f"{int(m_val)} {unit}"), 22).upper(),
                    })

        if len(scenes) < 3:
            scenes = [
                {
                    "scene_type": "hero_intro",
                    "narration": f"Most people never realize the true scale behind {topic} until you see it visualized.",
                    "top_label": _trim_words(topic, 28).upper(),
                    "visual_prompt": f"cinematic establishing shot of {topic}, {theme}",
                    "stock_keywords": f"{v_world.replace('_', ' ')} dramatic",
                    "metric_value": 3.0,
                    "metric_unit": "X SCALE",
                    "quote_title": theme.upper(),
                    "quote_text": "",
                    "callout_label": "ORIGIN POINT",
                },
                {
                    "scene_type": "scale_comparison",
                    "narration": "Step by step, the numbers climb far beyond what our brains can picture at a glance.",
                    "top_label": "THE REAL SCALE",
                    "visual_prompt": f"epic scale comparison visual for {topic}, {theme}",
                    "stock_keywords": f"{v_world.replace('_', ' ')} vast",
                    "metric_value": 1000.0,
                    "metric_unit": "KM",
                    "quote_title": theme.upper(),
                    "quote_text": "",
                    "callout_label": "1000 KM",
                },
                {
                    "scene_type": "action_flight",
                    "narration": "At the defining moment of this journey, momentum carries it past every known boundary.",
                    "top_label": "BEYOND THE LIMIT",
                    "visual_prompt": f"dynamic motion scene of {topic} crossing a boundary, {theme}",
                    "stock_keywords": f"{v_world.replace('_', ' ')} motion",
                    "metric_value": 90.0,
                    "metric_unit": "SPEED",
                    "quote_title": theme.upper(),
                    "quote_text": "",
                    "callout_label": "BOUNDARY CROSSED",
                },
                {
                    "scene_type": "source_quote",
                    "narration": f"The documented record of {topic} captures just how extraordinary this milestone really is.",
                    "top_label": "THE RECORD",
                    "visual_prompt": f"atmospheric dramatic backdrop for {topic}, {theme}",
                    "stock_keywords": f"{v_world.replace('_', ' ')} dark",
                    "metric_value": 1.0,
                    "metric_unit": "FACT",
                    "quote_title": f"{theme.upper()} RECORD",
                    "quote_text": f"The documented story of {topic} shows how far beyond ordinary limits reality can reach.",
                    "callout_label": "VERIFIED FACT",
                },
                {
                    "scene_type": "zoom_callout",
                    "narration": f"Did you know this detail about {topic}? Drop your answer in the comments below.",
                    "top_label": "WHAT DO YOU THINK?",
                    "visual_prompt": f"awe-inspiring finale shot of {topic}, {theme}",
                    "stock_keywords": f"{v_world.replace('_', ' ')} horizon",
                    "metric_value": 100.0,
                    "metric_unit": "% REAL",
                    "quote_title": theme.upper(),
                    "quote_text": "",
                    "callout_label": "COMMENT BELOW",
                },
            ]

        return {
            "hook_overlay": _trim_words(str(parsed.get("hook_overlay") or topic), 36).upper(),
            "yt_title": str(parsed.get("yt_title") or f"{topic[:48]} #Shorts")[:100],
            "ig_caption": str(parsed.get("ig_caption") or f"{topic} — animated breakdown. Tell us your take in the comments! #Story #Shorts #Facts"),
            "visual_world": v_world,
            "character": character,
            "scenes": scenes,
            "art_style": art_style,
            "theme": theme,
            "council_models_used": list(self.models_called),
        }


# ============================================================================
# 3. DEPARTMENT #1: INTELLIGENCE — YOUTUBE & INSTAGRAM TREND SCOUT
# ============================================================================

def get_ytdlp_cookie_args(job_dir: Path) -> list[str]:
    cookies_raw = os.environ.get("YT_COOKIES_TXT", "").strip()
    if not cookies_raw:
        return []
    cookie_file = job_dir / ".yt_cookies.txt"
    cookie_file.write_text(cookies_raw + "\n", encoding="utf-8")
    return ["--cookies", str(cookie_file)]


def discover_instagram_trending(
    niche_query: str,
    brain: CompanyBrain,
) -> list[dict[str, Any]]:
    ig_user_id = os.environ.get("IG_USER_ID", "").strip()
    access_token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if not (ig_user_id and access_token):
        return []

    hashtag = re.sub(r"[^a-zA-Z0-9]", "", niche_query.split()[0] if niche_query.split() else "ai").lower() or "ai"

    try:
        search_res = _ig_api_call(
            f"{IG_GRAPH_BASE}/ig_hashtag_search",
            method="GET",
            params={"user_id": ig_user_id, "q": hashtag, "access_token": access_token},
        )
        tag_data = search_res.get("data", [])
        if not tag_data:
            return []
        hashtag_id = str(tag_data[0]["id"])

        top_res = _ig_api_call(
            f"{IG_GRAPH_BASE}/{hashtag_id}/top_media",
            method="GET",
            params={
                "user_id": ig_user_id,
                "fields": "id,media_type,media_url,permalink,caption,like_count,comments_count",
                "access_token": access_token,
            },
        )
        candidates: list[dict[str, Any]] = []
        for item in top_res.get("data", []):
            m_type = item.get("media_type", "")
            media_url = (item.get("media_url") or "").strip()
            permalink = (item.get("permalink") or "").strip()
            target_url = media_url if media_url.lower().split("?")[0].endswith(".mp4") else (permalink or media_url)
            if m_type not in {"VIDEO", "REELS"} or not target_url:
                continue
            if f"clip_url:{target_url}" in brain.processed_items:
                continue
            likes = int(item.get("like_count", 0))
            comments = int(item.get("comments_count", 0))
            score = float(likes * 25 + comments * 50 + 1000)
            candidates.append({
                "platform": "instagram",
                "url": target_url,
                "title": (item.get("caption") or f"Trending #{hashtag} Reel")[:80],
                "score": score,
                "license": "instagram_top_media",
            })
        return candidates
    except Exception as exc:
        log.warning("Instagram Graph API Hashtag Trend Scout skipped: %s", exc)
        return []


def discover_youtube_trending(
    niche_query: str,
    brain: CompanyBrain,
    require_cc: bool = True,
    max_results: int = 12,
    cookie_args: list[str] | None = None,
) -> list[dict[str, Any]]:
    cookie_args = cookie_args or []

    def _run_search(query_str: str, enforce_strict_cc_field: bool) -> list[dict[str, Any]]:
        cmd = [
            "yt-dlp",
            *cookie_args,
            "--extractor-args", "youtube:player_client=default,web_creator",
            f"ytsearch{max_results}:{query_str}",
            "--dump-json",
            "--no-playlist",
            "--skip-download",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=180)
        found: list[dict[str, Any]] = []
        for line in res.stdout.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                info = json.loads(line)
            except Exception:
                continue

            url = (info.get("webpage_url") or info.get("original_url") or "").strip()
            if not url or f"clip_url:{url}" in brain.processed_items:
                continue

            duration = float(info.get("duration") or 0.0)
            if duration < 25.0 or duration > 3600.0:
                continue

            channel_id = info.get("channel_id", "")
            license_str = (info.get("license") or "").lower()
            desc_str = (info.get("description") or "").lower()
            is_cc = ("creative commons" in license_str) or ("cc-by" in desc_str) or ("creative commons" in desc_str)
            is_allowlisted = channel_id in brain.allowlisted_channels
            if enforce_strict_cc_field and not (is_cc or is_allowlisted):
                continue

            views = int(info.get("view_count") or 0)
            likes = int(info.get("like_count") or 0)
            score = float(views + likes * 25)
            found.append({
                "platform": "youtube",
                "url": url,
                "title": info.get("title", "YouTube Trending Video"),
                "duration": duration,
                "views": views,
                "likes": likes,
                "score": score,
                "license": info.get("license") or "CC-Search",
            })
        return found

    search_q = f"{niche_query} creative commons" if require_cc else niche_query
    results = _run_search(search_q, enforce_strict_cc_field=require_cc)
    if not results and require_cc:
        results = _run_search(f"{niche_query} creative commons attribution", enforce_strict_cc_field=False)
    return results


def discover_trending_candidates(
    niche_query: str,
    brain: CompanyBrain,
    trend_platform: str = "auto",
    require_cc: bool = True,
    cookie_args: list[str] | None = None,
) -> list[str]:
    urls: list[str] = []
    queue_file = brain.brain_dir / "queue.txt"
    if queue_file.exists():
        for raw_line in queue_file.read_text(encoding="utf-8").splitlines():
            u = raw_line.strip()
            if u and not u.startswith("#") and f"clip_url:{u}" not in brain.processed_items:
                urls.append(u)

    candidates: list[dict[str, Any]] = []
    if trend_platform in {"auto", "instagram"}:
        candidates.extend(discover_instagram_trending(niche_query, brain))
    if trend_platform in {"auto", "youtube"}:
        candidates.extend(discover_youtube_trending(niche_query, brain, require_cc=require_cc, cookie_args=cookie_args))

    candidates.sort(key=lambda c: float(c.get("score", 0.0)), reverse=True)
    for c in candidates:
        u = str(c["url"])
        if u not in urls:
            urls.append(u)

    if not urls:
        raise RuntimeError(
            f"TREND_SCOUT_EMPTY: No un-clipped trending videos found for query='{niche_query}' (require_cc={require_cc})."
        )
    return urls[:5]


def discover_trending_video(
    niche_query: str,
    brain: CompanyBrain,
    trend_platform: str = "auto",
    require_cc: bool = True,
) -> str:
    return discover_trending_candidates(niche_query, brain, trend_platform=trend_platform, require_cc=require_cc)[0]


# ============================================================================
# 4. SHARED MEDIA, FFMPEG & PUBLIC HOSTING UTILITIES
# ============================================================================

def run_cmd(cmd: list[str], check: bool = True, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    log.debug("Executing: %s", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True, check=check, timeout=timeout)


def resolve_device(requested: str) -> str:
    if requested in {"cuda", "cpu"}:
        return requested
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


def export_to_public_dir(files: list[Path], public_dir: Path | None) -> None:
    if public_dir is None:
        return
    public_dir.mkdir(parents=True, exist_ok=True)
    for src in files:
        if src.exists():
            dst = public_dir / src.name
            if src.resolve() != dst.resolve():
                shutil.copy2(src, dst)
                log.info("Exported %s -> %s (for GitHub Pages / IG Graph API)", src.name, dst)


def cleanup_heavy_temp_files(job_dir: Path) -> None:
    for pattern in ("source.*", "audio_16k.wav", ".yt_cookies.txt"):
        for p in job_dir.glob(pattern):
            if p.name == "source.info.json":
                continue
            try:
                p.unlink()
            except Exception:
                pass


def parse_fps(rate_str: str) -> float:
    try:
        return float(Fraction(rate_str))
    except (ValueError, ZeroDivisionError):
        return 30.0


def ffprobe_metadata(video_path: Path, min_duration: float = 5.0) -> dict[str, Any]:
    if not video_path.exists() or video_path.stat().st_size == 0:
        raise ValueError(f"DEAD_LETTER: File missing or 0 bytes: {video_path}")

    res = run_cmd([
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ])
    data = json.loads(res.stdout)
    duration = float(data.get("format", {}).get("duration", 0.0))
    streams = data.get("streams", [])
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    if not video_streams:
        raise ValueError("DEAD_LETTER: No video stream found in media file.")
    if not audio_streams:
        raise ValueError("DEAD_LETTER: No audio stream found in media file.")
    if duration < min_duration:
        raise ValueError(f"DEAD_LETTER: Duration ({duration:.1f}s) is shorter than minimum {min_duration:.1f}s.")

    vs = video_streams[0]
    aus = audio_streams[0]
    return {
        "duration": duration,
        "width": int(vs["width"]),
        "height": int(vs["height"]),
        "vcodec": vs.get("codec_name", ""),
        "acodec": aus.get("codec_name", ""),
        "sample_rate": int(aus.get("sample_rate", 48000)),
        "fps": parse_fps(vs.get("r_frame_rate", "30/1")),
    }


def verify_rendered_mp4(mp4_path: Path, min_duration: float = 5.0) -> bool:
    meta = ffprobe_metadata(mp4_path, min_duration=min_duration)
    if meta["width"] != 1080 or meta["height"] != 1920:
        raise ValueError(f"QA_FAIL: Expected 1080x1920, got {meta['width']}x{meta['height']}")
    if meta["vcodec"] != "h264" or meta["acodec"] != "aac":
        raise ValueError(f"QA_FAIL: Expected h264/aac, got {meta['vcodec']}/{meta['acodec']}")
    if meta["duration"] > 59.5:
        raise ValueError(f"QA_FAIL: Duration {meta['duration']:.2f}s exceeds 59.5s Shorts/Reels cap")

    with mp4_path.open("rb") as f:
        head = f.read(65536)
    moov_pos = head.find(b"moov")
    mdat_pos = head.find(b"mdat")
    if moov_pos == -1 or (mdat_pos != -1 and mdat_pos < moov_pos):
        raise ValueError("QA_FAIL: MP4 `moov` atom is not at the front of the file (+faststart failed).")
    return True


def escape_ffmpeg_filter_path(path: Path) -> str:
    s = str(path.resolve()).replace("\\", "/")
    s = s.replace(":", r"\:").replace("'", r"\'").replace("[", r"\[").replace("]", r"\]")
    return s


# ============================================================================
# 5. ENGINE A: DIGITAL PRODUCT & MICRO-SAAS FACTORY (`--engine digital_product`)
# ============================================================================

def create_whop_checkout_link(product_title: str, price_usd: float, redirect_url: str) -> str:
    api_key = os.environ.get("WHOP_API_KEY", "").strip()
    company_id = os.environ.get("WHOP_COMPANY_ID", "").strip()
    slug = re.sub(r"[^a-z0-9]+", "-", product_title.lower()).strip("-") or "bundle"
    if not api_key or not company_id:
        log.info("WHOP_API_KEY / WHOP_COMPANY_ID not set; returning simulated checkout URL for local dry run.")
        return f"https://whop.com/checkout/plan_{slug}_dryrun/"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Api-Version-Date": "2025-01-01",
    }
    payload = {
        "company_id": company_id,
        "plan": {
            "company_id": company_id,
            "initial_price": price_usd,
            "plan_type": "one_time",
            "currency": "usd",
        },
        "redirect_url": redirect_url,
        "metadata": {"product_title": product_title},
    }
    req = urllib.request.Request(
        "https://api.whop.com/api/v1/checkout_configurations",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        raw, _ = urlopen_with_retry(req, timeout=30)
        body = json.loads(raw.decode("utf-8"))
        url = body.get("purchase_url") or body.get("url")
        if url:
            return str(url)
    except Exception as exc:
        log.warning("Whop checkout_configurations failed (%s); attempting /api/v1/products fallback...", exc)

    fallback_req = urllib.request.Request(
        f"https://api.whop.com/api/v1/products?company_id={urllib.parse.quote(company_id)}",
        headers=headers,
        method="GET",
    )
    raw_fb, _ = urlopen_with_retry(fallback_req, timeout=30)
    fb_body = json.loads(raw_fb.decode("utf-8"))
    products = fb_body.get("data", [])
    if products and products[0].get("route"):
        return f"https://whop.com/{products[0]['route']}"
    raise RuntimeError("Whop checkout link creation failed on both primary and fallback endpoints.")


def run_digital_product_engine(
    product_title: str,
    price_usd: float,
    source_app_dir: Path | None,
    job_dir: Path,
    brain: CompanyBrain,
    public_dir: Path | None = None,
) -> dict[str, Any]:
    item_key = f"product:{product_title.lower().strip()}"
    brain.check_pre_flight(item_key, estimated_cost_usd=0.05)

    out_dir = job_dir / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    council = AICouncil()
    copy_spec = council.run_6_brain_copy_council(product_title, brain.offers_pricing, brain)

    bundle_zip = out_dir / "pro_app_bundle.zip"
    with zipfile.ZipFile(bundle_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        if source_app_dir and source_app_dir.exists():
            for file_p in sorted(source_app_dir.rglob("*")):
                if file_p.is_file() and file_p.resolve() != bundle_zip.resolve():
                    zf.write(file_p, file_p.relative_to(source_app_dir))
        else:
            readme_content = f"# {product_title}\n\nGenerated by Jagnor AI Digital Product Factory.\n\n{brain.offers_pricing}\n"
            zf.writestr("README.md", readme_content)
            zf.writestr("index.html", f"<!DOCTYPE html><html><body><h1>{product_title}</h1></body></html>")

    promo_png = out_dir / "promo_card.png"
    _render_brand_slide_png(
        promo_png,
        width=1080,
        height=1920,
        badge=copy_spec["hook_badge"],
        headline=product_title.upper(),
        subline=f"Instant Download • ${price_usd:.0f} One-Time • Link in Bio",
        footer="6-AI COUNCIL VERIFIED BUILD",
    )
    promo_mp4 = out_dir / "product_demo_9x16.mp4"
    run_cmd([
        "ffmpeg", "-y",
        "-loop", "1", "-t", "12", "-i", str(promo_png),
        "-f", "lavfi", "-t", "12", "-i", "anullsrc=channel_layout=mono:sample_rate=48000",
        "-vf", "scale=1080:1920,format=yuv420p",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
        "-movflags", "+faststart",
        str(promo_mp4),
    ])
    qa_ok = verify_rendered_mp4(promo_mp4, min_duration=10.0)
    export_to_public_dir([bundle_zip, promo_mp4], public_dir)

    public_base = os.environ.get("PUBLIC_VIDEO_BASE_URL", "https://jagnor110-cell.github.io/Jagnor").rstrip("/")
    redirect_url = f"{public_base}/pro_app_bundle.zip"
    checkout_url = create_whop_checkout_link(product_title, price_usd, redirect_url)

    result = {
        "engine": "digital_product",
        "status": "APPROVAL_PENDING",
        "product_title": product_title,
        "price_usd": price_usd,
        "bundle_zip_path": str(bundle_zip),
        "promo_mp4_path": str(promo_mp4),
        "qa_verified": qa_ok,
        "whop_checkout_url": checkout_url,
        "yt_title": copy_spec["yt_title"],
        "ig_caption": copy_spec["ig_caption"],
        "council_models_used": copy_spec["council_models_used"],
    }
    brain.record_completion(item_key, "digital_product", 0.05, result)
    return result


# ============================================================================
# 6. ENGINE B: AUTOMATED VIDEO CLIPPING (`--engine clipping`)
# ============================================================================

def ingest_video(
    url: str,
    job_dir: Path,
    require_cc: bool = True,
    allowlisted_channels: set[str] | None = None,
) -> tuple[Path, Path]:
    job_dir.mkdir(parents=True, exist_ok=True)
    out_tpl = str(job_dir / "source.%(ext)s")
    cookie_args = get_ytdlp_cookie_args(job_dir)

    if url.lower().split("?")[0].endswith(".mp4"):
        video_path = job_dir / "source.mp4"
        info_path = job_dir / "source.info.json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        raw, _ = urlopen_with_retry(req, timeout=120)
        video_path.write_bytes(raw)
        info_path.write_text(json.dumps({"webpage_url": url, "license": "instagram_graph_media"}), encoding="utf-8")
        ffprobe_metadata(video_path, min_duration=15.0)
        return video_path, info_path

    meta_res = run_cmd([
        "yt-dlp",
        *cookie_args,
        "--extractor-args", "youtube:player_client=default,web_creator",
        "--dump-single-json",
        "--no-playlist",
        url,
    ])
    info = json.loads(meta_res.stdout)
    channel_id = info.get("channel_id", "")
    extractor = (info.get("extractor") or "").lower()
    license_str = (info.get("license") or "").lower()
    desc_str = (info.get("description") or "").lower()

    is_cc = ("creative commons" in license_str) or ("cc-by" in desc_str) or ("creative commons" in desc_str)
    is_allowlisted = allowlisted_channels is not None and (channel_id in allowlisted_channels or url in allowlisted_channels)
    is_ig = "instagram" in extractor
    if require_cc and not (is_cc or is_allowlisted or is_ig):
        raise PermissionError(
            f"DEAD_LETTER: License '{info.get('license')}' is not Creative Commons and channel '{channel_id}' is not allowlisted."
        )

    run_cmd([
        "yt-dlp",
        *cookie_args,
        "--extractor-args", "youtube:player_client=default,web_creator",
        "--geo-bypass",
        "--no-playlist",
        "--write-info-json",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs", "en.*,en",
        "--sub-format", "json3",
        "-f", "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--remux-video", "mp4",
        "-o", out_tpl,
        url,
    ])

    video_path = job_dir / "source.mp4"
    if not video_path.exists():
        candidates = [
            p for p in job_dir.glob("source.*")
            if p.suffix.lower() in {".mkv", ".webm", ".mov", ".m4v"}
        ]
        if candidates:
            run_cmd(["ffmpeg", "-y", "-i", str(candidates[0]), "-c", "copy", str(video_path)])

    info_path = job_dir / "source.info.json"
    ffprobe_metadata(video_path, min_duration=20.0)
    return video_path, info_path


def parse_yt_json3_subtitles(job_dir: Path) -> list[IndexedSegment]:
    json3_files = sorted(job_dir.glob("source.*.json3"))
    if not json3_files:
        return []
    try:
        raw = json.loads(json3_files[0].read_text(encoding="utf-8"))
        events = [ev for ev in raw.get("events", []) if ev.get("segs")]
    except Exception:
        return []

    indexed: list[IndexedSegment] = []
    for ev_i, ev in enumerate(events):
        segs = ev.get("segs", [])
        t_start_ms = float(ev.get("tStartMs", 0.0))
        d_dur_ms = float(ev.get("dDurationMs", 2500.0))
        if ev_i + 1 < len(events):
            next_start_ms = float(events[ev_i + 1].get("tStartMs", t_start_ms + d_dur_ms))
            event_end_ms = min(t_start_ms + d_dur_ms, max(t_start_ms + 300.0, next_start_ms))
        else:
            event_end_ms = t_start_ms + d_dur_ms

        words: list[WordToken] = []
        for idx, s in enumerate(segs):
            txt = (s.get("utf8") or "").strip()
            if not txt or txt == "\n":
                continue
            offset_ms = float(s.get("tOffsetMs", idx * 220.0))
            w_start = min(event_end_ms - 100.0, t_start_ms + offset_ms) / 1000.0
            w_end = min(event_end_ms / 1000.0, w_start + 0.40)
            for sub_w in txt.split():
                words.append(
                    WordToken(
                        word=sub_w,
                        start=round(max(0.0, w_start), 3),
                        end=round(max(w_start + 0.12, w_end), 3),
                    )
                )

        if not words:
            continue
        contig_id = len(indexed)
        indexed.append(
            IndexedSegment(
                segment_id=contig_id,
                speaker="SPEAKER_00",
                start=words[0].start,
                end=words[-1].end,
                text=" ".join(w.word for w in words),
                words=words,
            )
        )
    return indexed


def transcribe_with_faster_whisper_cpu(audio_wav: Path, model_name: str = "base") -> tuple[list[IndexedSegment], str]:
    from faster_whisper import WhisperModel

    cpu_model = "base" if "large" in model_name else model_name
    log.info("Running faster-whisper CPU fallback (model=%s, int8, word_timestamps=True)...", cpu_model)
    fw = WhisperModel(cpu_model, device="cpu", compute_type="int8")
    segments_gen, info = fw.transcribe(str(audio_wav), word_timestamps=True)
    detected_lang = getattr(info, "language", "en") or "en"

    indexed: list[IndexedSegment] = []
    for seg in segments_gen:
        raw_words = getattr(seg, "words", None) or []
        words = [
            WordToken(word=w.word.strip(), start=round(float(w.start), 3), end=round(float(w.end), 3))
            for w in raw_words
            if w.word.strip()
        ]
        if not words:
            continue
        contig_id = len(indexed)
        indexed.append(
            IndexedSegment(
                segment_id=contig_id,
                speaker="SPEAKER_00",
                start=words[0].start,
                end=words[-1].end,
                text=" ".join(w.word for w in words),
                words=words,
            )
        )
    return indexed, detected_lang


def flush_gpu_memory() -> None:
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


def transcribe_with_whisperx(
    video_path: Path,
    job_dir: Path,
    device: str = "auto",
    model_name: str = "large-v3-turbo",
    compute_type: str = "float16",
    batch_size: int = 16,
    hf_token: str | None = None,
) -> tuple[list[IndexedSegment], str]:
    actual_device = resolve_device(device)
    try:
        import whisperx
        has_whisperx = True
    except ImportError:
        has_whisperx = False

    out_json = job_dir / "transcript_indexed.json"

    if actual_device == "cpu" or not has_whisperx:
        fast_segments = parse_yt_json3_subtitles(job_dir)
        if fast_segments:
            log.info("Using zero-GPU yt-dlp .json3 word-aligned subtitle fast path (%d segments).", len(fast_segments))
            out_json.write_text(
                json.dumps([asdict(s) for s in fast_segments], indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            return fast_segments, "en"

    audio_wav = job_dir / "audio_16k.wav"
    run_cmd([
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        str(audio_wav),
    ])

    if not has_whisperx:
        fw_segments, fw_lang = transcribe_with_faster_whisper_cpu(audio_wav, model_name=model_name)
        out_json.write_text(
            json.dumps([asdict(s) for s in fw_segments], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return fw_segments, fw_lang

    log.info("Stage 1/3: WhisperX (%s) ASR on %s...", model_name, actual_device)
    model = whisperx.load_model(model_name, actual_device, compute_type=compute_type)
    audio = whisperx.load_audio(str(audio_wav))
    result = model.transcribe(audio, batch_size=batch_size)
    detected_lang = result.get("language", "en")
    del model
    flush_gpu_memory()

    log.info("Stage 2/3: Word-level forced alignment...")
    align_model, metadata = whisperx.load_align_model(language_code=detected_lang, device=actual_device)
    aligned = whisperx.align(
        result["segments"], align_model, metadata, audio, actual_device, return_char_alignments=False
    )
    del align_model
    flush_gpu_memory()

    token = hf_token or os.environ.get("HF_TOKEN")
    if token:
        try:
            log.info("Stage 3/3: Running Pyannote speaker diarization...")
            from whisperx.diarize import DiarizationPipeline
            diarize_model = DiarizationPipeline(use_auth_token=token, device=actual_device)
            diarize_segments = diarize_model(audio)
            aligned = whisperx.assign_word_speakers(diarize_segments, aligned)
            del diarize_model
            flush_gpu_memory()
        except Exception as exc:
            log.warning("Speaker diarization skipped: %s", exc)

    indexed: list[IndexedSegment] = []
    for seg in aligned.get("segments", []):
        seg_speaker = seg.get("speaker", "SPEAKER_00")
        words = [
            WordToken(
                word=w["word"].strip(),
                start=float(w["start"]),
                end=float(w["end"]),
                speaker=w.get("speaker", seg_speaker),
            )
            for w in seg.get("words", [])
            if "start" in w and "end" in w and w.get("word", "").strip()
        ]
        if not words:
            continue

        chunk_start_idx = 0
        for w_idx, w_tok in enumerate(words):
            is_last = (w_idx == len(words) - 1)
            span = w_tok.end - words[chunk_start_idx].start
            if span >= 45.0 or is_last:
                sub_words = words[chunk_start_idx: w_idx + 1]
                contig_id = len(indexed)
                indexed.append(
                    IndexedSegment(
                        segment_id=contig_id,
                        speaker=seg_speaker,
                        start=float(sub_words[0].start),
                        end=float(sub_words[-1].end),
                        text=" ".join(sw.word for sw in sub_words),
                        words=sub_words,
                    )
                )
                chunk_start_idx = w_idx + 1

    out_json.write_text(
        json.dumps([asdict(s) for s in indexed], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return indexed, detected_lang


def select_candidate_windows(
    segments: list[IndexedSegment],
    min_sec: float = 30.0,
    max_sec: float = 55.0,
    max_clips: int = 3,
) -> list[tuple[int, int]]:
    if not segments:
        return []
    windows: list[tuple[int, int]] = []
    i = 0
    while i < len(segments) and len(windows) < max_clips:
        start_t = segments[i].start
        j = i
        while j + 1 < len(segments) and (segments[j + 1].end - start_t) <= max_sec:
            j += 1
        dur = segments[j].end - start_t
        if min_sec <= dur <= max_sec:
            windows.append((segments[i].segment_id, segments[j].segment_id))
            i = j + 1
        else:
            i += 1

    if not windows:
        for seg in segments:
            dur = seg.end - seg.start
            if 15.0 <= dur <= 58.0:
                windows.append((seg.segment_id, seg.segment_id))
                break
        if not windows:
            windows.append((segments[0].segment_id, segments[0].segment_id))
    return windows


def detect_faces_in_frame(rgb_frame: np.ndarray, mp_detector: Any = None, cv_cascade: Any = None) -> list[tuple[float, float]]:
    detections: list[tuple[float, float]] = []
    if mp_detector is not None:
        res = mp_detector.process(rgb_frame)
        if res and getattr(res, "detections", None):
            for d in res.detections:
                score = float(d.score[0]) if d.score else 0.6
                box = d.location_data.relative_bounding_box
                cx = float(np.clip(box.xmin + box.width / 2.0, 0.15, 0.85))
                detections.append((score, cx))
        return detections

    if cv_cascade is not None:
        gray = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2GRAY)
        _h, w = gray.shape[:2]
        faces = cv_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(48, 48))
        for (x, _y, fw, _fh) in faces:
            cx = float(np.clip((x + fw / 2.0) / max(w, 1), 0.15, 0.85))
            detections.append((0.7, cx))
    return detections


def analyze_speaker_centers(
    video_path: Path,
    start_sec: float,
    end_sec: float,
    sample_fps: float = 2.0,
) -> tuple[list[tuple[float, float]], str]:
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, int(fps / sample_fps))

    centers: list[tuple[float, float]] = []
    wide_two_speaker_frames = 0
    total_sampled = 0

    mp_detector = None
    cv_cascade = None
    try:
        import mediapipe as mp
        if hasattr(mp, "solutions") and hasattr(mp.solutions, "face_detection"):
            mp_detector = mp.solutions.face_detection.FaceDetection(
                model_selection=1, min_detection_confidence=0.55
            )
    except Exception:
        mp_detector = None

    if mp_detector is None:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        cv_cascade = cv2.CascadeClassifier(cascade_path)

    try:
        frame_idx = int(start_sec * fps)
        end_idx = int(end_sec * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)

        while frame_idx <= end_idx:
            ok, frame = cap.read()
            if not ok:
                break
            if (frame_idx - int(start_sec * fps)) % step == 0:
                total_sampled += 1
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                faces = detect_faces_in_frame(rgb, mp_detector=mp_detector, cv_cascade=cv_cascade)
                t_rel = (frame_idx / fps) - start_sec

                if faces:
                    faces_sorted = sorted(faces, key=lambda item: item[0], reverse=True)
                    if len(faces_sorted) >= 2 and abs(faces_sorted[0][1] - faces_sorted[1][1]) >= 0.20:
                        wide_two_speaker_frames += 1
                    centers.append((t_rel, faces_sorted[0][1]))
                else:
                    prev_cx = centers[-1][1] if centers else 0.5
                    centers.append((t_rel, prev_cx))
            frame_idx += 1
    finally:
        cap.release()
        if mp_detector is not None and hasattr(mp_detector, "close"):
            mp_detector.close()

    if total_sampled > 0 and (wide_two_speaker_frames / total_sampled) > 0.45:
        return centers, "split"
    return centers, "single_ema"


def smooth_crop_x(centers: list[tuple[float, float]], alpha: float = 0.15, dwell_sec: float = 1.5) -> float:
    if not centers:
        return 0.5
    ema = centers[0][1]
    locked_x = ema
    last_switch_t = centers[0][0]
    smoothed: list[float] = []

    for t_rel, cx in centers:
        ema = alpha * cx + (1.0 - alpha) * ema
        if abs(ema - locked_x) > 0.08 and (t_rel - last_switch_t) >= dwell_sec:
            locked_x = ema
            last_switch_t = t_rel
        smoothed.append(locked_x)
    return float(np.median(smoothed))


def format_ass_time(sec: float) -> str:
    sec = max(0.0, sec)
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def sanitize_ass_text(raw: str) -> str:
    return re.sub(r"[{}\\\r\n]+", "", raw).strip()


def write_ass_captions(
    segments: list[IndexedSegment],
    start_seg_id: int,
    end_seg_id: int,
    clip_start: float,
    ass_path: Path,
    hook_overlay: str = "",
) -> None:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,72,&H00FFFFFF,&H0000D7FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,70,70,360,1
Style: HookBanner,Arial,58,&H0000D7FF,&H00FFFFFF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,3,3,0,8,80,80,240,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    clean_hook = sanitize_ass_text(hook_overlay).upper()
    if clean_hook:
        lines.append(
            f"Dialogue: 1,{format_ass_time(0.0)},{format_ass_time(3.5)},HookBanner,,0,0,0,,{clean_hook}"
        )

    selected = [s for s in segments if start_seg_id <= s.segment_id <= end_seg_id]

    for seg in selected:
        words = seg.words
        for idx in range(0, len(words), 4):
            chunk = words[idx: idx + 4]
            for active_i, active_w in enumerate(chunk):
                t0 = max(0.0, active_w.start - clip_start)
                t1 = max(t0 + 0.12, active_w.end - clip_start)
                rendered_tokens: list[str] = []
                for j, w in enumerate(chunk):
                    clean = sanitize_ass_text(w.word).upper()
                    if not clean:
                        continue
                    if j == active_i:
                        rendered_tokens.append(r"{\c&H00D7FF&}" + clean + r"{\c&HFFFFFF&}")
                    else:
                        rendered_tokens.append(clean)
                if rendered_tokens:
                    lines.append(
                        f"Dialogue: 0,{format_ass_time(t0)},{format_ass_time(t1)},Default,,0,0,0,,{' '.join(rendered_tokens)}"
                    )

    ass_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_vertical_short(
    video_path: Path,
    meta: dict[str, Any],
    start_sec: float,
    end_sec: float,
    ass_path: Path,
    out_mp4: Path,
    norm_cx: float,
    layout_mode: str,
) -> None:
    src_w, src_h = meta["width"], meta["height"]
    duration_sec = min(58.5, max(1.0, end_sec - start_sec))
    is_already_vertical = abs((src_w / src_h) - (9 / 16)) < 0.05
    ass_escaped = escape_ffmpeg_filter_path(ass_path)

    if is_already_vertical:
        vf = (
            f"scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,ass='{ass_escaped}'"
        )
        filter_args = ["-vf", vf]
    elif layout_mode == "split":
        fc = (
            f"[0:v]split=2[left][right];"
            f"[left]crop=trunc(iw/4)*2:trunc(ih/2)*2:0:0,"
            f"scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[top];"
            f"[right]crop=trunc(iw/4)*2:trunc(ih/2)*2:trunc(iw/4)*2:0,"
            f"scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[bot];"
            f"[top][bot]vstack=inputs=2,ass='{ass_escaped}'[vout]"
        )
        filter_args = ["-filter_complex", fc, "-map", "[vout]", "-map", "0:a:0"]
    else:
        crop_w = int((src_h * 9 / 16) // 2 * 2)
        crop_w = min(crop_w, (src_w // 2) * 2)
        x_offset = int(np.clip(norm_cx * src_w - crop_w / 2, 0, src_w - crop_w))
        x_offset = (x_offset // 2) * 2
        vf = f"crop={crop_w}:{(src_h // 2) * 2}:{x_offset}:0,scale=1080:1920,ass='{ass_escaped}'"
        filter_args = ["-vf", vf]

    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start_sec:.3f}",
        "-i", str(video_path),
        "-t", f"{duration_sec:.3f}",
        *filter_args,
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
        "-movflags", "+faststart",
        str(out_mp4),
    ]
    run_cmd(cmd)


def run_clipping_engine(
    url: str,
    job_dir: Path,
    brain: CompanyBrain,
    max_clips: int = 3,
    device: str = "auto",
    model_name: str = "large-v3-turbo",
    allow_all_licenses: bool = False,
    public_dir: Path | None = None,
) -> dict[str, Any]:
    item_key = f"clip_url:{url.strip()}"
    brain.check_pre_flight(item_key, estimated_cost_usd=0.25)

    out_dir = job_dir / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    video_path, _ = ingest_video(
        url,
        job_dir,
        require_cc=not allow_all_licenses,
        allowlisted_channels=brain.allowlisted_channels,
    )
    meta = ffprobe_metadata(video_path, min_duration=15.0)
    actual_device = resolve_device(device)
    compute_type = "float16" if actual_device == "cuda" else "int8"
    segments, lang = transcribe_with_whisperx(
        video_path,
        job_dir,
        device=actual_device,
        model_name=model_name,
        compute_type=compute_type,
    )
    seg_map = {s.segment_id: s for s in segments}

    council = AICouncil()
    council_specs = council.run_6_brain_clip_council(segments, brain=brain, max_clips=max_clips)
    if not council_specs:
        raise ValueError("DEAD_LETTER: Transcript produced 0 usable speech windows.")

    rendered: list[ClipSpec] = []
    exported_mp4s: list[Path] = []
    for idx, c_spec in enumerate(council_specs, start=1):
        clip_id = f"clip_{idx:02d}"
        s_id = int(c_spec["start_segment_id"])
        e_id = int(c_spec["end_segment_id"])
        start_sec = seg_map[s_id].start
        end_sec = min(start_sec + 58.0, max(start_sec + 12.0, seg_map[e_id].end))
        hook_overlay = str(c_spec.get("hook_overlay", ""))
        yt_title = str(c_spec.get("yt_title", f"Highlight {clip_id} #Shorts"))
        ig_caption = str(c_spec.get("ig_caption", "Full breakdown via link in bio."))
        council_score = float(c_spec.get("council_score", 9.0))

        centers, layout_mode = analyze_speaker_centers(video_path, start_sec, end_sec)
        norm_cx = smooth_crop_x(centers)

        ass_path = out_dir / f"{clip_id}.ass"
        mp4_path = out_dir / f"{clip_id}.mp4"
        write_ass_captions(segments, s_id, e_id, start_sec, ass_path, hook_overlay=hook_overlay)
        render_vertical_short(
            video_path, meta, start_sec, end_sec, ass_path, mp4_path, norm_cx, layout_mode
        )
        qa_ok = verify_rendered_mp4(mp4_path, min_duration=10.0)
        exported_mp4s.append(mp4_path)

        rendered.append(
            ClipSpec(
                clip_id=clip_id,
                start_segment_id=s_id,
                end_segment_id=e_id,
                start_sec=start_sec,
                end_sec=end_sec,
                duration_sec=round(end_sec - start_sec, 2),
                mp4_path=str(mp4_path),
                layout_mode=layout_mode,
                qa_verified=qa_ok,
                yt_title=yt_title,
                ig_caption=ig_caption,
                hook_overlay=hook_overlay,
                council_score=council_score,
                council_models_used=list(council.models_called),
                contains_synthetic_media=False,
                source_url=url,
            )
        )

    export_to_public_dir(exported_mp4s, public_dir)
    cleanup_heavy_temp_files(job_dir)

    result = {
        "engine": "clipping",
        "status": "APPROVAL_PENDING",
        "source_url": url,
        "language": lang,
        "council_models_used": list(council.models_called),
        "clips": [asdict(c) for c in rendered],
    }
    brain.record_completion(
        item_key,
        "clipping",
        0.25,
        {"clip_count": len(rendered), "source_url": url, "council_models": list(council.models_called)},
    )
    return result


# ============================================================================
# 7. ENGINE C: B2B LEAD, PROPOSAL & INVOICE ENGINE (`--engine b2b_agency`)
# ============================================================================

def run_b2b_agency_engine(
    client_name: str,
    discovery_notes: str,
    price_usd: float,
    job_dir: Path,
    brain: CompanyBrain,
) -> dict[str, Any]:
    item_key = f"b2b_client:{client_name.lower().strip()}"
    brain.check_pre_flight(item_key, estimated_cost_usd=0.05)

    out_dir = job_dir / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    ops_summary_path = out_dir / "01_operations_call_summary.md"
    ops_md = (
        f"# Discovery Call Summary — {client_name}\n\n"
        f"## Captured Notes\n{discovery_notes}\n\n"
        f"## Action Items & Owners\n"
        f"- **Operations Agent:** Lock scope against `03_offers_pricing.md`.\n"
        f"- **Deals Agent:** Draft turnkey automation proposal at **${price_usd:,.2f}**.\n"
        f"- **Human Gate:** Review proposal and invoice before sending to {client_name}.\n"
    )
    ops_summary_path.write_text(ops_md, encoding="utf-8")

    proposal_path = out_dir / "02_deals_proposal.md"
    proposal_md = (
        f"# AI Automation Proposal for {client_name}\n\n"
        f"## 1. Objective & Scope\n"
        f"Addressing key bottleneck identified in discovery: *{discovery_notes}*\n\n"
        f"## 2. Deliverables (Aligned with Company Brain)\n"
        f"{brain.offers_pricing}\n\n"
        f"## 3. Investment & Terms\n"
        f"- **Total Setup & Retainer:** ${price_usd:,.2f} USD\n"
        f"- **First Milestone (50% on sign-off):** ${price_usd / 2.0:,.2f} USD\n"
    )
    proposal_path.write_text(proposal_md, encoding="utf-8")

    invoice_id = f"INV-{int(time.time())}"
    invoice_path = out_dir / "03_backoffice_invoice.json"
    invoice_payload = {
        "invoice_id": invoice_id,
        "client_name": client_name,
        "amount_due_usd": round(price_usd / 2.0, 2),
        "total_contract_usd": round(price_usd, 2),
        "status": "APPROVAL_PENDING",
    }
    atomic_write_json(invoice_path, invoice_payload)

    result = {
        "engine": "b2b_agency",
        "status": "APPROVAL_PENDING",
        "client_name": client_name,
        "ops_summary_path": str(ops_summary_path),
        "proposal_path": str(proposal_path),
        "invoice_path": str(invoice_path),
        "invoice_id": invoice_id,
        "amount_due_usd": invoice_payload["amount_due_usd"],
    }
    brain.record_completion(item_key, "b2b_agency", 0.05, result)
    return result


# ============================================================================
# 8. ENGINE D: BRANDED 5-SLIDE IG CAROUSEL & FUNNEL (`--engine carousel_funnel`)
# ============================================================================

def _load_ttf_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size=size)
            except Exception:
                pass
    return ImageFont.load_default(size=size) if "size" in ImageFont.load_default.__code__.co_varnames else ImageFont.load_default()


def _wrap_text_lines(text: str, max_chars_per_line: int = 24, max_lines: int = 5) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur: list[str] = []
    for w in words:
        if len(w) > max_chars_per_line:
            w = w[:max_chars_per_line]
        cur.append(w)
        if len(" ".join(cur)) > max_chars_per_line:
            lines.append(" ".join(cur[:-1]) if len(cur) > 1 else cur[0])
            cur = [w] if len(cur) > 1 else []
    if cur:
        lines.append(" ".join(cur))
    return lines[:max_lines]


def _render_brand_slide_png(
    out_png: Path,
    width: int,
    height: int,
    badge: str,
    headline: str,
    subline: str,
    footer: str,
) -> None:
    img = Image.new("RGB", (width, height), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)

    draw.rectangle([(60, 80), (width - 60, 92)], fill=(56, 189, 248))
    draw.rounded_rectangle([(60, 130), (width - 60, height - 130)], radius=32, outline=(56, 189, 248), width=3)

    font_lg = _load_ttf_font(52, bold=True)
    font_md = _load_ttf_font(32, bold=False)

    draw.text((110, 190), badge[:40], fill=(250, 204, 21), font=font_md)

    y = 310
    for line in _wrap_text_lines(headline, max_chars_per_line=22, max_lines=5):
        draw.text((110, y), line, fill=(255, 255, 255), font=font_lg)
        y += 76

    y += 40
    for s_line in _wrap_text_lines(subline, max_chars_per_line=38, max_lines=3):
        draw.text((110, y), s_line, fill=(148, 163, 184), font=font_md)
        y += 48

    draw.text((110, height - 220), footer[:48], fill=(56, 189, 248), font=font_md)
    img.save(out_png, format="PNG")


def run_carousel_funnel_engine(
    topic: str,
    points: list[str],
    job_dir: Path,
    brain: CompanyBrain,
    public_dir: Path | None = None,
) -> dict[str, Any]:
    item_key = f"carousel:{topic.lower().strip()}"
    brain.check_pre_flight(item_key, estimated_cost_usd=0.04)

    out_dir = job_dir / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    council = AICouncil()
    copy_spec = council.run_6_brain_copy_council(topic, "; ".join(points), brain)
    padded_points = copy_spec["points"]

    slides_spec = [
        (f"SLIDE 01 / {copy_spec['hook_badge'][:18]}", topic.upper(), "Swipe to see the exact 4-stage blueprint ->"),
        ("SLIDE 02 / STEP 1", padded_points[0], "Stage 1: Foundation"),
        ("SLIDE 03 / STEP 2", padded_points[1], "Stage 2: Execution"),
        ("SLIDE 04 / STEP 3", padded_points[2], "Stage 3: Governance Gate"),
        ("SLIDE 05 / ACTION", "GET THE FULL BLUEPRINT & TOOLS", "Check the link in bio to deploy this today."),
    ]

    slide_paths: list[str] = []
    slide_files: list[Path] = []
    for idx, (badge, headline, subline) in enumerate(slides_spec, start=1):
        p = out_dir / f"slide_{idx:02d}.png"
        _render_brand_slide_png(
            p,
            width=1080,
            height=1350,
            badge=badge,
            headline=headline,
            subline=subline,
            footer=f"JAGNOR AI • {idx}/5",
        )
        slide_paths.append(str(p))
        slide_files.append(p)

    export_to_public_dir(slide_files, public_dir)

    result = {
        "engine": "carousel_funnel",
        "status": "APPROVAL_PENDING",
        "topic": topic,
        "slide_paths": slide_paths,
        "ig_caption": copy_spec["ig_caption"],
        "council_models_used": copy_spec["council_models_used"],
    }
    brain.record_completion(item_key, "carousel_funnel", 0.04, result)
    return result


# ============================================================================
# 8B. ENGINE E: CANVA / FABBLER / DIGITAL MAKER / QWEN DROP (`--engine raw_video_drop`)
# ============================================================================

def run_raw_video_drop_engine(
    inbox_dir: Path,
    job_dir: Path,
    brain: CompanyBrain,
    device: str = "auto",
    model_name: str = "base",
    public_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Scans `inbox_dir` (e.g. `inbox_videos/`) for the next unprocessed MP4/MOV exported from
    Canva (Fabbler.ai), Digital Maker AI, or Qwen/Wan, auto-transcribes (if audio has speech),
    runs the 4-Brain Free AI Council for hook/title/caption, formats to 1080x1920 9:16 with +faststart,
    marks `contains_synthetic_media=True`, and queues it for YouTube Shorts + Instagram Reels.
    """
    inbox_dir.mkdir(parents=True, exist_ok=True)
    video_files = sorted(
        f for f in inbox_dir.iterdir()
        if f.is_file() and f.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}
    )
    target_file: Path | None = None
    for vf in video_files:
        if f"raw_drop:{vf.name}" not in brain.processed_items:
            target_file = vf
            break

    if target_file is None:
        raise FileNotFoundError(
            f"DEAD_LETTER: No unprocessed MP4/MOV files found in {inbox_dir}. Drop a Canva/Qwen export there first."
        )

    item_key = f"raw_drop:{target_file.name}"
    brain.check_pre_flight(item_key, estimated_cost_usd=0.10)

    out_dir = job_dir / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    working_src = job_dir / "dropped_source.mp4"
    probe_raw = run_cmd([
        "ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(target_file)
    ])
    pdata = json.loads(probe_raw.stdout)
    has_audio = any(s.get("codec_type") == "audio" for s in pdata.get("streams", []))
    raw_dur = float(pdata.get("format", {}).get("duration", 15.0))

    if not has_audio:
        log.info("Dropped video %s has no audio track (e.g. Qwen/Wan); muxing silent 48kHz track...", target_file.name)
        run_cmd([
            "ffmpeg", "-y",
            "-i", str(target_file),
            "-f", "lavfi", "-t", f"{raw_dur:.3f}", "-i", "anullsrc=channel_layout=mono:sample_rate=48000",
            "-c:v", "copy", "-c:a", "aac", "-shortest",
            str(working_src),
        ])
    else:
        shutil.copy2(target_file, working_src)

    meta = ffprobe_metadata(working_src, min_duration=5.0)
    duration_sec = min(58.0, meta["duration"])
    clean_stem = re.sub(r"[_-]+", " ", target_file.stem).strip() or "AI Story Video"

    segments: list[IndexedSegment] = []
    lang = "en"
    if has_audio:
        try:
            actual_device = resolve_device(device)
            compute_type = "float16" if actual_device == "cuda" else "int8"
            segments, lang = transcribe_with_whisperx(
                working_src, job_dir, device=actual_device, model_name=model_name, compute_type=compute_type
            )
        except Exception as exc:
            log.info("Skipping speech transcription on dropped video (%s); using 4-Brain Free AI Council hook banner only.", exc)

    council = AICouncil()
    if segments:
        council_specs = council.run_6_brain_clip_council(segments, brain=brain, max_clips=1)
        c_spec = council_specs[0]
        s_id = int(c_spec["start_segment_id"])
        e_id = int(c_spec["end_segment_id"])
        seg_map = {s.segment_id: s for s in segments}
        start_sec = seg_map[s_id].start
        end_sec = min(start_sec + 58.0, max(start_sec + 5.0, seg_map[e_id].end))
        hook_overlay = str(c_spec.get("hook_overlay") or clean_stem[:36]).upper()
        yt_title = str(c_spec.get("yt_title") or f"{clean_stem[:48]} #Shorts")
        ig_caption = str(c_spec.get("ig_caption") or f"{clean_stem} — created with AI. Full tools in bio.")
        council_score = float(c_spec.get("council_score") or 9.2)
    else:
        copy_spec = council.run_6_brain_copy_council(clean_stem, f"AI generated short video: {clean_stem}", brain)
        s_id, e_id = 0, 0
        start_sec, end_sec = 0.0, duration_sec
        hook_overlay = copy_spec["hook_badge"]
        yt_title = copy_spec["yt_title"]
        ig_caption = copy_spec["ig_caption"]
        council_score = 9.0

    centers, layout_mode = analyze_speaker_centers(working_src, start_sec, end_sec)
    norm_cx = smooth_crop_x(centers)

    ass_path = out_dir / "drop_01.ass"
    safe_slug = re.sub(r"[^a-zA-Z0-9]+", "_", target_file.stem)[:24].strip("_") or "01"
    mp4_path = out_dir / f"drop_{safe_slug}.mp4"
    write_ass_captions(segments, s_id, e_id, start_sec, ass_path, hook_overlay=hook_overlay)
    render_vertical_short(working_src, meta, start_sec, end_sec, ass_path, mp4_path, norm_cx, layout_mode)
    qa_ok = verify_rendered_mp4(mp4_path, min_duration=5.0)

    export_to_public_dir([mp4_path], public_dir)
    if working_src.exists():
        working_src.unlink()
    cleanup_heavy_temp_files(job_dir)

    clip_obj = ClipSpec(
        clip_id="drop_01",
        start_segment_id=s_id,
        end_segment_id=e_id,
        start_sec=start_sec,
        end_sec=end_sec,
        duration_sec=round(end_sec - start_sec, 2),
        mp4_path=str(mp4_path),
        layout_mode=layout_mode,
        qa_verified=qa_ok,
        yt_title=yt_title,
        ig_caption=ig_caption,
        hook_overlay=hook_overlay,
        council_score=council_score,
        council_models_used=list(council.models_called),
        contains_synthetic_media=True,
        source_url=f"inbox:{target_file.name}",
    )

    result = {
        "engine": "clipping",
        "source_mode": "raw_video_drop",
        "status": "APPROVAL_PENDING",
        "source_url": f"inbox:{target_file.name}",
        "language": lang,
        "council_models_used": list(council.models_called),
        "clips": [asdict(clip_obj)],
    }
    brain.record_completion(item_key, "raw_video_drop", 0.10, {"file": target_file.name, "mp4_path": str(mp4_path)})
    return result


# ============================================================================
# 8C. ENGINE F: 100% HANDS-FREE AI FACELESS GENERATOR (`--engine ai_faceless`)
# ============================================================================

def _trim_words(text: str, max_chars: int = 58) -> str:
    """Trim text cleanly on a word boundary so fallback cards never slice mid-word."""
    clean = " ".join(text.split()).strip()
    if len(clean) <= max_chars:
        return clean
    cut = clean[:max_chars].rsplit(" ", 1)[0].rstrip(",;:- ")
    return (cut or clean[:max_chars]) + "..."


def _extract_narration_search_query(narration: str, explicit_query: str, topic: str) -> str:
    """
    Ensures every scene's visual search query stays tightly locked to the exact concrete
    subject spoken in that scene's narration (never generic random filler).
    """
    q = " ".join(re.sub(r"[^a-zA-Z0-9\s\-]+", " ", str(explicit_query or "")).split()).strip()
    if len(q.split()) >= 2:
        return q[:64]
    stopwords = {
        "the", "and", "for", "that", "this", "with", "from", "into", "your", "they", "them",
        "their", "what", "when", "where", "which", "about", "there", "these", "those", "most",
        "people", "never", "really", "just", "over", "under", "still", "every", "single",
        "would", "could", "should", "have", "been", "were", "will", "more", "than", "then",
    }
    words = [w for w in re.findall(r"[A-Za-z0-9\-]+", narration) if len(w) > 3 and w.lower() not in stopwords]
    base_topic = " ".join(topic.split()[:3])
    picked = " ".join(words[:3])
    return f"{base_topic} {picked}".strip()[:64] or topic[:64]


def _center_crop_9x16(im: Image.Image, out_img: Path) -> None:
    rgb = im.convert("RGB")
    w, h = rgb.size
    target_ratio = 9.0 / 16.0
    cur_ratio = w / float(max(h, 1))
    if cur_ratio > target_ratio:
        new_w = int(h * target_ratio)
        x0 = max(0, (w - new_w) // 2)
        rgb = rgb.crop((x0, 0, x0 + new_w, h))
    else:
        new_h = int(w / target_ratio)
        y0 = max(0, (h - new_h) // 2)
        rgb = rgb.crop((0, y0, w, y0 + new_h))
    rgb.resize((1080, 1920), Image.Resampling.LANCZOS).save(out_img, format="PNG")


def _apply_art_style_filter(im: Image.Image, art_style: str) -> Image.Image:
    """
    Transforms any fallback photo using OpenCV so it matches the user's chosen `art_style`
    (anime cel-shading, comic ink outlines, cyberpunk neon, oil painting, minimalist sketch,
    or dark cinematic film grading) — never raw unstyled photography.
    """
    try:
        bgr = cv2.cvtColor(np.asarray(im.convert("RGB")), cv2.COLOR_RGB2BGR)
        style = (art_style or "dark_cinematic").lower()

        if style in {"anime", "comic_book"}:
            # Bilateral color smoothing + crisp ink edge overlay (cel-shaded illustration look)
            smooth = cv2.bilateralFilter(bgr, d=9, sigmaColor=75, sigmaSpace=75)
            smooth = cv2.bilateralFilter(smooth, d=9, sigmaColor=75, sigmaSpace=75)
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            edges = cv2.adaptiveThreshold(
                cv2.medianBlur(gray, 5), 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 7
            )
            edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
            out = cv2.bitwise_and(smooth, edges_bgr)
            # Boost vibrance slightly
            hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.28, 0, 255)
            out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
        elif style == "cyberpunk":
            # High-contrast cyan/magenta neon split-tone grading
            out = cv2.bilateralFilter(bgr, d=7, sigmaColor=50, sigmaSpace=50).astype(np.float32)
            out[:, :, 0] = np.clip(out[:, :, 0] * 1.28 + 18, 0, 255)  # Blue/Cyan boost
            out[:, :, 1] = np.clip(out[:, :, 1] * 0.88, 0, 255)
            out[:, :, 2] = np.clip(out[:, :, 2] * 1.22 + 12, 0, 255)  # Magenta/Red boost
            out = out.astype(np.uint8)
        elif style == "oil_painting":
            out = cv2.stylization(bgr, sigma_s=60, sigma_r=0.45)
        elif style == "minimalist_sketch":
            gray_sketch, _ = cv2.pencilSketch(bgr, sigma_s=50, sigma_r=0.07, shade_factor=0.04)
            # Dark slate paper with warm gold-tinted sketch highlights
            inv = 255 - gray_sketch
            out = np.zeros_like(bgr)
            out[:, :, 0] = np.clip(22 + inv * 0.45, 0, 255).astype(np.uint8)
            out[:, :, 1] = np.clip(28 + inv * 0.72, 0, 255).astype(np.uint8)
            out[:, :, 2] = np.clip(38 + inv * 0.88, 0, 255).astype(np.uint8)
        elif style == "3d_pixar":
            out = cv2.edgePreservingFilter(bgr, flags=1, sigma_s=55, sigma_r=0.45)
            hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.25, 0, 255)
            hsv[:, :, 2] = np.clip(hsv[:, :, 2] * 1.06, 0, 255)
            out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
        else:
            # dark_cinematic: deep shadows, teal/amber film grade
            out = bgr.astype(np.float32)
            out[:, :, 0] = np.clip(out[:, :, 0] * 1.08, 0, 255)
            out[:, :, 1] = np.clip(out[:, :, 1] * 0.96, 0, 255)
            out[:, :, 2] = np.clip(out[:, :, 2] * 1.05, 0, 255)
            out = cv2.convertScaleAbs(out, alpha=1.08, beta=-14)

        return Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB), mode="RGB")


    except Exception as exc:
        log.debug("Art style filter [%s] fallback (%s); returning RGB image.", art_style, exc)
        return im.convert("RGB")

def _fetch_openrouter_ai_image(full_prompt: str, out_img: Path, scene_num: int) -> bool:
    """
    Generates a true 9:16 AI-styled image via OpenRouter's Image API (`POST /api/v1/images`)
    using `OPENROUTER_API_KEY`, matching the exact topic, theme, character, and art_style.
    """
    or_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not or_key:
        return False
    models = [
        os.environ.get("OPENROUTER_IMAGE_MODEL", "").strip(),
        "bytedance-seed/seedream-4.5",
        "black-forest-labs/flux.2-klein-4b",
    ]
    for model in [m for m in dict.fromkeys(models) if m]:
        payload = {
            "model": model,
            "prompt": full_prompt[:900],
            "aspect_ratio": "9:16",
            "n": 1,
        }
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/images",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {or_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/jagnor110-cell",
                "X-Title": "Jagnor AI Studio",
            },
            method="POST",
        )
        try:
            raw, _ = urlopen_with_retry(req, timeout=60, max_attempts=1)
            data = json.loads(raw.decode("utf-8"))
            items = data.get("data") or []
            if not items:
                continue
            item = items[0]
            img_bytes: bytes | None = None
            if item.get("b64_json"):
                b64_str = str(item["b64_json"])
                if "," in b64_str and b64_str.startswith("data:"):
                    b64_str = b64_str.split(",", 1)[1]
                img_bytes = base64.b64decode(b64_str)
            elif item.get("url"):
                with urllib.request.urlopen(urllib.request.Request(str(item["url"]), headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as resp:
                    img_bytes = resp.read()
            if img_bytes and len(img_bytes) > 10000:
                tmp_f = out_img.with_suffix(".or.img")
                tmp_f.write_bytes(img_bytes)
                with Image.open(tmp_f) as im:
                    _center_crop_9x16(im, out_img)
                tmp_f.unlink(missing_ok=True)
                log.info("Scene %d custom AI art generated via OpenRouter (%s).", scene_num, model)
                return True
        except Exception as exc:
            err_s = str(exc)
            log.debug("Scene %d OpenRouter image (%s) skipped: %s", scene_num, model, err_s)
            if any(code in err_s for code in ("HTTP 401", "HTTP 402", "HTTP 403")):
                break
            continue
    return False


def _fetch_hf_ai_image(full_prompt: str, out_img: Path, scene_num: int) -> bool:
    """Generates a custom 9:16 AI image via Hugging Face Inference API (`HF_TOKEN`) if configured."""
    hf_key = os.environ.get("HF_TOKEN", "").strip()
    if not hf_key:
        return False
    req = urllib.request.Request(
        "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell",
        data=json.dumps({"inputs": full_prompt[:600]}).encode("utf-8"),
        headers={"Authorization": f"Bearer {hf_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        raw, _ = urlopen_with_retry(req, timeout=60, max_attempts=1)
        if len(raw) > 10000:
            tmp_f = out_img.with_suffix(".hf.img")
            tmp_f.write_bytes(raw)
            with Image.open(tmp_f) as im:
                _center_crop_9x16(im, out_img)
            tmp_f.unlink(missing_ok=True)
            log.info("Scene %d custom AI art generated via Hugging Face FLUX.", scene_num)
            return True
    except Exception as exc:
        log.debug("Scene %d HF FLUX image skipped: %s", scene_num, exc)
    return False


def _fetch_wikimedia_topic_image(query: str, out_img: Path, scene_num: int, used_urls: set[str] | None = None) -> bool:
    """
    Fetches real, topic-accurate public-domain / CC photographs matching the exact scene
    narration from Wikimedia Commons (100% free, zero API key, zero watermarks).
    """
    clean_q = " ".join(re.sub(r"[^a-zA-Z0-9\s\-]+", " ", query).split()).strip()
    if not clean_q:
        return False
    api_url = (
        "https://commons.wikimedia.org/w/api.php?"
        + urllib.parse.urlencode({
            "action": "query",
            "generator": "search",
            "gsrnamespace": "6",
            "gsrsearch": f"{clean_q} filetype:bitmap",
            "gsrlimit": "10",
            "prop": "imageinfo",
            "iiprop": "url|mime|size",
            "iiurlwidth": "1200",
            "format": "json",
        })
    )
    try:
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": "JagnorAIStudio/2.0 (https://github.com/jagnor110-cell)"},
        )
        raw, _ = urlopen_with_retry(req, timeout=20, max_attempts=2)
        data = json.loads(raw.decode("utf-8"))
        pages = list((data.get("query") or {}).get("pages", {}).values())
        if not pages:
            return False

        candidates: list[tuple[int, str]] = []
        for p in pages:
            title_low = str(p.get("title") or "").lower()
            if any(bad in title_low for bad in (".svg", ".pdf", ".tif", "logo", "icon", "flag_of", "diagram_blank", "map_blank")):
                continue
            infos = p.get("imageinfo") or []
            if not infos:
                continue
            info = infos[0]
            mime = str(info.get("mime") or "")
            if mime not in {"image/jpeg", "image/png", "image/webp"}:
                continue
            w = int(info.get("width") or 0)
            h = int(info.get("height") or 0)
            if w < 500 or h < 500:
                continue
            img_url = str(info.get("thumburl") or info.get("url") or "")
            if not img_url:
                continue
            if used_urls is not None and img_url in used_urls:
                continue
            # Prefer portrait/square high-res photos over ultra-wide panoramas
            aspect_penalty = 0 if (h / float(max(w, 1))) >= 0.65 else -5000
            candidates.append((w * h + aspect_penalty, img_url))

        if not candidates:
            return False
        candidates.sort(key=lambda x: x[0], reverse=True)
        chosen_url = candidates[0][1]

        img_req = urllib.request.Request(
            chosen_url,
            headers={"User-Agent": "JagnorAIStudio/2.0 (https://github.com/jagnor110-cell)"},
        )
        with urllib.request.urlopen(img_req, timeout=25) as resp:
            img_bytes = resp.read()
        if len(img_bytes) < 12000:
            return False

        tmp_img = out_img.with_suffix(".wiki.img")
        tmp_img.write_bytes(img_bytes)
        with Image.open(tmp_img) as im:
            _center_crop_9x16(im, out_img)
        tmp_img.unlink(missing_ok=True)
        if used_urls is not None:
            used_urls.add(chosen_url)
        log.info("Scene %d real topic photo loaded from Wikimedia Commons (%s).", scene_num, clean_q[:36])
        return True
    except Exception as exc:
        log.info("Scene %d Wikimedia Commons lookup unavailable (%s).", scene_num, exc)
        return False


def _fetch_pexels_portrait_image(keywords: str, out_img: Path, scene_num: int) -> bool:
    """Fetches a free, watermark-free 9:16 portrait HD photo from Pexels API (`PEXELS_API_KEY`)."""
    pexels_key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not pexels_key:
        return False
    clean_q = re.sub(r"[^a-zA-Z0-9\s]+", " ", keywords).strip() or "futuristic dark technology"
    search_url = (
        "https://api.pexels.com/v1/search?"
        + urllib.parse.urlencode({"query": clean_q[:60], "orientation": "portrait", "per_page": 8})
    )
    try:
        req = urllib.request.Request(
            search_url,
            headers={"Authorization": pexels_key, "User-Agent": "JagnorAIStudio/2.0"},
        )
        raw, _ = urlopen_with_retry(req, timeout=25, max_attempts=2)
        data = json.loads(raw.decode("utf-8"))
        photos = data.get("photos") or []
        if not photos:
            return False
        chosen = photos[(scene_num - 1) % len(photos)]
        src_obj = chosen.get("src") or {}
        img_url = src_obj.get("portrait") or src_obj.get("large2x") or src_obj.get("large")
        if not img_url:
            return False
        img_req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(img_req, timeout=30) as resp:
            img_bytes = resp.read()
        if len(img_bytes) < 10000:
            return False
        tmp_jpg = out_img.with_suffix(".pexels.jpg")
        tmp_jpg.write_bytes(img_bytes)
        with Image.open(tmp_jpg) as im:
            rgb = im.convert("RGB")
            w, h = rgb.size
            target_ratio = 9.0 / 16.0
            cur_ratio = w / float(max(h, 1))
            if cur_ratio > target_ratio:
                new_w = int(h * target_ratio)
                x0 = max(0, (w - new_w) // 2)
                rgb = rgb.crop((x0, 0, x0 + new_w, h))
            else:
                new_h = int(w / target_ratio)
                y0 = max(0, (h - new_h) // 2)
                rgb = rgb.crop((0, y0, w, y0 + new_h))
            rgb.resize((1080, 1920), Image.Resampling.LANCZOS).save(out_img, format="PNG")
        tmp_jpg.unlink(missing_ok=True)
        log.info("Scene %d visual loaded from Pexels HD (%s).", scene_num, clean_q[:30])
        return True
    except Exception as exc:
        log.info("Scene %d Pexels API unavailable (%s).", scene_num, exc)
        return False


def _fetch_free_ai_scene_image(
    visual_prompt: str,
    out_img: Path,
    fallback_headline: str,
    scene_num: int,
    art_style: str = "dark_cinematic",
    stock_keywords: str = "",
) -> Path:
    """
    3-Layer Free Visual Chain:
      1) Pollinations.ai (`POLLINATIONS_API_KEY` on gen.pollinations.ai, or 1-shot legacy check; stops immediately on HTTP 401/402)
      2) Pexels HD Portrait Photos (`PEXELS_API_KEY` — 100% free, zero watermarks)
      3) Cleanly word-wrapped branded editorial card
    """
    style_suffix = ART_STYLE_PROMPTS.get(art_style, ART_STYLE_PROMPTS["dark_cinematic"])
    full_prompt = f"{visual_prompt}, {style_suffix}, vertical 9:16 composition"
    encoded = urllib.parse.quote(full_prompt)
    poll_key = os.environ.get("POLLINATIONS_API_KEY", "").strip()

    if scene_num > 1 and poll_key:
        time.sleep(3.0)

    max_attempts = 3 if poll_key else 1
    last_exc: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        seed = (scene_num * 137) + (attempt * 31)
        if poll_key:
            url = (
                f"https://gen.pollinations.ai/image/{encoded}"
                f"?width=1080&height=1920&model=flux&nologo=true&seed={seed}"
            )
            headers = {"Authorization": f"Bearer {poll_key}", "User-Agent": "Mozilla/5.0"}
        else:
            url = (
                f"https://image.pollinations.ai/prompt/{encoded}"
                f"?width=1080&height=1920&nologo=true&seed={seed}"
            )
            headers = {"User-Agent": "Mozilla/5.0"}

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=45) as resp:
                raw = resp.read()
            if len(raw) > 10000:
                tmp_jpg = out_img.with_suffix(".jpg")
                tmp_jpg.write_bytes(raw)
                with Image.open(tmp_jpg) as im:
                    rgb = im.convert("RGB")
                    w, h = rgb.size
                    cropped = rgb.crop((0, 0, w, int(h * 0.94)))
                    cropped.resize((1080, 1920), Image.Resampling.LANCZOS).save(out_img, format="PNG")
                tmp_jpg.unlink(missing_ok=True)
                log.info("Scene %d visual generated via Pollinations (%s).", scene_num, art_style)
                return out_img
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code in {401, 402, 403}:
                log.info("Scene %d Pollinations returned HTTP %d; skipping retries and checking Pexels fallback.", scene_num, exc.code)
                break
            if attempt < max_attempts:
                time.sleep(4.0 * attempt)
        except Exception as exc:
            last_exc = exc
            if "Temporary failure in name resolution" in str(exc) or "nodename nor servname" in str(exc):
                break
            if attempt < max_attempts:
                time.sleep(4.0 * attempt)

    if _fetch_openrouter_ai_image(full_prompt, out_img, scene_num):
        return out_img

    if _fetch_hf_ai_image(full_prompt, out_img, scene_num):
        return out_img

    if _fetch_pexels_portrait_image(stock_keywords or visual_prompt, out_img, scene_num) or _fetch_wikimedia_topic_image(stock_keywords or fallback_headline, out_img, scene_num):
        with Image.open(out_img) as im:
            _apply_art_style_filter(im, art_style).save(out_img, format="PNG")
        return out_img

    log.info("Scene %d image APIs unavailable (%s); rendering branded fallback visual.", scene_num, last_exc)
    _render_brand_slide_png(
        out_img,
        width=1080,
        height=1920,
        badge=f"SCENE 0{scene_num} • {art_style.replace('_', ' ').upper()}",
        headline=_trim_words(fallback_headline, 58).upper(),
        subline="4-Brain Free AI Council • Motion Short",
        footer="JAGNOR AI STUDIO",
    )
    return out_img


VOICE_PRESETS: dict[str, tuple[str, str, str]] = {
    # preset_name: (edge_tts_voice, rate, pitch)
    "deep_male": ("en-US-ChristopherNeural", "-6%", "-14Hz"),
    "serious_male": ("en-GB-RyanNeural", "-4%", "-6Hz"),
    "mysterious_male": ("en-US-SteffanNeural", "-12%", "-10Hz"),
    "happy_male": ("en-US-BrianNeural", "+8%", "+4Hz"),
    "indian_storyteller_male": ("en-IN-PrabhatNeural", "-3%", "-4Hz"),
    "deep_female": ("en-US-AriaNeural", "-6%", "-10Hz"),
    "serious_female": ("en-GB-SoniaNeural", "-4%", "-4Hz"),
    "mysterious_female": ("en-US-EmmaNeural", "-11%", "-8Hz"),
    "happy_female": ("en-US-JennyNeural", "+8%", "+6Hz"),
    "malayalam_mysterious_male": ("ml-IN-MidhunNeural", "-8%", "-6Hz"),
    "malayalam_female": ("ml-IN-SobhanaNeural", "-4%", "-2Hz"),
    "hindi_serious_male": ("hi-IN-MadhurNeural", "-5%", "-6Hz"),
}


def _resolve_voice_preset(voice_or_preset: str) -> tuple[str, str, str]:
    key = (voice_or_preset or "").strip()
    if key in VOICE_PRESETS:
        return VOICE_PRESETS[key]
    return (key or "en-US-ChristopherNeural", "+0%", "+0Hz")


def _synthesize_scene_voiceover(text: str, out_wav: Path, voice: str = "deep_male") -> float:
    """
    Uses free Microsoft `edge-tts` with mood presets (deep/serious/mysterious/happy
    male & female voices via --rate and --pitch) and 3-attempt retry + fallback voice.
    Falls back to a timed silent WAV only if offline or `edge-tts` is missing.
    """
    resolved_voice, rate, pitch = _resolve_voice_preset(voice)
    text = " ".join(str(text or "").split()).strip() or "Discover the hidden story behind this moment."
    mp3_tmp = out_wav.with_suffix(".mp3")
    est_dur = max(3.2, min(9.5, len(text.split()) / 2.6))
    voices_to_try = [resolved_voice, resolved_voice, "en-US-ChristopherNeural"]
    last_exc: Exception | None = None

    for attempt, active_voice in enumerate(voices_to_try, start=1):
        try:
            mp3_tmp.unlink(missing_ok=True)
            run_cmd(
                [
                    "edge-tts",
                    f"--voice={active_voice}",
                    f"--rate={rate}",
                    f"--pitch={pitch}",
                    f"--text={text}",
                    f"--write-media={mp3_tmp}",
                ],
                timeout=45,
            )
            if not mp3_tmp.exists() or mp3_tmp.stat().st_size < 1000:
                raise RuntimeError("edge-tts produced empty audio file")
            run_cmd([
                "ffmpeg", "-y", "-i", str(mp3_tmp),
                "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(out_wav),
            ], timeout=60)
            mp3_tmp.unlink(missing_ok=True)
            res = run_cmd([
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(out_wav),
            ])
            dur = float(res.stdout.strip() or est_dur)
            return max(2.5, min(11.0, dur))
        except FileNotFoundError as exc:
            last_exc = exc
            break  # edge-tts binary not installed
        except Exception as exc:
            last_exc = exc
            if attempt < len(voices_to_try):
                sleep_s = 2.0 * attempt
                log.info("edge-tts attempt %d/%d failed (%s); retrying in %.0fs...", attempt, len(voices_to_try), exc, sleep_s)
                time.sleep(sleep_s)

    log.info("edge-tts unavailable (%s); generating %.1fs silent fallback audio.", last_exc, est_dur)
    run_cmd([
        "ffmpeg", "-y", "-f", "lavfi", "-t", f"{est_dur:.2f}",
        "-i", "anullsrc=channel_layout=mono:sample_rate=48000",
        "-c:a", "pcm_s16le", str(out_wav),
    ], timeout=30)
    return est_dur


def run_ai_faceless_engine(
    topic: str,
    job_dir: Path,
    brain: CompanyBrain,
    voice: str = "deep_male",
    public_dir: Path | None = None,
    art_style: str = "dark_cinematic",
    theme: str = "AI & Tech Automation",
    character_desc: str = "",
) -> dict[str, Any]:
    """
    100% Hands-Free AI Faceless Short Generator:
    1) 4-Brain Free AI Council writes a 5-scene script & visual prompts.
    2) Free `edge-tts` voices each scene (with automatic fallback).
    3) Fetches 9:16 AI scene visuals (or branded fallback cards) and applies smooth Ken Burns zoompan.
    4) Burns 3.5s HookBanner + word-by-word gold karaoke `.ass` captions and verifies `moov` +faststart.
    """
    item_key = f"ai_faceless:{topic.lower().strip()}:{time.strftime('%Y%m%d', time.gmtime())}"
    brain.check_pre_flight(item_key, estimated_cost_usd=0.12)

    out_dir = job_dir / "out"
    scene_dir = job_dir / "scenes"
    out_dir.mkdir(parents=True, exist_ok=True)
    scene_dir.mkdir(parents=True, exist_ok=True)

    council = AICouncil()
    resolved_v = _resolve_voice_preset(voice)[0]
    lang_hint = "Malayalam" if resolved_v.startswith("ml-") else ("Hindi" if resolved_v.startswith("hi-") else "English")
    log.info(
        "Active Settings [ai_faceless]: topic='%s' | theme='%s' | art_style='%s' | voice='%s' (%s) | character='%s'",
        topic, theme, art_style, voice, lang_hint, character_desc or "auto",
    )
    script_pkg = council.run_6_brain_faceless_script(
        topic, brain, art_style=art_style, theme=theme, character_desc=character_desc, language_hint=lang_hint
    )
    scenes = script_pkg["scenes"]

    scene_mp4s: list[Path] = []
    indexed_segments: list[IndexedSegment] = []
    cursor_t = 0.0

    for idx, sc in enumerate(scenes, start=1):
        narration = sc["narration"]
        vis_prompt = f"{sc['visual_prompt']}, featuring {character_desc}" if character_desc.strip() else sc["visual_prompt"]
        img_p = scene_dir / f"scene_{idx:02d}.png"
        wav_p = scene_dir / f"scene_{idx:02d}.wav"
        clip_p = scene_dir / f"scene_{idx:02d}.mp4"

        stock_kw = sc.get("stock_keywords", f"{theme} {topic}")
        _fetch_free_ai_scene_image(
            vis_prompt,
            img_p,
            fallback_headline=narration,
            scene_num=idx,
            art_style=art_style,
            stock_keywords=stock_kw,
        )
        dur = _synthesize_scene_voiceover(narration, wav_p, voice=voice)
        frames = max(60, int(round(dur * 30)))

        # Alternating dynamic camera motion per scene (zoom-in, pan-right, zoom-out, pan-left, punch-in)
        motion_mode = (idx - 1) % 5
        if motion_mode == 0:
            zp_expr = f"zoompan=z='min(zoom+0.0016,1.18)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30"
        elif motion_mode == 1:
            zp_expr = f"zoompan=z='1.12':d={frames}:x='(iw-iw/zoom)*on/{frames}':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30"
        elif motion_mode == 2:
            zp_expr = f"zoompan=z='max(1.18-on*0.0012,1.0)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30"
        elif motion_mode == 3:
            zp_expr = f"zoompan=z='1.12':d={frames}:x='(iw-iw/zoom)*(1-on/{frames})':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30"
        else:
            zp_expr = f"zoompan=z='min(zoom+0.0018,1.20)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30"

        run_cmd([
            "ffmpeg", "-y",
            "-loop", "1", "-t", f"{dur:.3f}", "-i", str(img_p),
            "-i", str(wav_p),
            "-vf", f"scale=1080:1920,{zp_expr},format=yuv420p",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
            "-shortest",
            str(clip_p),
        ])
        scene_mp4s.append(clip_p)

        # Evenly distribute word timestamps across this scene's exact voiceover duration
        raw_words = [w for w in narration.split() if w.strip()]
        w_dur = dur / max(len(raw_words), 1)
        tokens: list[WordToken] = []
        for wi, w in enumerate(raw_words):
            ws = cursor_t + wi * w_dur
            we = cursor_t + (wi + 1) * w_dur
            tokens.append(WordToken(word=w, start=round(ws, 3), end=round(we, 3)))

        indexed_segments.append(
            IndexedSegment(
                segment_id=idx - 1,
                speaker="NARRATOR",
                start=round(cursor_t, 3),
                end=round(cursor_t + dur, 3),
                text=narration,
                words=tokens,
            )
        )
        cursor_t += dur

    # Concatenate all animated scenes
    concat_txt = scene_dir / "concat.txt"
    concat_txt.write_text("\n".join(f"file '{p.resolve()}'" for p in scene_mp4s) + "\n", encoding="utf-8")
    merged_mp4 = scene_dir / "merged_raw.mp4"
    run_cmd([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
        "-c", "copy", str(merged_mp4),
    ])

    # Burn HookBanner + word-by-word gold karaoke ASS captions and enforce -14 LUFS + faststart
    ass_path = out_dir / "faceless_01.ass"
    safe_slug = re.sub(r"[^a-zA-Z0-9]+", "_", topic)[:24].strip("_").lower() or f"short_{int(time.time()) % 100000}"
    final_mp4 = out_dir / f"faceless_{safe_slug}.mp4"
    write_ass_captions(
        indexed_segments,
        0,
        len(indexed_segments) - 1,
        0.0,
        ass_path,
        hook_overlay=script_pkg["hook_overlay"],
    )
    ass_escaped = escape_ffmpeg_filter_path(ass_path)
    run_cmd([
        "ffmpeg", "-y",
        "-i", str(merged_mp4),
        "-t", f"{min(58.0, cursor_t):.3f}",
        "-vf", f"scale=1080:1920,ass='{ass_escaped}'",
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
        "-movflags", "+faststart",
        str(final_mp4),
    ])

    qa_ok = verify_rendered_mp4(final_mp4, min_duration=10.0)
    export_to_public_dir([final_mp4], public_dir)
    shutil.rmtree(scene_dir, ignore_errors=True)

    clip_obj = ClipSpec(
        clip_id="faceless_01",
        start_segment_id=0,
        end_segment_id=len(indexed_segments) - 1,
        start_sec=0.0,
        end_sec=round(min(58.0, cursor_t), 2),
        duration_sec=round(min(58.0, cursor_t), 2),
        mp4_path=str(final_mp4),
        layout_mode="ai_faceless_9x16",
        qa_verified=qa_ok,
        yt_title=script_pkg["yt_title"],
        ig_caption=script_pkg["ig_caption"],
        hook_overlay=script_pkg["hook_overlay"],
        council_score=9.6,
        council_models_used=script_pkg["council_models_used"],
        contains_synthetic_media=True,
        source_url=f"ai_faceless:{topic}",
    )

    result = {
        "engine": "clipping",
        "source_mode": "ai_faceless",
        "status": "APPROVAL_PENDING",
        "source_url": f"ai_faceless:{topic}",
        "language": lang_hint,
        "settings_applied": {
            "topic": topic, "theme": theme, "art_style": art_style, "voice": voice, "character_desc": character_desc,
        },
        "council_models_used": script_pkg["council_models_used"],
        "clips": [asdict(clip_obj)],
    }
    brain.record_completion(item_key, "ai_faceless", 0.12, {"topic": topic, "mp4_path": str(final_mp4)})
    return result



# ============================================================================
# 8D. ENGINE G: UNIVERSAL 2D ANIMATED STORY & CHARACTER ENGINE (`--engine motion_story`)
# ============================================================================

def _hex_to_rgb(hex_str: str, default: tuple[int, int, int] = (217, 74, 56)) -> tuple[int, int, int]:
    s = hex_str.strip().lstrip("#")
    if len(s) == 6:
        try:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
        except Exception:
            pass
    return default


def _build_gradient_backdrop(width: int, height: int, mood: str, scene_idx: int) -> Image.Image:
    """Pre-renders a rich vertical atmospheric sky/horizon gradient once per scene."""
    palettes = [
        ((10, 18, 42), (24, 44, 84), (14, 24, 50)),    # Starry night ocean
        ((46, 26, 58), (156, 86, 88), (224, 152, 92)), # Golden sunset horizon
        ((12, 22, 46), (26, 62, 112), (48, 120, 186)), # Orbital space glow
        ((28, 20, 42), (76, 42, 74), (168, 96, 84)),   # Dusk twilight
        ((14, 24, 44), (30, 52, 90), (18, 30, 56)),    # Deep midnight finale
    ]
    if "sunset" in mood or "warm" in mood:
        top_c, mid_c, bot_c = palettes[(scene_idx + 1) % len(palettes)]
    elif "space" in mood or "cyber" in mood:
        top_c, mid_c, bot_c = palettes[(scene_idx + 2) % len(palettes)]
    else:
        top_c, mid_c, bot_c = palettes[scene_idx % len(palettes)]

    arr = np.zeros((height, width, 3), dtype=np.uint8)
    split = int(height * 0.65)
    for y in range(height):
        if y < split:
            t = y / float(max(split, 1))
            c = [int(top_c[i] + (mid_c[i] - top_c[i]) * t) for i in range(3)]
        else:
            t = (y - split) / float(max(height - split, 1))
            c = [int(mid_c[i] + (bot_c[i] - mid_c[i]) * t) for i in range(3)]
        arr[y, :] = c
    img = Image.fromarray(arr, mode="RGB")
    draw = ImageDraw.Draw(img)

    # Subtle twinkling starfield in upper sky
    rng = random.Random(1000 + scene_idx * 77)
    for _ in range(55):
        sx = rng.randint(20, width - 20)
        sy = rng.randint(40, int(height * 0.58))
        sr = rng.choice([1, 1, 2, 2, 3])
        alpha = rng.randint(155, 245)
        draw.ellipse((sx - sr, sy - sr, sx + sr, sy + sr), fill=(alpha, alpha, min(255, alpha + 10)))

    # Glowing moon / sun orb
    orb_x = int(width * (0.78 if scene_idx % 2 == 0 else 0.24))
    orb_y = int(height * 0.16)
    draw.ellipse((orb_x - 42, orb_y - 42, orb_x + 42, orb_y + 42), fill=(252, 238, 198))
    return img


def _load_font(size: int, bold: bool = False, text_sample: str = "") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    has_malayalam = any("\u0d00" <= ch <= "\u0d7f" for ch in text_sample)
    has_devanagari = any("\u0900" <= ch <= "\u097f" for ch in text_sample)
    candidates: list[str] = []
    if has_malayalam:
        candidates.extend([
            "/usr/share/fonts/truetype/noto/NotoSansMalayalam-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSansMalayalam-Regular.ttf",
            "/usr/share/fonts/truetype/lohit-malayalam/Lohit-Malayalam.ttf",
            "/usr/share/fonts/truetype/malayalam/Manjari-Bold.ttf",
        ])
    elif has_devanagari:
        candidates.extend([
            "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
            "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf",
        ])
    candidates.extend(
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        ]
        if bold
        else [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        ]
    )
    for fp in candidates:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    start_size: int = 56,
    min_size: int = 24,
    bold: bool = True,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for sz in range(start_size, min_size - 1, -4):
        fnt = _load_font(sz, bold=bold, text_sample=text)
        bbox = draw.textbbox((0, 0), text, font=fnt)
        if (bbox[2] - bbox[0]) <= max_width:
            return fnt
    return _load_font(min_size, bold=bold, text_sample=text)


def _draw_topic_subject(
    draw: ImageDraw.ImageDraw,
    visual_world: str,
    cx: float,
    cy: float,
    scale: float,
    char: dict[str, str],
    phase: float,
    flying: bool = False,
) -> None:
    """
    Draws a clean, topic-accurate 2D vector centerpiece so every topic gets the right visual:
      - `space`        : Voyager-style golden parabolic spacecraft + antenna + glowing thrusters
      - `ocean`        : Deep-sea exploration submersible + glowing headlight beam + bubbles
      - `tech_ai`      : Glowing neural core + orbiting satellite nodes + circuit rings
      - `finance`      : Animated rising gold market bars + luminous upward trend arrow
      - `history_myth` / `nature` : Sleek Kurzgesagt-style illustrated protagonist silhouette (no boxy blocks)
    """
    primary = _hex_to_rgb(char.get("primary_hex", "#D94A38"), (217, 74, 56))
    accent = _hex_to_rgb(char.get("accent_hex", "#F5C451"), (245, 196, 81))
    skin = _hex_to_rgb(char.get("skin_hex", "#C68642"), (198, 134, 66))
    aura = _hex_to_rgb(char.get("aura_hex", "#38BDF8"), (56, 189, 248))
    s = max(0.35, scale)
    bob = math.sin(phase * 2.0 * math.pi) * (10.0 * s)
    y = cy + bob

    if visual_world == "space":
        # Voyager-style deep-space probe: high-gain dish, golden record disc, long booms
        draw.ellipse((cx - 115 * s, y - 220 * s, cx + 115 * s, y - 140 * s), fill=(228, 236, 248), outline=aura, width=max(2, int(4 * s)))
        draw.ellipse((cx - 38 * s, y - 196 * s, cx + 38 * s, y - 164 * s), fill=(52, 68, 96))
        # Central hexagonal bus
        bus = [(cx - 58 * s, y - 140 * s), (cx + 58 * s, y - 140 * s), (cx + 46 * s, y - 62 * s), (cx - 46 * s, y - 62 * s)]
        draw.polygon(bus, fill=(38, 48, 72), outline=(190, 210, 235))
        # Golden Record emblem on spacecraft side
        draw.ellipse((cx - 26 * s, y - 126 * s, cx + 26 * s, y - 74 * s), fill=accent, outline=(255, 246, 200), width=max(2, int(3 * s)))
        draw.ellipse((cx - 7 * s, y - 107 * s, cx + 7 * s, y - 93 * s), fill=(38, 48, 72))
        # Magnetometer & RTG booms
        draw.line((cx - 54 * s, y - 104 * s, cx - 195 * s, y - 65 * s), fill=(180, 200, 225), width=max(2, int(4 * s)))
        draw.line((cx + 54 * s, y - 104 * s, cx + 185 * s, y - 145 * s), fill=(180, 200, 225), width=max(2, int(4 * s)))
        draw.ellipse((cx - 205 * s, y - 75 * s, cx - 185 * s, y - 55 * s), fill=aura)
        # Subtle thruster glow
        glow = int(18 * s * (0.85 + 0.25 * math.sin(phase * 6.0 * math.pi)))
        draw.ellipse((cx - glow, y - 60 * s, cx + glow, y - 60 * s + glow * 2), fill=aura)

    elif visual_world == "ocean":
        # Sleek deep-sea submersible + searchlight cone + rising bubbles
        beam = [(cx + 85 * s, y - 135 * s), (cx + 340 * s, y - 220 * s), (cx + 340 * s, y - 50 * s)]
        draw.polygon(beam, fill=(48, 128, 178))
        draw.rounded_rectangle((cx - 125 * s, y - 185 * s, cx + 110 * s, y - 85 * s), radius=int(48 * s), fill=accent, outline=(250, 245, 225), width=max(2, int(4 * s)))
        draw.rounded_rectangle((cx - 42 * s, y - 225 * s, cx + 28 * s, y - 175 * s), radius=int(14 * s), fill=primary, outline=(250, 245, 225), width=max(2, int(3 * s)))
        # Glass viewport dome
        draw.ellipse((cx + 22 * s, y - 165 * s, cx + 82 * s, y - 105 * s), fill=(26, 62, 108), outline=(185, 232, 255), width=max(2, int(4 * s)))
        # Rising bubbles
        for bi in range(4):
            bx = cx - 135 * s - bi * 18 * s
            by = y - 120 * s - ((phase * 140 + bi * 35) % 140) * s
            br = max(3, int((8 - bi) * s))
            draw.ellipse((bx - br, by - br, bx + br, by + br), outline=(185, 232, 255), width=2)

    elif visual_world == "tech_ai":
        # Glowing AI neural core + orbiting nodes
        r_outer = int(118 * s)
        r_inner = int(58 * s)
        draw.ellipse((cx - r_outer, y - 160 * s - r_outer, cx + r_outer, y - 160 * s + r_outer), outline=aura, width=max(2, int(4 * s)))
        draw.ellipse((cx - r_inner, y - 160 * s - r_inner, cx + r_inner, y - 160 * s + r_inner), fill=(22, 42, 76), outline=accent, width=max(3, int(5 * s)))
        for ni in range(6):
            ang = phase * 2.0 * math.pi + ni * (math.pi / 3.0)
            nx = cx + math.cos(ang) * r_outer
            ny = (y - 160 * s) + math.sin(ang) * r_outer
            draw.line((cx, y - 160 * s, nx, ny), fill=aura, width=max(1, int(2 * s)))
            draw.ellipse((nx - 14 * s, ny - 14 * s, nx + 14 * s, ny + 14 * s), fill=accent, outline=(255, 255, 255), width=2)

    elif visual_world == "finance":
        # Animated rising gold bars + glowing upward arrow
        bar_heights = [90, 145, 200, 275]
        for bi, bh in enumerate(bar_heights):
            cur_h = bh * s * min(1.0, 0.35 + phase * 0.9)
            bx = cx - 130 * s + bi * 74 * s
            col = accent if bi == 3 else aura
            draw.rounded_rectangle((bx, y - cur_h, bx + 52 * s, y), radius=int(8 * s), fill=col, outline=(245, 248, 255), width=2)
        draw.line((cx - 130 * s, y - 110 * s, cx + 135 * s, y - 305 * s), fill=accent, width=max(3, int(6 * s)))

    else:
        # Sleek Kurzgesagt-style minimalist illustrated protagonist (clean proportions, no boxy stomach smiley)
        halo_r = int(120 * s * (1.0 + 0.04 * math.sin(phase * 4.0 * math.pi)))
        draw.ellipse((cx - halo_r, y - 240 * s - halo_r * 0.7, cx + halo_r, y - 240 * s + halo_r * 0.7), outline=aura, width=max(2, int(3 * s)))
        sway = math.sin(phase * 2.0 * math.pi) * (20 * s)
        # Flowing cloak silhouette
        cloak = [(cx - 52 * s, y - 275 * s), (cx + 52 * s, y - 275 * s), (cx + 88 * s + sway, y - 35 * s), (cx - 88 * s + sway, y - 35 * s)]
        draw.polygon(cloak, fill=tuple(max(0, c - 45) for c in primary), outline=accent)
        # Tapered torso & lower tunic
        torso = [(cx - 52 * s, y - 278 * s), (cx + 52 * s, y - 278 * s), (cx + 38 * s, y - 150 * s), (cx - 38 * s, y - 150 * s)]
        draw.polygon(torso, fill=primary, outline=(245, 240, 230))
        if not flying:
            draw.rounded_rectangle((cx - 34 * s, y - 155 * s, cx - 6 * s, y), radius=int(10 * s), fill=tuple(max(0, c - 25) for c in primary))
            draw.rounded_rectangle((cx + 6 * s, y - 155 * s, cx + 34 * s, y), radius=int(10 * s), fill=tuple(max(0, c - 25) for c in primary))
        # Diagonal sash / scarf accent
        draw.line((cx - 46 * s, y - 272 * s, cx + 36 * s, y - 158 * s), fill=accent, width=max(3, int(8 * s)))
        # Clean rounded head + minimal glowing eyes (no awkward mouth)
        hr = 42 * s
        hy = y - 328 * s
        draw.ellipse((cx - hr, hy - hr, cx + hr, hy + hr), fill=skin, outline=(245, 240, 230), width=max(2, int(3 * s)))
        draw.ellipse((cx - 18 * s, hy - 8 * s, cx - 8 * s, hy + 2 * s), fill=(255, 255, 255))
        draw.ellipse((cx + 8 * s, hy - 8 * s, cx + 18 * s, hy + 2 * s), fill=(255, 255, 255))
        draw.arc((cx - hr * 0.9, hy - hr * 0.9, cx + hr * 0.9, hy - hr * 0.15), start=195, end=345, fill=accent, width=max(2, int(6 * s)))


def _fetch_story_backdrop_if_available(
    scene: dict[str, Any],
    art_style: str,
    scene_num: int,
    tmp_dir: Path,
    topic: str = "",
    theme: str = "",
    character_desc: str = "",
    used_urls: set[str] | None = None,
) -> Image.Image | None:
    """
    Strictly follows ALL pre-workflow instructions (`art_style`, `theme`, `topic`, `character_desc`):
      1) Pollinations.ai (`POLLINATIONS_API_KEY`) — custom AI art
      2) OpenRouter Image API (`OPENROUTER_API_KEY`) — custom AI art
      3) Hugging Face FLUX (`HF_TOKEN`) — custom AI art
      4) Stylized topic media (Pexels / Wikimedia transformed via `_apply_art_style_filter`
         so it NEVER looks like raw unstyled photography)
    """
    tmp_png = tmp_dir / f"story_bg_{scene_num:02d}.png"
    narration = str(scene.get("narration") or "")
    vp = str(scene.get("visual_prompt") or "")
    sk = _extract_narration_search_query(narration, str(scene.get("stock_keywords") or ""), topic or str(scene.get("top_label") or ""))

    style_suffix = ART_STYLE_PROMPTS.get(art_style, ART_STYLE_PROMPTS["dark_cinematic"])
    char_clause = f", featuring {character_desc}" if character_desc.strip() else ""
    theme_clause = f", theme: {theme}" if theme.strip() else ""
    full_prompt = f"{vp or sk}{char_clause}{theme_clause}, topic: {topic}, {style_suffix}, vertical 9:16 composition"

    poll_key = os.environ.get("POLLINATIONS_API_KEY", "").strip()
    pexels_key = os.environ.get("PEXELS_API_KEY", "").strip()
    loaded_ai = False
    loaded_photo = False

    if poll_key:
        encoded = urllib.parse.quote(full_prompt)
        url = f"https://gen.pollinations.ai/image/{encoded}?width=1080&height=1920&model=flux&nologo=true&seed={scene_num * 211}"
        try:
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {poll_key}", "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=40) as resp:
                raw = resp.read()
            if len(raw) > 10000:
                tmp_jpg = tmp_png.with_suffix(".jpg")
                tmp_jpg.write_bytes(raw)
                with Image.open(tmp_jpg) as im:
                    rgb = im.convert("RGB")
                    w, h = rgb.size
                    rgb.crop((0, 0, w, int(h * 0.94))).resize((1080, 1920), Image.Resampling.LANCZOS).save(tmp_png, format="PNG")
                tmp_jpg.unlink(missing_ok=True)
                loaded_ai = True
        except Exception as exc:
            log.info("Story scene %d Pollinations AI art skipped (%s).", scene_num, exc)

    if not loaded_ai:
        loaded_ai = _fetch_openrouter_ai_image(full_prompt, tmp_png, scene_num)

    if not loaded_ai:
        loaded_ai = _fetch_hf_ai_image(full_prompt, tmp_png, scene_num)

    if not loaded_ai and pexels_key:
        loaded_photo = _fetch_pexels_portrait_image(sk, tmp_png, scene_num)

    if not loaded_ai and not loaded_photo:
        loaded_photo = _fetch_wikimedia_topic_image(sk, tmp_png, scene_num, used_urls=used_urls)

    if (loaded_ai or loaded_photo) and tmp_png.exists():
        with Image.open(tmp_png) as im:
            styled = _apply_art_style_filter(im, art_style) if loaded_photo else im.convert("RGB")
            arr = np.asarray(styled, dtype=np.float32) * 0.65
            return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="RGB")
    return None


def _render_motion_story_scene(
    scene: dict[str, Any],
    character: dict[str, str],
    scene_idx: int,
    dur: float,
    wav_path: Path,
    out_mp4: Path,
    fps: int = 24,
    art_style: str = "dark_cinematic",
    tmp_dir: Path | None = None,
    topic: str = "",
    theme: str = "",
    character_desc: str = "",
    used_urls: set[str] | None = None,
) -> None:
    """
    Streams 1080x1920 24fps topic-accurate animation frames directly into FFmpeg:
    - Uses real AI/Pexels topic backdrops with smooth Ken Burns zoom when keys are set,
      OR topic-matched procedural 2D vector worlds (`space`, `ocean`, `tech_ai`, `finance`, `history_myth`, `nature`).
    - Overlays crisp animated HUD graphics: scale rulers, ticking counters, auto-sized
      parchment quote cards, and rim-anchored circular magnifier callouts.
    """
    W, H = 1080, 1920
    n_frames = max(48, int(round(dur * fps)))
    scene_type = scene.get("scene_type", "hero_intro")
    visual_world = character.get("visual_world", "space")
    top_label = str(scene.get("top_label") or "").upper()
    metric_val = float(scene.get("metric_value") or 100.0)
    metric_unit = str(scene.get("metric_unit") or "").upper()
    quote_title = str(scene.get("quote_title") or "RECORD")
    quote_text = str(scene.get("quote_text") or scene.get("narration") or "")
    callout_label = str(scene.get("callout_label") or "")

    photo_bg = _fetch_story_backdrop_if_available(scene, art_style, scene_idx + 1, tmp_dir or out_mp4.parent, topic=topic, theme=theme, character_desc=character_desc, used_urls=used_urls)
    bg_base = photo_bg if photo_bg is not None else _apply_art_style_filter(_build_gradient_backdrop(W, H, visual_world, scene_idx), art_style)
    has_photo_bg = photo_bg is not None

    sample_all = f"{top_label} {quote_title} {quote_text} {callout_label}"
    font_med = _load_font(38, bold=True, text_sample=sample_all)
    font_body = _load_font(34, bold=False, text_sample=sample_all)
    accent_rgb = _hex_to_rgb(character.get("accent_hex", "#F5C451"), (245, 196, 81))
    aura_rgb = _hex_to_rgb(character.get("aura_hex", "#38BDF8"), (56, 189, 248))

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
        "-i", str(wav_path),
        "-c:v", "libx264", "-preset", "fast", "-crf", "21", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
        "-shortest",
        str(out_mp4),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert proc.stdin is not None

    try:
        for f_idx in range(n_frames):
            t = f_idx / float(max(n_frames - 1, 1))
            if has_photo_bg:
                # Smooth 1.00x -> 1.12x Ken Burns zoom on real topic-accurate AI/Pexels artwork
                z = 1.0 + 0.12 * t
                cw, ch = int(W / z), int(H / z)
                x0, y0 = (W - cw) // 2, (H - ch) // 2
                frame = bg_base.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.Resampling.BILINEAR)
            else:
                frame = bg_base.copy()
            draw = ImageDraw.Draw(frame)

            horizon_y = int(H * 0.74)
            # Only draw water/ground horizon when procedural & appropriate to the world (not in deep space!)
            if not has_photo_bg:
                if visual_world == "space":
                    # Distant planet curvature & subtle orbital grid
                    draw.ellipse((-320, horizon_y + 10, W + 320, H + 520), fill=(18, 36, 74), outline=aura_rgb, width=4)
                    draw.arc((-140, horizon_y - 160, W + 140, H + 180), start=205, end=335, fill=(75, 110, 165), width=2)
                elif visual_world in {"ocean", "history_myth", "nature"}:
                    draw.rectangle((0, horizon_y, W, H), fill=(12, 22, 46))
                    for wi in range(12):
                        wy = horizon_y + 22 + wi * 38
                        shift = int(math.sin(t * 2.0 * math.pi + wi * 0.7) * 40)
                        draw.line((80 + shift, wy, 360 + shift, wy), fill=(72, 102, 148), width=3)
                        draw.line((560 - shift, wy + 12, 960 - shift, wy + 12), fill=(60, 88, 134), width=2)
                else:
                    # Sleek dark tech/finance studio floor grid
                    draw.rectangle((0, horizon_y, W, H), fill=(14, 18, 32))
                    for gi in range(6):
                        gy = horizon_y + gi * 70
                        draw.line((0, gy, W, gy), fill=(36, 54, 88), width=2)

            if scene_type == "hero_intro":
                if not has_photo_bg:
                    subj_scale = 0.85 + 0.25 * min(1.0, t * 1.4)
                    _draw_topic_subject(draw, visual_world, W * 0.5, horizon_y + 10, subj_scale, character, phase=t)
                if t > 0.30:
                    ruler_t = min(1.0, (t - 0.30) / 0.45)
                    ry_top = int(horizon_y - 520 * ruler_t)
                    draw.line((110, horizon_y, 110, ry_top), fill=accent_rgb, width=4)
                    for step_i, mult in enumerate(["×1", "×2", "×3"], start=1):
                        sy = int(horizon_y - step_i * 165)
                        if sy >= ry_top:
                            draw.line((96, sy, W - 90, sy), fill=(145, 170, 205), width=2)
                            draw.text((126, sy - 40), mult, font=font_med, fill=accent_rgb)

            elif scene_type == "scale_comparison":
                cur_val = metric_val * min(1.0, t * 1.25)
                val_str = f"{int(round(cur_val)):,} {metric_unit}".strip()
                f_stat = _fit_font(draw, val_str, max_width=W - 140, start_size=76, min_size=34, bold=True)
                sb = draw.textbbox((0, 0), val_str, font=f_stat)
                # Subtle dark pill behind stat so it never clashes with sun/moon or photo
                pw, ph = (sb[2] - sb[0]) + 48, (sb[3] - sb[1]) + 28
                px = (W - pw) // 2
                draw.rounded_rectangle((px, 218, px + pw, 218 + ph), radius=16, fill=(12, 18, 34))
                draw.text(((W - (sb[2] - sb[0])) // 2, 228), val_str, font=f_stat, fill=accent_rgb)

                if not has_photo_bg:
                    grow_scale = 0.65 + 0.48 * min(1.0, t * 1.2)
                    _draw_topic_subject(draw, visual_world, W * 0.52, horizon_y + 10, grow_scale, character, phase=t)
                bar_h = int(480 * min(1.0, t * 1.2))
                draw.line((110, horizon_y, 110, horizon_y - bar_h), fill=accent_rgb, width=6)

            elif scene_type == "action_flight":
                fx = 180 + (W - 360) * t
                fy = 820 + math.sin(t * 2.5 * math.pi) * 85
                for ti in range(1, 7):
                    tx = fx - ti * 38
                    ty = fy - 140 + math.sin((t - ti * 0.03) * 2.5 * math.pi) * 20
                    tr = max(4, 20 - ti * 3)
                    draw.ellipse((tx - tr, ty - tr, tx + tr, ty + tr), fill=aura_rgb)
                if not has_photo_bg:
                    _draw_topic_subject(draw, visual_world, fx, fy, 0.72, character, phase=t * 1.5, flying=True)

            elif scene_type == "source_quote":
                # Auto-sized parchment/editorial quote card — tight height with zero empty bottom gap!
                words = quote_text.split()
                q_lines: list[str] = []
                cur_l = ""
                for w in words:
                    test_l = (cur_l + " " + w).strip()
                    if len(test_l) > 36 and cur_l:
                        q_lines.append(cur_l)
                        cur_l = w
                    else:
                        cur_l = test_l
                if cur_l:
                    q_lines.append(cur_l)
                q_lines = q_lines[:7]

                card_h = 175 + len(q_lines) * 52
                card_top = max(320, (H - 360 - card_h) // 2)
                card_scale = min(1.0, t * 3.0)
                cy_off = int((1.0 - card_scale) * 65)
                box = (86, card_top + cy_off, W - 86, card_top + card_h + cy_off)
                draw.rounded_rectangle(box, radius=24, fill=(242, 230, 202), outline=accent_rgb, width=6)
                qt_str = f"|| {quote_title} ||"
                f_qt = _fit_font(draw, qt_str, max_width=W - 260, start_size=38, min_size=22, bold=True)
                qb = draw.textbbox((0, 0), qt_str, font=f_qt)
                draw.text(((W - (qb[2] - qb[0])) // 2, card_top + 38 + cy_off), qt_str, font=f_qt, fill=(108, 72, 24))
                draw.line((130, card_top + 102 + cy_off, W - 130, card_top + 102 + cy_off), fill=(170, 138, 86), width=3)
                for li, ql in enumerate(q_lines):
                    draw.text((130, card_top + 128 + cy_off + li * 52), ql, font=font_body, fill=(32, 26, 20))

            else:
                # zoom_callout: Rim-anchored circular magnifier callout + topic-matched icon
                if not has_photo_bg:
                    _draw_topic_subject(draw, visual_world, W * 0.64, horizon_y + 10, 0.95, character, phase=t)
                pop = min(1.0, t * 2.5)
                cr = int(138 * pop)
                ccx, ccy = 270, 620
                if cr > 24:
                    # Anchor leader line strictly from circle rim (not center!)
                    tx, ty = int(W * 0.56), horizon_y - 40
                    dx, dy = tx - ccx, ty - ccy
                    dist = max(1.0, math.hypot(dx, dy))
                    rim_x = int(ccx + (dx / dist) * cr)
                    rim_y = int(ccy + (dy / dist) * cr)
                    draw.line((rim_x, rim_y, tx, ty), fill=(235, 244, 255), width=4)
                    draw.ellipse((ccx - cr, ccy - cr, ccx + cr, ccy + cr), fill=(18, 30, 56), outline=(245, 248, 255), width=6)
                    # Topic-appropriate icon inside magnifier
                    if visual_world == "space":
                        draw.ellipse((ccx - cr * 0.36, ccy - cr * 0.36, ccx + cr * 0.36, ccy + cr * 0.36), fill=accent_rgb, outline=(255, 248, 220), width=3)
                        draw.ellipse((ccx - cr * 0.10, ccy - cr * 0.10, ccx + cr * 0.10, ccy + cr * 0.10), fill=(18, 30, 56))
                    elif visual_world == "ocean":
                        draw.arc((ccx - cr * 0.5, ccy - cr * 0.15, ccx + cr * 0.5, ccy + cr * 0.45), start=0, end=180, fill=aura_rgb, width=6)
                        draw.ellipse((ccx - cr * 0.16, ccy - cr * 0.42, ccx + cr * 0.16, ccy - cr * 0.10), outline=(200, 238, 255), width=3)
                    else:
                        draw.ellipse((ccx - cr * 0.42, ccy - cr * 0.42, ccx + cr * 0.42, ccy + cr * 0.42), outline=accent_rgb, width=4)
                        draw.ellipse((ccx - cr * 0.14, ccy - cr * 0.14, ccx + cr * 0.14, ccy + cr * 0.14), fill=aura_rgb)
                    f_co = _fit_font(draw, callout_label, max_width=520, start_size=36, min_size=22, bold=True)
                    cb = draw.textbbox((0, 0), callout_label, font=f_co)
                    co_x = max(48, min(W - 48 - (cb[2] - cb[0]), int(ccx - (cb[2] - cb[0]) // 2)))
                    draw.text((co_x, ccy - cr - 64), callout_label, font=f_co, fill=accent_rgb)

            # Top editorial title header (cleanly auto-fitted with subtle dark backing pill)
            if top_label:
                f_top = _fit_font(draw, top_label, max_width=W - 120, start_size=54, min_size=26, bold=True)
                bbox = draw.textbbox((0, 0), top_label, font=f_top)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                tx = (W - tw) // 2
                draw.rounded_rectangle((tx - 24, 110, tx + tw + 24, 110 + th + 24), radius=14, fill=(10, 16, 30))
                draw.text((tx, 118), top_label, font=f_top, fill=accent_rgb)

            proc.stdin.write(frame.tobytes())
    finally:
        if proc.stdin:
            proc.stdin.close()
        stderr_out = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        ret = proc.wait(timeout=180)
        if ret != 0:
            raise RuntimeError(f"FFmpeg motion_story scene render failed (code {ret}): {stderr_out[-400:]}")


def run_motion_story_engine(
    topic: str,
    job_dir: Path,
    brain: CompanyBrain,
    voice: str = "en-IN-PrabhatNeural",
    public_dir: Path | None = None,
    art_style: str = "dark_cinematic",
    theme: str = "Universal Storytelling",
    character_desc: str = "",
) -> dict[str, Any]:
    """
    All-Rounder 2D Animated Story & Universal Character Engine (`--engine motion_story`):
    1) 4-Brain Free AI Council designs a universal character sheet + 5 animated story scenes.
    2) Free `edge-tts` voices every scene (supports Indian English, US/UK English, Malayalam, Hindi).
    3) Streams real 24fps 2D vector animations (universal character motion, scale rulers,
       ticking counters, parchment quote cards, circular zoom callouts) directly to FFmpeg.
    4) Burns centered karaoke captions, enforces -14 LUFS + faststart, and exports to public/.
    """
    item_key = f"motion_story:{topic.lower().strip()}:{time.strftime('%Y%m%d', time.gmtime())}"
    brain.check_pre_flight(item_key, estimated_cost_usd=0.10)

    out_dir = job_dir / "out"
    scene_dir = job_dir / "story_scenes"
    out_dir.mkdir(parents=True, exist_ok=True)
    scene_dir.mkdir(parents=True, exist_ok=True)

    resolved_v = _resolve_voice_preset(voice)[0]
    lang_hint = "Malayalam" if resolved_v.startswith("ml-") else ("Hindi" if resolved_v.startswith("hi-") else "English")
    log.info(
        "Active Settings [motion_story]: topic='%s' | theme='%s' | art_style='%s' | voice='%s' (%s) | character='%s'",
        topic, theme, art_style, voice, lang_hint, character_desc or "auto",
    )
    council = AICouncil()
    story_pkg = council.run_motion_story_council(
        topic=topic,
        brain=brain,
        art_style=art_style,
        theme=theme,
        character_desc=character_desc,
        language_hint=lang_hint,
    )
    character = story_pkg["character"]
    scenes = story_pkg["scenes"]

    scene_mp4s: list[Path] = []
    indexed_segments: list[IndexedSegment] = []
    used_media_urls: set[str] = set()
    cursor_t = 0.0

    for idx, sc in enumerate(scenes, start=1):
        narration = sc["narration"]
        wav_p = scene_dir / f"story_{idx:02d}.wav"
        clip_p = scene_dir / f"story_{idx:02d}.mp4"

        dur = _synthesize_scene_voiceover(narration, wav_p, voice=voice)
        _render_motion_story_scene(
            sc,
            character,
            idx - 1,
            dur,
            wav_p,
            clip_p,
            fps=24,
            art_style=art_style,
            tmp_dir=scene_dir,
            topic=topic,
            theme=theme,
            character_desc=character_desc,
            used_urls=used_media_urls,
        )
        scene_mp4s.append(clip_p)

        raw_words = [w for w in narration.split() if w.strip()]
        w_dur = dur / max(len(raw_words), 1)
        tokens: list[WordToken] = []
        for wi, w in enumerate(raw_words):
            ws = cursor_t + wi * w_dur
            we = cursor_t + (wi + 1) * w_dur
            tokens.append(WordToken(word=w, start=round(ws, 3), end=round(we, 3)))

        indexed_segments.append(
            IndexedSegment(
                segment_id=idx - 1,
                speaker="NARRATOR",
                start=round(cursor_t, 3),
                end=round(cursor_t + dur, 3),
                text=narration,
                words=tokens,
            )
        )
        cursor_t += dur

    concat_txt = scene_dir / "concat.txt"
    concat_txt.write_text("\n".join(f"file '{p.resolve()}'" for p in scene_mp4s) + "\n", encoding="utf-8")
    merged_mp4 = scene_dir / "merged_story.mp4"
    run_cmd([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
        "-c", "copy", str(merged_mp4),
    ])

    ass_path = out_dir / "motion_story_01.ass"
    safe_slug = re.sub(r"[^a-zA-Z0-9]+", "_", topic)[:24].strip("_").lower() or f"story_{int(time.time()) % 100000}"
    final_mp4 = out_dir / f"story_{safe_slug}.mp4"
    # Pass empty hook_overlay so ASS top banner doesn't collide with the animated scene header
    write_ass_captions(
        indexed_segments,
        0,
        len(indexed_segments) - 1,
        0.0,
        ass_path,
        hook_overlay="",
    )
    ass_escaped = escape_ffmpeg_filter_path(ass_path)
    run_cmd([
        "ffmpeg", "-y",
        "-i", str(merged_mp4),
        "-t", f"{min(58.0, cursor_t):.3f}",
        "-vf", f"scale=1080:1920,ass='{ass_escaped}'",
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
        "-movflags", "+faststart",
        str(final_mp4),
    ])

    qa_ok = verify_rendered_mp4(final_mp4, min_duration=10.0)
    export_to_public_dir([final_mp4], public_dir)
    shutil.rmtree(scene_dir, ignore_errors=True)

    clip_obj = ClipSpec(
        clip_id="story_01",
        start_segment_id=0,
        end_segment_id=len(indexed_segments) - 1,
        start_sec=0.0,
        end_sec=round(min(58.0, cursor_t), 2),
        duration_sec=round(min(58.0, cursor_t), 2),
        mp4_path=str(final_mp4),
        layout_mode="motion_story_2d_9x16",
        qa_verified=qa_ok,
        yt_title=story_pkg["yt_title"],
        ig_caption=story_pkg["ig_caption"],
        hook_overlay=story_pkg["hook_overlay"],
        council_score=9.7,
        council_models_used=story_pkg["council_models_used"],
        contains_synthetic_media=True,
        source_url=f"motion_story:{topic}",
    )

    result = {
        "engine": "clipping",
        "source_mode": "motion_story",
        "status": "APPROVAL_PENDING",
        "source_url": f"motion_story:{topic}",
        "language": lang_hint,
        "settings_applied": {
            "topic": topic, "theme": theme, "art_style": art_style, "voice": voice, "character_desc": character_desc,
        },
        "character": character,
        "council_models_used": story_pkg["council_models_used"],
        "clips": [asdict(clip_obj)],
    }
    brain.record_completion(
        item_key,
        "motion_story",
        0.10,
        {"topic": topic, "character": character["name"], "mp4_path": str(final_mp4)},
    )
    return result


# ============================================================================
# 9. UNIFIED CLI ENTRYPOINT (TREND SCOUT + 4-BRAIN FREE AI COUNCIL + SOCIAL PUBLISHER)
# ============================================================================

def pick_fresh_auto_topic(theme: str, brain: CompanyBrain, engine: str) -> str:
    """
    Picks a fresh, non-duplicate story topic for scheduled cron runs so automated
    3x/day runs never collide with `05_memory_ledger.json`.
    """
    today_str = time.strftime("%Y%m%d", time.gmtime())
    ledger_data, _ = load_ledger(brain.ledger_path.parent)
    processed = set(ledger_data.get("processed_items", []))
    council = AICouncil()
    ai_raw = council.invoke_stage(
        "groq",
        "Return ONE short, high-curiosity YouTube Shorts story topic (5-10 words, no quotes, no numbering).",
        f"Theme: {theme}. Give a fresh, fascinating scale/mystery/history/science story idea that viewers haven't seen yet. "
        f"Avoid repeating recent titles: {list(processed)[-8:]}",
    )
    if ai_raw:
        cand = " ".join(ai_raw.strip().strip('"').strip("'").splitlines()[0].split())[:72]
        if len(cand) >= 10 and f"{engine}:{cand.lower().strip()}:{today_str}" not in processed:
            log.info("Auto-topic selected via AI Council: %s", cand)
            return cand

    fallback_pool = [
        "How Deep The Mariana Trench Really Goes",
        "How Far Voyager 1 Has Traveled Into Deep Space",
        "Why The Roman Concrete Formula Lasted 2000 Years",
        "How Tall Olympus Mons Is Compared To Everest",
        "The Forgotten Library That Changed Ancient Science",
        "How Fast A Neutron Star Spins In Deep Space",
        "Why The Great Pyramid Aligns Almost Perfectly True North",
        "How Much Gold Is Still Hidden Inside Earth's Core",
        "The Smallest Creature That Can Survive Outer Space",
        "How One Algorithm Changed Modern Navigation Forever",
    ]
    for cand in fallback_pool:
        if f"{engine}:{cand.lower().strip()}:{today_str}" not in processed:
            log.info("Auto-topic selected from curated pool: %s", cand)
            return cand
    return f"{theme} Untold Story {time.strftime('%H%M', time.gmtime())}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Jagnor AI Master Company Worker — 4-Brain Free AI Council, Trend Discovery & Social Publishing"
    )
    parser.add_argument(
        "--stage",
        default="build",
        choices=["build", "publish", "full"],
        help="`build` (discover/render & pause at APPROVAL_PENDING), `publish` (run built-in social publisher), or `full` (discover + build + publish)",
    )
    parser.add_argument(
        "--engine",
        default="clipping",
        choices=["motion_story", "ai_faceless", "clipping", "raw_video_drop", "digital_product", "b2b_agency", "carousel_funnel"],
        help="Which monetization engine to execute during build stage",
    )
    parser.add_argument("--job-dir", required=True, help="Working directory for this ticket/job")
    parser.add_argument("--brain-dir", default=None, help="Path to company `brain/` directory")
    parser.add_argument("--public-dir", default=None, help="Optional `public/` directory for GitHub Pages hosting")
    parser.add_argument("--inbox-dir", default="./inbox_videos", help="[raw_video_drop] Folder containing Canva/Fabbler/Digital Maker/Qwen MP4s")

    parser.add_argument("--url", default=None, help="[clipping] Explicit video URL (if omitted, Trend Scout auto-discovers)")
    parser.add_argument("--niche", default="AI agents automation tech podcast", help="[clipping] Niche query/hashtag for Trend Scout")
    parser.add_argument(
        "--trend-platform",
        default="auto",
        choices=["auto", "youtube", "instagram"],
        help="[clipping] Where Trend Scout searches when --url is omitted",
    )
    parser.add_argument("--max-clips", type=int, default=3, help="[clipping] Max clips to render")
    parser.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"], help="[clipping] Execution device")
    parser.add_argument("--model", default="large-v3-turbo", help="[clipping] WhisperX / faster-whisper model")
    parser.add_argument("--allow-all-licenses", action="store_true", help="[clipping] Disable CC-only filter")

    parser.add_argument("--title", default="Jagnor Pro Automation Suite", help="[ai_faceless / digital_product / carousel_funnel] Title or topic")
    parser.add_argument(
        "--art-style",
        default="dark_cinematic",
        choices=list(ART_STYLE_PROMPTS.keys()),
        help="[ai_faceless] Visual art style preset for animated scenes",
    )
    parser.add_argument(
        "--theme",
        default="Universal Storytelling",
        help="[motion_story / ai_faceless] Content niche/theme guiding script & visuals",
    )
    parser.add_argument(
        "--voice",
        default="deep_male",
        help="[motion_story / ai_faceless] Voice mood preset (deep_male, serious_male, mysterious_male, happy_male, deep_female, serious_female, mysterious_female, happy_female, etc.) or raw edge-tts voice",
    )
    parser.add_argument(
        "--character",
        default="",
        help="[motion_story] Optional character description (leave blank for universal auto-creation)",
    )
    parser.add_argument(
        "--auto-topic",
        action="store_true",
        help="[motion_story / ai_faceless] Auto-generate a fresh non-duplicate topic (used on scheduled runs)",
    )
    parser.add_argument("--price", type=float, default=17.0, help="[digital_product / b2b_agency] Price in USD")
    parser.add_argument("--source-app-dir", default=None, help="[digital_product] Optional folder to bundle into zip")

    parser.add_argument("--client", default="Acme Corp", help="[b2b_agency] Client name")
    parser.add_argument("--notes", default="Automate lead outreach, call summaries, and weekly reels.", help="[b2b_agency / carousel_funnel] Discovery notes or semicolon-separated points")

    parser.add_argument(
        "--approve-manifest",
        action="store_true",
        help="Pass Paperclip Human Approval Gate (transitions APPROVAL_PENDING -> APPROVED before publishing)",
    )
    parser.add_argument("--platforms", default="youtube,instagram", help="Comma-separated platforms (youtube,instagram)")
    parser.add_argument("--max-daily-posts", type=int, default=4, help="Max posts/platform per rolling 24h")
    parser.add_argument("--min-gap-hours", type=float, default=3.5, help="Min hours between posts on same platform")
    parser.add_argument("--skip-spacing-check", action="store_true", help="Bypass spacing check for immediate release")
    parser.add_argument("--apply-jitter", action="store_true", help="Sleep random 0..10m before calling social APIs")
    parser.add_argument("--dry-run-publish", action="store_true", help="Simulate YouTube/Instagram API calls locally")

    args = parser.parse_args()
    job_dir = Path(args.job_dir)
    job_dir.mkdir(parents=True, exist_ok=True)
    brain_dir = Path(args.brain_dir) if args.brain_dir else (job_dir / "brain")
    public_dir = Path(args.public_dir) if args.public_dir else None
    manifest_path = job_dir / "manifest.json"

    try:
        if args.stage in {"build", "full"}:
            brain = CompanyBrain.load(brain_dir)
            if args.engine == "clipping":
                explicit_url = (args.url or "").strip()
                if explicit_url:
                    candidate_urls = [explicit_url]
                else:
                    cookie_args = get_ytdlp_cookie_args(job_dir)
                    log.info("Launching Department #1 Trend Scout (niche='%s', platform='%s')...", args.niche, args.trend_platform)
                    candidate_urls = discover_trending_candidates(
                        niche_query=args.niche,
                        brain=brain,
                        trend_platform=args.trend_platform,
                        require_cc=not args.allow_all_licenses,
                        cookie_args=cookie_args,
                    )

                manifest = None
                last_err: Exception | None = None
                for cand_idx, cand_url in enumerate(candidate_urls, start=1):
                    try:
                        log.info("Attempting candidate %d/%d: %s", cand_idx, len(candidate_urls), cand_url)
                        manifest = run_clipping_engine(
                            url=cand_url,
                            job_dir=job_dir,
                            brain=brain,
                            max_clips=args.max_clips,
                            device=args.device,
                            model_name=args.model,
                            allow_all_licenses=args.allow_all_licenses,
                            public_dir=public_dir,
                        )
                        break
                    except Exception as err:
                        log.warning("Candidate %d (%s) failed (%s); trying next candidate...", cand_idx, cand_url, err)
                        cleanup_heavy_temp_files(job_dir)
                        last_err = err
                if manifest is None:
                    raise RuntimeError(f"All {len(candidate_urls)} trending candidates failed. Last error: {last_err}")

            elif args.engine == "motion_story":
                active_topic = pick_fresh_auto_topic(args.theme, brain, "motion_story") if args.auto_topic else (args.title or args.niche)
                manifest = run_motion_story_engine(
                    topic=active_topic,
                    job_dir=job_dir,
                    brain=brain,
                    voice=args.voice,
                    public_dir=public_dir,
                    art_style=args.art_style,
                    theme=args.theme,
                    character_desc=args.character,
                )
            elif args.engine == "ai_faceless":
                active_topic = pick_fresh_auto_topic(args.theme, brain, "ai_faceless") if args.auto_topic else (args.title or args.niche)
                manifest = run_ai_faceless_engine(
                    topic=active_topic,
                    job_dir=job_dir,
                    brain=brain,
                    voice=args.voice,
                    public_dir=public_dir,
                    art_style=args.art_style,
                    theme=args.theme,
                    character_desc=args.character,
                )
            elif args.engine == "raw_video_drop":
                manifest = run_raw_video_drop_engine(
                    inbox_dir=Path(args.inbox_dir),
                    job_dir=job_dir,
                    brain=brain,
                    device=args.device,
                    model_name=args.model,
                    public_dir=public_dir,
                )
            elif args.engine == "digital_product":
                src_dir = Path(args.source_app_dir) if args.source_app_dir else None
                manifest = run_digital_product_engine(
                    product_title=args.title,
                    price_usd=args.price,
                    source_app_dir=src_dir,
                    job_dir=job_dir,
                    brain=brain,
                    public_dir=public_dir,
                )
            elif args.engine == "b2b_agency":
                manifest = run_b2b_agency_engine(
                    client_name=args.client,
                    discovery_notes=args.notes,
                    price_usd=args.price,
                    job_dir=job_dir,
                    brain=brain,
                )
            elif args.engine == "carousel_funnel":
                pts = [p.strip() for p in args.notes.split(";") if p.strip()]
                manifest = run_carousel_funnel_engine(
                    topic=args.title,
                    points=pts,
                    job_dir=job_dir,
                    brain=brain,
                    public_dir=public_dir,
                )
            else:
                raise ValueError(f"Unsupported engine: {args.engine}")

            atomic_write_json(manifest_path, manifest)
            log.info("Build stage [%s] complete -> %s (status=%s)", args.engine, manifest_path, manifest.get("status"))

        if args.stage in {"publish", "full"}:
            platforms = {p.strip().lower() for p in args.platforms.split(",") if p.strip()}
            updated = process_manifest(
                manifest_path=manifest_path,
                brain_dir=brain_dir,
                approve_manifest=args.approve_manifest,
                platforms=platforms,
                max_daily_posts=args.max_daily_posts,
                min_gap_hours=args.min_gap_hours,
                skip_spacing_check=args.skip_spacing_check,
                apply_jitter=args.apply_jitter,
                dry_run=args.dry_run_publish,
                public_dir=public_dir,
            )
            log.info(
                "Connected Social Publisher complete -> status=%s | receipts=%s",
                updated.get("status"),
                updated.get("published_receipts"),
            )
            manifest = updated

        final_manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        subj, body = format_manifest_report(final_manifest, stage=args.stage)
        send_gmail_report(subj, body, dry_run=args.dry_run_publish)
        return 0
    except Exception as exc:
        log.error("Master pipeline halted: %s", exc)
        err_manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"engine": args.engine}
        subj, body = format_manifest_report(err_manifest, stage=args.stage, error_msg=str(exc))
        send_gmail_report(subj, body, dry_run=args.dry_run_publish)
        return 1


if __name__ == "__main__":
    sys.exit(main())
