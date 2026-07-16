"""
IW-19 VideoSearch — Google/Bing Video Results
Iron Warrior #19 — Vidéo, thumbnails + duration.
Aucun dédié sur RapidAPI.
"""
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import sys
sys.path.insert(0, '/home/user/iron_warriors/shared')
from base import create_app, fetch_html, clean_text, get_timestamp, measure_latency
import time

app = create_app("IW-19 VideoSearch", "Google/Bing video results — thumbnails + duration")

class VideoResult(BaseModel):
    title: str
    url: str
    source: Optional[str] = None
    duration: Optional[str] = None
    thumbnail_url: Optional[str] = None
    uploaded: Optional[str] = None
    position: int

class VideoResponse(BaseModel):
    query: str
    engine: str
    results: List[VideoResult]
    timestamp: str
    latency_ms: int

@app.get("/search", response_model=VideoResponse)
async def video_search(
    q: str = Query(..., description="Video search query"),
    engine: str = Query("google", description="google or bing"),
    num: int = Query(20, ge=1, le=50),
    gl: str = Query("us"),
    hl: str = Query("en"),
):
    start = time.time()

    if engine == "google":
        url = f"https://www.google.com/search?q={quote_plus(q)}&tbm=vid&num={num}&gl={gl}&hl={hl}"
        try:
            html = await fetch_html(url)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Google Video fetch failed: {e}")

        soup = BeautifulSoup(html, 'html.parser')
        results = []
        seen = set()

        for div in soup.find_all('div', class_='g') or soup.find_all('div', class_='ZkmD2'):
            h3 = div.find('h3')
            link = div.find('a', href=True)
            source_tag = div.find('div', class_='UPmit') or div.find('span', class_='eNNCq')
            duration_tag = div.find('span', class_='rQMQod') or div.find('div', class_='MmBeae')
            img_tag = div.find('img')
            uploaded_tag = div.find('span', class_='r0bn4c')

            if h3 and link:
                href = link['href']
                if href.startswith('/url?q='):
                    href = href.split('/url?q=')[1].split('&')[0]
                if href in seen or not href.startswith('http'):
                    continue
                seen.add(href)
                results.append(VideoResult(
                    title=clean_text(h3.get_text()),
                    url=href,
                    source=clean_text(source_tag.get_text()) if source_tag else None,
                    duration=clean_text(duration_tag.get_text()) if duration_tag else None,
                    thumbnail_url=img_tag.get('src') if img_tag else None,
                    uploaded=clean_text(uploaded_tag.get_text()) if uploaded_tag else None,
                    position=len(results) + 1,
                ))
                if len(results) >= num:
                    break

    elif engine == "bing":
        url = f"https://www.bing.com/videos/search?q={quote_plus(q)}&count={num}"
        try:
            html = await fetch_html(url)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Bing Video fetch failed: {e}")

        soup = BeautifulSoup(html, 'html.parser')
        results = []
        seen = set()

        for div in soup.find_all('div', class_='mc_vtvc') or soup.find_all('div', class_='vrhtitle'):
            title_tag = div.find('a', class_='mc_vtvc_title') or div.find('a', href=True)
            duration_tag = div.find('span', class_='mc_vtvc_dur')
            img_tag = div.find('img')
            source_tag = div.find('div', class_='mc_vtvc_meta')

            if title_tag and title_tag.get('href'):
                href = title_tag['href']
                if href in seen:
                    continue
                seen.add(href)
                results.append(VideoResult(
                    title=clean_text(title_tag.get_text()),
                    url=href,
                    duration=clean_text(duration_tag.get_text()) if duration_tag else None,
                    thumbnail_url=img_tag.get('src') if img_tag else None,
                    source=clean_text(source_tag.get_text()) if source_tag else None,
                    position=len(results) + 1,
                ))
                if len(results) >= num:
                    break
    else:
        raise HTTPException(status_code=400, detail="Engine must be 'google' or 'bing'")

    return VideoResponse(
        query=q, engine=engine, results=results,
        timestamp=get_timestamp(), latency_ms=measure_latency(start),
    )
