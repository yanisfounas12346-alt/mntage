"""Upload YouTube via OAuth desktop. Default visibility: private."""
import argparse
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def credentials():
    token = Path("token.json")
    creds = Credentials.from_authorized_user_file(str(token), SCOPES) if token.exists() else None
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        if not Path("client_secret.json").exists():
            raise FileNotFoundError("Fichier client_secret.json OAuth Google Cloud manquant.")
        flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
        creds = flow.run_local_server(port=0)
    token.write_text(creds.to_json(), encoding="utf-8")
    return creds


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", default="")
    args = parser.parse_args()
    if not args.video.is_file():
        parser.error("Vidéo introuvable.")
    youtube = build("youtube", "v3", credentials=credentials())
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {"title": args.title, "description": args.description, "categoryId": "28"},
            "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False},
        },
        media_body=MediaFileUpload(str(args.video), mimetype="video/mp4", resumable=True),
    )
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Envoi : {status.progress():.0%}")
    print("Vidéo envoyée en privé :", "https://www.youtube.com/watch?v=" + response["id"])


if __name__ == "__main__":
    main()
