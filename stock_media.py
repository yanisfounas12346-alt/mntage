"""Optional Pexels stock media search; attribution and license review remain user's responsibility."""
import os,json,re
from urllib.request import Request,urlopen
from urllib.parse import urlencode

def _api(endpoint,params):
    key=os.environ.get("PEXELS_API_KEY","").strip()
    if not key:raise RuntimeError("Ajoute PEXELS_API_KEY dans PowerShell.")
    url="https://api.pexels.com/"+endpoint+"?"+urlencode(params)
    with urlopen(Request(url,headers={"Authorization":key,"User-Agent":"mntage/0.4"}),timeout=20) as response:
        return json.load(response)

def scene_queries(script,limit=8):
    sentences=[s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+",script) if s.strip()]
    stop={"pour","dans","avec","sans","cette","comme","quand","alors","mais","plus","tout","tous","elles","nous","vous","leur","être","avoir","est","une","des","les","que","qui","sur","par","pas","son","ses","aux","ces","cela","c'est","d'un","d'une","dans","même","encore","peut","déjà","fait","très","vois","sont","dont","cette"}
    queries=[]
    for sentence in sentences[:limit]:
        words=[w.lower() for w in re.findall(r"[\wÀ-ÿ'-]+",sentence) if len(w)>3 and w.lower() not in stop]
        concepts=[(("nuage","ciel","visage"),"face shaped clouds sky"),(("cerveau","neurone"),"human brain science"),(("illusion","optique"),"optical illusion"),(("yeux","regard"),"close up human eye"),(("nature","forêt"),"cinematic forest"),(("espace","planète"),"space galaxy"),(("océan","mer"),"ocean waves"),(("ville","rue"),"city street")]
        query=next((english for keywords,english in concepts if any(k in sentence.lower() for k in keywords)),None)
        if not query:query=" ".join(words[:3]) or "cinematic nature"
        queries.append(query)
    return queries or ["cinematic nature"]

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
    with urlopen(Request(url,headers={"User-Agent":"mntage/0.4"}),timeout=45) as response:
        data=response.read(max_bytes+1)
    if len(data)>max_bytes:raise RuntimeError("Média trop volumineux.")
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
