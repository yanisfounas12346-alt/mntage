"""Optional Pexels image search. Requires free user API key and review of licenses."""
import os
import json
from urllib.request import Request, urlopen
from urllib.parse import urlencode

def search_images(query: str, limit: int = 4):
    key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("PEXELS_API_KEY manquante.")
    url = "https://api.pexels.com/v1/search?" + urlencode({"query":query[:100],"per_page":min(10,max(1,limit)),"orientation":"portrait"})
    req = Request(url,headers={"Authorization":key,"User-Agent":"mntage/0.2"})
    with urlopen(req,timeout=15) as response:
        data = json.load(response)
    return [{"url":p["src"]["large"],"credit":p.get("photographer",""),"page":p.get("url","")} for p in data.get("photos",[])]

def download_images(items):
    result=[]
    for item in items:
        req=Request(item["url"],headers={"User-Agent":"mntage/0.2"})
        with urlopen(req,timeout=20) as response:
            raw=response.read(8*1024*1024+1)
            if len(raw)>8*1024*1024: raise ValueError("Image trop volumineuse")
            result.append(raw)
    return result
