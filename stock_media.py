"""Optional Pexels stock media search; attribution and license review remain user's responsibility."""
import os,json,re
from urllib.request import Request,urlopen
from urllib.parse import urlencode, urlparse

def _api(endpoint,params):
    key=os.environ.get("PEXELS_API_KEY","").strip()
    if not key:raise RuntimeError("Ajoute PEXELS_API_KEY dans PowerShell.")
    url="https://api.pexels.com/"+endpoint+"?"+urlencode(params)
    with urlopen(Request(url,headers={"Authorization":key,"User-Agent":"mntage/0.4"}),timeout=20) as response:
        return json.load(response)

def scene_queries(script,limit=8):
    """Turn French narration into concrete English footage searches."""
    sentences=[s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+",script) if s.strip()]
    topics=[
        (("forêt","arbre","bois","jungle"),"forest trees"),
        (("océan","mer","vague","plage","eau"),"ocean waves"),
        (("espace","étoile","galaxie","planète","univers"),"outer space stars"),
        (("cerveau","neurone","mémoire","pensée"),"human brain science"),
        (("yeux","oeil","œil","regard","vision"),"human eye closeup"),
        (("ville","rue","immeuble","bâtiment"),"city streets"),
        (("montagne","sommet","alpes"),"mountain landscape"),
        (("animal","chien","chat","oiseau"),"wildlife animals"),
        (("soleil","lumière","coucher"),"sunset sky"),
        (("pluie","orage","tempête"),"rain storm"),
        (("voiture","route","conduite"),"cars road"),
        (("ordinateur","technologie","internet","robot"),"computer technology"),
        (("corps","santé","médecin","sang"),"human body medicine"),
        (("histoire","ancien","siècle","château"),"historic architecture"),
        (("nuage","ciel"),"clouds sky"),
    ]
    queries=[]
    for sentence in sentences[:limit]:
        normalized=sentence.casefold()
        matches=[(normalized.find(word),query) for words,query in topics
                 for word in words if word in normalized]
        if matches:
            queries.append(min(matches,key=lambda item:item[0])[1])
        else:
            words=re.findall(r"[a-zA-ZÀ-ÿ]+",normalized)
            # Commons indexes French descriptions too: do not invent unrelated stock topics.
            stop={"avec","pour","dans","cette","comme","mais","plus","nous","vous",
                  "elles","sont","être","avoir","cest","tout","tous","leurs","alors",
                  "cette","notre","votre","cela","depuis","quand","parce","aussi"}
            keywords=[w for w in words if len(w)>=5 and w not in stop]
            queries.append(" ".join(keywords[:3]) or "nature")
    return queries or ["nature"]

def search_videos(query,limit=3):
    data=_api("videos/search",{"query":query[:100],"per_page":min(10,max(1,limit)),"orientation":"portrait"})
    out=[]
    for video in data.get("videos",[]):
        files=[f for f in video.get("video_files",[]) if f.get("file_type")=="video/mp4" and f.get("link")]
        files.sort(key=lambda f:(0 if (f.get("width") or 0) >= 540 and (f.get("height") or 0) >= 960 else 1, abs((f.get("width") or 540)-720)+abs((f.get("height") or 960)-1280)))
        if files:
            out.append({"url":files[0]["link"],"credit":video.get("user",{}).get("name",""),"page":video.get("url",""),"duration":video.get("duration",0),"id":video.get("id")})
    return out

def search_images(query,limit=4):
    data=_api("v1/search",{"query":query[:100],"per_page":min(10,max(1,limit)),"orientation":"portrait"})
    return [{"url":p["src"]["large"],"credit":p.get("photographer",""),"page":p.get("url","")} for p in data.get("photos",[])]

def _download(url,max_bytes):
    """Download bounded media over HTTPS; reject HTML error pages and empty files."""
    parsed=urlparse(url)
    if parsed.scheme!="https" or not parsed.hostname:
        raise RuntimeError("Source média non sécurisée : HTTPS requis.")
    request=Request(url,headers={
        "User-Agent":"mntage/1.0 (https://github.com/yanisfounas12346-alt/mntage)"})
    with urlopen(request,timeout=45) as response:
        length=response.headers.get("Content-Length")
        if length and int(length)>max_bytes:
            raise RuntimeError("Média trop volumineux (taille annoncée).")
        content_type=response.headers.get("Content-Type","").split(";")[0].strip().lower()
        if content_type in {"text/html","application/json","text/plain"}:
            raise RuntimeError("Le serveur a renvoyé une page au lieu d'un média.")
        data=response.read(max_bytes+1)
    if not data:
        raise RuntimeError("Le fichier média téléchargé est vide.")
    if len(data)>max_bytes:
        raise RuntimeError("Média trop volumineux.")
    return data

def download_images(items):
    return [_download(i["url"],8*1024*1024) for i in items]

def download_videos(items):
    return [_download(i["url"],55*1024*1024) for i in items]

def select_video_scenes(script, limit=8):
    """Prefer distinct source videos; fail visibly instead of substituting abstract backgrounds."""
    selected=[]
    used=set()
    missing=[]
    for query in scene_queries(script,limit):
        options=search_videos(query,limit=6)
        choice=next((v for v in options if v.get("id") not in used),None)
        if choice:
            selected.append(choice)
            used.add(choice.get("id"))
        else:
            missing.append(query)
    if not selected:
        raise RuntimeError("Aucun clip Pexels pertinent trouvé. Essaie un script plus visuel.")
    return selected,missing

def search_pixabay_videos(query, limit=6):
    """Pixabay video API, with 24h on-disk search cache as required by API terms."""
    import hashlib
    import time
    from pathlib import Path
    key=os.environ.get("PIXABAY_API_KEY","").strip()
    if not key:raise RuntimeError("PIXABAY_API_KEY manquante.")
    cache=Path("outputs")/"pixabay_cache"
    cache.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256((query+str(limit)).encode("utf-8")).hexdigest()
    file=cache/(digest+".json")
    if file.exists() and time.time()-file.stat().st_mtime<86400:
        data=json.loads(file.read_text(encoding="utf-8"))
    else:
        params={"key":key,"q":query[:100],"per_page":max(3,min(limit,20)),"safesearch":"true","video_type":"film"}
        url="https://pixabay.com/api/videos/?"+urlencode(params)
        with urlopen(Request(url,headers={"User-Agent":"mntage/0.5"}),timeout=20) as response:
            data=json.load(response)
        file.write_text(json.dumps(data),encoding="utf-8")
    result=[]
    for hit in data.get("hits",[]):
        versions=hit.get("videos",{})
        version=next((versions.get(k) for k in ("medium","small","large","tiny") if versions.get(k,{}).get("url") and (versions[k].get("size") or 0)<55*1024*1024),None)
        if not version:continue
        result.append({"id":hit.get("id"),"url":version["url"],"page":hit.get("pageURL",""),"credit":hit.get("user",""),"duration":hit.get("duration",0)})
    return result

def select_pixabay_scenes(script,limit=8):
    selected=[]
    used=set()
    missing=[]
    for query in scene_queries(script,limit):
        options=search_pixabay_videos(query,limit=8)
        clip=next((item for item in options if item.get("id") not in used),None)
        if clip:
            selected.append(clip)
            used.add(clip.get("id"))
        else:
            missing.append(query)
    if not selected:raise RuntimeError("Aucune vidéo Pixabay trouvée pour ce script.")
    return selected,missing

def search_commons_videos(query, limit=6):
    """Find freely licensed video files on Wikimedia Commons without API keys."""
    params={"action":"query","generator":"search","gsrsearch":"filetype:video "+query[:90],
            "gsrnamespace":6,"gsrlimit":max(5,min(limit*3,30)),
            "prop":"imageinfo","iiprop":"url|size|mime|extmetadata","iiextmetadatafilter":"LicenseShortName|LicenseUrl|Artist|Credit","format":"json"}
    url="https://commons.wikimedia.org/w/api.php?"+urlencode(params)
    with urlopen(Request(url,headers={"User-Agent":"mntage/1.0 (https://github.com/yanisfounas12346-alt/mntage)"}),timeout=25) as response:
        data=json.load(response)
    allowed={"cc0","cc0 1.0","pd","public domain","cc-by-4.0","cc-by-3.0","cc-by-2.0","cc by 4.0","cc by 3.0","cc by 2.0"}
    found=[]
    for page in data.get("query",{}).get("pages",{}).values():
        info=(page.get("imageinfo") or [{}])[0]
        if info.get("mime") not in {"video/webm","video/ogg","video/mp4"}:
            continue
        if not 0 < info.get("size",0) <= 55*1024*1024:
            continue
        meta=info.get("extmetadata",{})
        license_name=meta.get("LicenseShortName",{}).get("value","").strip().lower()
        if license_name not in allowed or not info.get("url"):
            continue
        found.append({"id":page.get("pageid"),"url":info["url"],
                      "page":info.get("descriptionurl",""),
                      "credit":meta.get("Artist",{}).get("value",""),
                      "license":license_name,"title":page.get("title","")})
    terms=[w for w in query.lower().split() if len(w)>2]
    found.sort(key=lambda item: (-sum(w in item["title"].lower() for w in terms),
                                  info_size_score(item["title"]),item["title"]))
    return found[:limit]

def info_size_score(title):
    """Prefer descriptively titled clips over anonymous file names."""
    return 1 if len(title)<15 else 0

def select_commons_scenes(script,limit=8):
    """Select distinct licensed footage; never silently substitute unrelated visuals."""
    chosen=[]
    used=set()
    missing=[]
    for query in scene_queries(script,limit):
        try:options=search_commons_videos(query,limit=8)
        except Exception as exc:raise RuntimeError("Recherche Wikimedia Commons indisponible : "+str(exc)) from exc
        item=next((v for v in options if v["id"] not in used),None)
        if item:
            chosen.append(item)
            used.add(item["id"])
        else:missing.append(query)
    if not chosen:raise RuntimeError("Aucun clip vidéo libre trouvé sur Wikimedia Commons. Essaie des scènes plus concrètes ou importe tes MP4.")
    return chosen,missing
