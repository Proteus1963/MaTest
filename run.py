from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import httpx
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware

# Import other modules as needed
from filmpertutti import filmpertutti
from streamingcommunity import streaming_community
from tantifilm import tantifilm
from lordchannel import lordchannel
from streamingwatch import streamingwatch
from okru import okru_get_url
from animeworld import animeworld
from dictionaries import okru, STREAM
import config

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize FastAPI app and rate limiter
app = FastAPI()
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# Configuration variables
FILMPERTUTTI = config.FILMPERTUTTI
STREAMINGCOMMUNITY = config.STREAMINGCOMMUNITY
MYSTERIUS = config.MYSTERIUS
TUTTIFILM = config.TUTTIFILM
TF_DOMAIN = config.TF_DOMAIN
LORDCHANNEL = config.LORDCHANNEL
STREAMINGWATCH = config.STREAMINGWATCH
ANIMEWORLD = config.ANIMEWORLD
HOST = config.HOST
PORT = int(config.PORT)
HF = config.HF
if HF == "1":
    HF = "🤗️"
else:
    HF = ""
if MYSTERIUS == "1":
    from cool import cool

# Define the manifest
MANIFEST = {
    "id": "org.stremio.mammamia",
    "version": "1.0.5",
    "catalogs": [
        {"type": "tv", "id": "tv_channels", "name": "TV Channels"}
    ],
    "resources": ["stream", "catalog", "meta"],
    "types": ["movie", "series", "tv"],
    "name": "Mamma Mia",
    "description": "Addon providing HTTPS Streams for Italian Movies,Series and Live TV! Note that you need to have Kitsu Addon installed in order to watch Anime",
    "logo": "https://creazilla-store.fra1.digitaloceanspaces.com/emojis/49647/pizza-emoji-clipart-md.png"
}

def respond_with(data):
    resp = JSONResponse(content=data)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = '*'
    return resp

@app.get('/manifest.json')
def addon_manifest():
    return respond_with(MANIFEST)

@app.get('/')
def root():
    return "Hello, this is a Stremio Addon providing HTTPS Stream for Italian Movies/Series, to install it add /manifest.json to the url and then add it into the Stremio search bar"

@app.get('/catalog/{type}/{id}.json')
@limiter.limit("5/second")
def addon_catalog(request: Request, type: str, id: str):
    if type != "tv":
        raise HTTPException(status_code=404)

    catalogs = {"metas": []}
    for channel in STREAM["channels"]:
        catalogs["metas"].append({
            "id": channel["id"],
            "type": "tv",
            "name": channel["title"],
            "poster": channel.get("poster", ""),  # Add poster URL if available
            "description": f"Watch {channel['title']}"
        })

    return respond_with(catalogs)

@app.get('/meta/tv/{id}.json')
@limiter.limit("5/second")
def addon_meta(request: Request, id: str):
    # Find the channel by ID
    channel = next((ch for ch in STREAM['channels'] if ch['id'] == id), None)
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    meta = {
        'meta': {
            'id': channel['id'],
            'type': 'tv',
            'name': channel['name'],
            'poster': channel.get('poster', ''),
            'posterShape': 'landscape',
            'description': channel.get('title', ''),
            'background': channel.get('poster', ''),  # Example of using the same poster as background
            'logo': channel.get('poster', ''),  # Example of using the same poster as logo
            'url': channel.get('url', ''),  # Using the stream URL as a website link
        }
    }
    return respond_with(meta)

@app.get('/stream/{type}/{id}.json')
@limiter.limit("5/second")
async def addon_stream(request: Request, type: str, id: str):
    if type not in MANIFEST['types']:
        raise HTTPException(status_code=404)   
    
    streams = {'streams': []}
    async with httpx.AsyncClient() as client:
        if type == "tv":
            for channel in STREAM["channels"]:
                if channel["id"] == id:
                    streams['streams'].append({
                        'title': channel['name'],
                        'url': channel['url']
                    })
                    if id in okru:
                        channel_url = await okru_get_url(id, client)
                        streams['streams'].append({
                            'title': channel['name'] + " OKRU",
                            'url': channel_url
                        })
            if not streams['streams']:
                raise HTTPException(status_code=404)
            return respond_with(streams)
        
        # For movies or series
        if "tt" in id or "tmdb" in id:
            logging.debug(f"Handling movie or series: {id}")
            if "kitsu" in id and ANIMEWORLD == "1":
                animeworld_urls = await animeworld(id, client)
                if animeworld_urls:
                    for i, url in enumerate(animeworld_urls):
                        title = "Original" if i == 0 else "Italian"
                        streams['streams'].append({'title': f'{HF}Animeworld {title}', 'url': url})
            
            if MYSTERIUS == "1":
                results = await cool(id, client)
                if results:
                    for resolution, link in results.items():
                        streams['streams'].append({'title': f'{HF}Mysterious {resolution}', 'url': link})
            
            if STREAMINGCOMMUNITY == "1":
                url_streaming_community, url_720_streaming_community, quality_sc = await streaming_community(id, client)
                if url_streaming_community:
                    streams['streams'].append({'title': f'{HF}StreamingCommunity 1080p Max', 'url': url_streaming_community})
                    if quality_sc == "1080":
                        streams['streams'].append({'title': f'{HF}StreamingCommunity 720p Max', 'url': url_720_streaming_community})
                    else:
                        streams['streams'].append({'title': f'{HF}StreamingCommunity 720p Max', 'url': url_streaming_community})
            
            if LORDCHANNEL == "1":
                url_lordchannel, quality_lordchannel = await lordchannel(id, client)
                if url_lordchannel:
                    if quality_lordchannel == "FULL HD":
                        streams['streams'].append({'title': f'{HF}LordChannel 1080p', 'url': url_lordchannel})
                    else:
                        streams['streams'].append({'title': f'{HF}LordChannel 720p', 'url': url_lordchannel})
            
            if FILMPERTUTTI == "1":
                url_filmpertutti = await filmpertutti(id, client)
                if url_filmpertutti:
                    streams['streams'].append({'title': 'Filmpertutti', 'url': url_filmpertutti})
            
            if TUTTIFILM == "1":
                url_tuttifilm = await tantifilm(id, client)
                if url_tuttifilm:
                    if not isinstance(url_tuttifilm, str):
                        for title, url in url_tuttifilm.items():
                            streams['streams'].append({'title': f'{HF}Tantifilm {title}', 'url': url, 'behaviorHints': {'proxyHeaders': {"request": {"Referer": "https://d000d.com/"}}, 'notWebReady': True}})
            
            if STREAMINGWATCH == "1":
                url_streamingwatch = await streamingwatch(id, client)
                if url_streamingwatch:
                    streams['streams'].append({'title': f'{HF}StreamingWatch 720p', 'url': url_streamingwatch})
        
        if not streams['streams']:
            raise HTTPException(status_code=404)

    return respond_with(streams)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("run:app", host=HOST, port=PORT, log_level="info")
