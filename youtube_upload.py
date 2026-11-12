"""YouTube upload via OAuth; always private, explicit user confirmation required."""
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
            raise FileNotFoundError("Place ton fichier OAuth client_secret.json dans le dossier mntage.")
        flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
        creds = flow.run_local_server(port=0)
    token.write_text(creds.to_json(), encoding="utf-8")
    return creds

def upload_private(video: Path, title: str, description: str = "") -> str:
    if not video.is_file():
        raise FileNotFoundError(str(video))
    youtube = build("youtube","v3",credentials=credentials())
    req = youtube.videos().insert(part="snippet,status",
        body={"snippet":{"title":title[:100],"description":description[:5000],"categoryId":"28"},
              "status":{"privacyStatus":"private","selfDeclaredMadeForKids":False}},
        media_body=MediaFileUpload(str(video),mimetype="video/mp4",resumable=True))
    result = None
    while result is None:
        _, result = req.next_chunk()
    return "https://www.youtube.com/watch?v=" + result["id"]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("video",type=Path)
    p.add_argument("--title",required=True)
    p.add_argument("--description",default="")
    a=p.parse_args()
    print("Vidéo envoyée en privé :",upload_private(a.video,a.title,a.description))

if __name__=="__main__":
    main()
