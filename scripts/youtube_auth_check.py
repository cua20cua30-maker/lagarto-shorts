import os

REQUIRED = (
    "YOUTUBE_CLIENT_ID",
    "YOUTUBE_CLIENT_SECRET",
    "YOUTUBE_REFRESH_TOKEN",
)


def main():
    missing = [name for name in REQUIRED if not os.getenv(name)]
    if missing:
        print("YouTube OAuth: NOT READY")
        print("Missing GitHub Actions secrets: " + ", ".join(missing))
        return 1

    print("YouTube OAuth: secrets present.")
    print("Automatic publication remains controlled by YOUTUBE_AUTO_PUBLISH.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
