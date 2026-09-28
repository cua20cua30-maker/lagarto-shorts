import json, os, urllib.parse, urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/creators.json"
OUT = ROOT / "data/kick_candidates.json"
DIAG = ROOT / "data/kick_radar_diagnostics.json"
TOKEN_URL = "https://id.kick.com/oauth/token"
API = "https://api.kick.com/public/v1"

def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default

def token():
    client_id = os.getenv("KICK_CLIENT_ID")
    client_secret = os.getenv("KICK_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None, "missing Kick credentials"
    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }).encode()
    req = urllib.request.Request(
        TOKEN_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "LagartoShortsFactory/2.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.loads(response.read().decode())
        access_token = data.get("access_token")
        return (access_token, None) if access_token else (None, "Kick token response did not contain access_token")
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"

def get(path, access_token, params):
    query = urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(
        API + path + ("?" + query if query else ""),
        headers={
            "Authorization": "Bearer " + access_token,
            "User-Agent": "LagartoShortsFactory/2.0",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode())

def score(title, viewers, started_at):
    text = (title or "").lower()
    keywords = (
        "reacción", "reaccion", "increíble", "increible", "polémica", "polemica",
        "humilla", "explota", "locura", "nadie esperaba", "se lía", "se lia",
        "viral", "wtf", "qué coño", "que coño", "no puede ser", "llora",
        "llorando", "triste", "enfado", "cabreado", "sorpresa", "brutal",
        "😂", "😭", "🥹", "💔", "😱", "😡", "😳", "💀", "🤯",
    )
    signal_score = sum(9 for keyword in keywords if keyword in text)
    viewer_score = min(25.0, (max(0, int(viewers or 0)) / 10000) ** 0.5 * 5)
    try:
        age_hours = max(
            0.0,
            (datetime.now(timezone.utc) - datetime.fromisoformat(
                started_at.replace("Z", "+00:00")
            )).total_seconds() / 3600,
        )
    except Exception:
        age_hours = 168.0
    freshness = max(0.0, 25.0 - age_hours / 7)
    return round(min(100.0, signal_score + viewer_score + freshness), 2)

def main():
    cfg = load(CONFIG, {"creators": []})
    now = datetime.now(timezone.utc)
    access_token, auth_error = token()
    candidates = []
    diagnostics = []

    if not access_token:
        status = "not_configured" if "missing Kick credentials" in (auth_error or "") else "error"
        for creator in cfg.get("creators", []):
            if creator.get("enabled", True) and creator.get("kick_slug"):
                diagnostics.append({
                    "creator": creator["name"],
                    "platform": "kick",
                    "status": status,
                    "kick_slug": creator["kick_slug"],
                    "error": auth_error,
                })
    else:
        for creator in cfg.get("creators", []):
            if not creator.get("enabled", True) or not creator.get("kick_slug"):
                continue
            slug = creator["kick_slug"]
            try:
                channels = get("/channels", access_token, {"slug": slug}).get("data", [])
                if not channels:
                    diagnostics.append({
                        "creator": creator["name"],
                        "platform": "kick",
                        "status": "not_found",
                        "kick_slug": slug,
                    })
                    continue

                channel = channels[0]
                user_id = channel.get("broadcaster_user_id")
                live = []
                if user_id:
                    live = get("/livestreams", access_token, {"user_id": user_id}).get("data", [])

                if not live:
                    diagnostics.append({
                        "creator": creator["name"],
                        "platform": "kick",
                        "status": "ok_offline",
                        "kick_slug": slug,
                        "broadcaster_user_id": user_id,
                        "live_streams": 0,
                    })
                    continue

                stream = live[0]
                started_at = stream.get("started_at") or now.isoformat()
                title = stream.get("title") or channel.get("stream_title") or ""
                viewers = stream.get("viewer_count", 0) or 0
                stream_id = stream.get("id")
                category = (stream.get("category") or {}).get("name")
                channel_slug = (stream.get("channel") or {}).get("slug") or slug
                source_url = f"https://kick.com/{channel_slug}"

                candidates.append({
                    "candidate_id": f"kick:live:{stream_id or user_id}",
                    "source_platform": "kick",
                    "source_creator": creator["name"],
                    "source_kind": "livestream_metadata",
                    "source_url": source_url,
                    "acquisition_url": None,
                    "source_id": stream_id,
                    "title": title,
                    "category": category,
                    "language_code": stream.get("language_code"),
                    "duration_raw": None,
                    "score": score(title, viewers, started_at),
                    "radar_rank": 0,
                    "detected_at": now.isoformat(),
                    "published_at": started_at,
                    "started_at": started_at,
                    "authorization_status": "unknown",
                    "publishable": False,
                    "acquirable": False,
                    "uploader_verified": True,
                    "uploader": (stream.get("broadcaster_user") or {}).get("username", slug),
                    "uploader_id": str(user_id),
                    "view_count": viewers,
                    "viewer_count": viewers,
                    "thumbnail_url": stream.get("thumbnail") or channel.get("stream", {}).get("thumbnail"),
                    "kick_slug": slug,
                    "kick_live": True,
                    "authorization_note": "Official Kick API metadata only; no undocumented VOD scraping.",
                })

                diagnostics.append({
                    "creator": creator["name"],
                    "platform": "kick",
                    "status": "ok_live",
                    "kick_slug": slug,
                    "broadcaster_user_id": user_id,
                    "live_streams": len(live),
                    "viewer_count": viewers,
                    "stream_id": stream_id,
                })
            except Exception as exc:
                diagnostics.append({
                    "creator": creator["name"],
                    "platform": "kick",
                    "status": "error",
                    "kick_slug": slug,
                    "error": f"{type(exc).__name__}: {exc}",
                })

    ranked = sorted(
        {item["candidate_id"]: item for item in candidates}.values(),
        key=lambda item: item["score"],
        reverse=True,
    )
    DIAG.write_text(
        json.dumps({
            "schema_version": 1,
            "generated_at": now.isoformat(),
            "api": "Kick Developer Public API",
            "results": diagnostics,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    OUT.write_text(
        json.dumps({
            "schema_version": 1,
            "generated_at": now.isoformat(),
            "candidates": ranked,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    counts = Counter(item["source_creator"] for item in ranked)
    print(
        f"Kick radar: discovered={len(ranked)} "
        f"creators_live={len(counts)} configured={bool(access_token)}"
    )

if __name__ == "__main__":
    main()
