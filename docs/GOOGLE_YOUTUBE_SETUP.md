# Google / YouTube setup

## OAuth secrets

Create a Google OAuth 2.0 client suitable for a server-side application and authorize the YouTube account that owns the destination Shorts channel.

The refresh token used by the factory must have these scopes:

- https://www.googleapis.com/auth/youtube.upload
- https://www.googleapis.com/auth/youtube.force-ssl
- https://www.googleapis.com/auth/youtube.readonly

Store the resulting values only as GitHub Actions repository secrets:

- YOUTUBE_CLIENT_ID
- YOUTUBE_CLIENT_SECRET
- YOUTUBE_REFRESH_TOKEN

Optional publication controls:

- YOUTUBE_AUTO_PUBLISH=true to allow real publication
- YOUTUBE_PRIVACY_STATUS=private, unlisted, or public

Keep automatic publication disabled until the end-to-end test has passed.

## Authorization manifest

The factory deliberately does not assume that public availability means permission to republish.

Add a source URL to `data/authorization_manifest.json` only when there is a real authorization or license permitting the intended use. Do not add a creator merely because their videos are public.

The manifest is the publication gate: without an authorized source, the factory will not download, render, or publish that source.

## First safe validation

After the three OAuth secrets exist, run the workflow with automatic publication still disabled. The expected result is:

- OAuth readiness succeeds.
- Analytics can authenticate.
- Publisher remains a dry-run.
- No unauthorized source is processed.
- The self-test remains green.

Only after that should a genuinely authorized source be added to the manifest and the render/publication path tested.
