import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


REQUIRED = (
    "YOUTUBE_CLIENT_ID",
    "YOUTUBE_CLIENT_SECRET",
    "YOUTUBE_REFRESH_TOKEN",
)

SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]


def main():
    missing = [name for name in REQUIRED if not os.getenv(name)]
    if missing:
        print("YouTube OAuth: NOT READY")
        print("Missing GitHub Actions secrets: " + ", ".join(missing))
        return 0

    try:
        credentials = Credentials(
            token=None,
            refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.environ["YOUTUBE_CLIENT_ID"],
            client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
            scopes=SCOPES,
        )
        credentials.refresh(Request())

        youtube = build("youtube", "v3", credentials=credentials)
        response = youtube.channels().list(
            part="id,snippet",
            mine=True,
            maxResults=1,
        ).execute()

        channels = response.get("items", [])
        if not channels:
            print("YouTube OAuth: API call succeeded, but no channel was returned.")
            return 1

        channel = channels[0]
        channel_id = channel.get("id", "")
        channel_title = channel.get("snippet", {}).get("title", "")
        print("YouTube OAuth: LIVE API CHECK OK.")
        print(f"Authenticated channel: {channel_title or '(unnamed)'}")
        print(f"Channel ID: {channel_id or '(missing)'}")
        print("Automatic publication remains controlled by YOUTUBE_AUTO_PUBLISH.")
        return 0

    except Exception as exc:
        print("YouTube OAuth: LIVE API CHECK FAILED.")
        print(f"{type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
