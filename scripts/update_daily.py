#!/usr/bin/env python3
"""NVPI daily publisher. Source-attributed news + original text explainer + fashion.
Runs via GitHub Actions at 05:30 UTC = 11:00 Asia/Kolkata.
Does NOT upload Facebook content, reuse third-party video, or invent local reporting.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import textwrap
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "daily"
OUT.mkdir(exist_ok=True)
NOW = datetime.now(ZoneInfo("Asia/Kolkata"))
TODAY = NOW.date().isoformat()
NEWS_QUERIES = [
    "Vasai Virar Nalasopara Naigaon property housing railway infrastructure when:7d",
    "Palghar Vasai Virar municipal metro road housing development when:7d",
    "Vasai Virar railway station infrastructure when:7d",
    "Vasai Virar local news when:7d",
    "Nalasopara Naigaon news when:7d",
    "Maharashtra RERA property housing news when:7d",
]
FASHION_QUERIES = [
    "India fashion trends ethnic wear textile designers when:7d",
    "Indian fashion style saree sustainable fashion when:7d",
]
# Facebook TRAVEL niche only: hidden gems, drives, road trips and destinations.
# These are search terms, not automatic Facebook account connections.
TRAVEL_QUERIES = [
    "Maharashtra tourism travel hidden places forts caves road trip when:7d",
    "Maharashtra Goa tourism beaches waterfalls road trip when:7d",
    "Goa beach tourism offbeat travel destination when:7d",
    "Karnataka Andhra Pradesh caves scenic tourist destination when:7d",
    "India highway road trip driving routes tourist travel when:7d",
    "India offbeat travel destinations trekking forts tourism when:7d",
]
TRAVEL_SUBJECTS = (
    "travel", "tourism", "tourist", "destination", "road trip", "roadtrip",
    "scenic", "beach", "fort", "cave", "waterfall", "trek", "hill station",
    "hidden gem", "offbeat", "highway", "route", "monsoon trip",
    "heritage site", "nature trail", "safari", "trip", "getaway",
    "पर्यटन", "यात्रा", "पर्यटक", "समुद्रतट", "किला", "गुफा", "धबधबा",
    "समुद्रकिनारा", "किल्ला", "लेणी"
)
TRAVEL_REGIONS = (
    "maharashtra", "goa", "konkan", "mumbai", "pune", "lonavala",
    "vasai", "virar", "palghar", "sindhudurg", "ratnagiri", "raigad",
    "sahyadri", "kolhapur", "satara", "nashik", "gokarna",
    "karnataka", "belum", "gandikota", "andhra", "murudeshwar",
    "india", "western ghats", "arvalem", "netravali",
)
TRAVEL_EXCLUDE = ("celebrity", "box office", "stock price", "cricket", "tournament",
                  "relationship", "fashion week", "flight attendant", "astrology")

LOCAL_TERMS = ("vasai", "virar", "nalasopara", "naigaon", "palghar", "vvmc",
               "juchandra", "dahanu", "vaitarna", "boisar")
PROPERTY_TERMS = ("housing", "property", "real estate", "metro", "rail", "train",
                  "road", "station", "infrastructure", "development", "building",
                  "rera", "construction", "flood", "civic", "municipal", "water",
                  "drainage", "land", "connectivity", "वसई", "विरार", "नालासोपारा",
                  "नायगाव", "रेल", "प्रकल्प", "रस्ता")
FASHION_TIPS = [
    ("Cotton-first comfort", "For warm weather, breathable cotton and linen layers make a versatile everyday look."),
    ("Saree contrast idea", "A solid blouse can balance a printed saree; try one accent from the border."),
    ("Monsoon-ready styling", "Choose easy-dry fabrics and shoes with reliable grip; keep delicate fabric out of heavy rain."),
    ("Capsule wardrobe", "Build a base of neutral tops and bottoms, then add one statement colour."),
    ("Traditional meets casual", "Pair a simple kurta with straight-cut trousers and minimal accessories."),
    ("Fabric care matters", "Read care labels before washing embellished or heavily dyed garments."),
    ("Everyday ethnic wear", "For daily use, lighter fabrics and manageable silhouettes often feel more practical."),
    ("Denim restyle", "A crisp oversized shirt can dress up jeans without making the outfit complicated."),
    ("Accessories with balance", "Choose either statement earrings or a bold necklace so the look stays intentional."),
    ("Linen look", "Natural creases are part of linen's appeal; try relaxed fits for summer."),
    ("Footwear first", "Comfortable footwear can make a stylish outfit practical for a full working day."),
    ("Slow fashion", "Repair, restyle and rewear favourite clothes before buying another similar piece."),
]
def get_xml(query):
    url = "https://news.google.com/rss/search?" + urlencode({
        "q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"
    })
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (NVPI source-linked headlines; contact via website)"})
    with urlopen(req, timeout=18) as res:
        content = res.read(2_000_000)
    return ET.fromstring(content)

def recent_items(queries, mode):
    seen = set()
    matches = []
    for query in queries:
        try:
            root = get_xml(query)
        except Exception as exc:
            print("RSS unavailable:", str(exc)[:160])
            continue
        for item in root.findall("./channel/item"):
            title = " ".join((item.findtext("title") or "").split())
            link = (item.findtext("link") or "").strip()
            source = (item.findtext("source") or "Google News").strip()
            date_text = item.findtext("pubDate") or ""
            if not title or not link.startswith("https://") or len(title) > 280:
                continue
            key = re.sub(r"\W+", "", title.lower())[:110]
            if key in seen:
                continue
            seen.add(key)
            try:
                published = parsedate_to_datetime(date_text).astimezone(timezone.utc)
            except Exception:
                continue
            age = datetime.now(timezone.utc) - published
            if age < timedelta(hours=-1) or age > timedelta(days=7):
                continue
            ltitle = title.casefold()
            if mode == "news" and not (any(t in ltitle for t in LOCAL_TERMS) or any(t in ltitle for t in PROPERTY_TERMS)):
                continue
            # A locality alone is not enough: keep local/property/infrastructure focus.
            if mode == "fashion" and not any(t in ltitle for t in ("fashion","saree","style","designer","textile","wear","couture","runway","trend","कपड","फॅशन")):
                continue
            if mode == "travel":
                # Keep travel explicitly separate from property and fashion.
                if any(t in ltitle for t in TRAVEL_EXCLUDE):
                    continue
                if not any(t in ltitle for t in TRAVEL_SUBJECTS):
                    continue
                if not any(t in ltitle for t in TRAVEL_REGIONS):
                    continue
            matches.append({
                "title": title, "url": link, "source": source,
                "published_at": published.isoformat(),
                "kind": "Source-linked headline (not independently fact-checked)",
            })
    if mode == "travel":
        # Prefer Maharashtra/Goa road-trip and hidden-destination stories.
        priority = ("maharashtra","goa","konkan","sahyadri","palghar","vasai","virar",
                    "fort","cave","beach","road trip","highway","offbeat","hidden","waterfall")
        matches.sort(key=lambda x:(sum(2 if p in x["title"].casefold() else 0 for p in priority), x["published_at"]),reverse=True)
    else:
        matches.sort(key=lambda x: x["published_at"], reverse=True)
    return matches

def pick(items, previous_titles):
    for item in items:
        if item["title"] not in previous_titles:
            return item
    return None

def get_last():
    p = OUT / "updates.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def select_content():
    old = get_last()
    history = (old.get("recent_news_titles") or [])[-45:]
    news = pick(recent_items(NEWS_QUERIES, "news"), set(history))
    news_is_new = news is not None
    if not news:
        news = old.get("news")
    if news_is_new:
        history.append(news["title"])
    fashion_history = (old.get("recent_fashion_titles") or [])[-45:]
    fashion = pick(recent_items(FASHION_QUERIES, "fashion"), set(fashion_history))
    if fashion:
        fashion_history.append(fashion["title"])
        fashion["kind"] = "Fashion headline · linked to original publication"
    else:
        title, description = FASHION_TIPS[NOW.toordinal() % len(FASHION_TIPS)]
        fashion = {"title": title, "description": description, "url": "",
                   "source": "NVPI original style tip", "published_at": NOW.isoformat(),
                   "kind": "Everyday style advice (not breaking news)"}
    travel_history = (old.get("recent_travel_titles") or [])[-45:]
    travel = pick(recent_items(TRAVEL_QUERIES, "travel"), set(travel_history))
    travel_is_new = travel is not None
    if travel:
        travel_history.append(travel["title"])
        travel["kind"] = "Source-attributed travel headline (not independently verified)"
    else:
        # Keep the previous headline rather than inventing travel news.
        travel = old.get("travel")
    if news:
        text_for_video = news["title"]
        attribution = news["source"]
    else:
        text_for_video = "Naigaon to Virar: before buying, verify RERA, approvals and on-ground conditions."
        attribution = "NVPI original buyer-awareness tip"
    return {
        "updated_at": NOW.isoformat(), "run_date_ist": TODAY,
        "schedule": "Daily 11:00 AM IST (GitHub Actions; timing can vary)",
        "news": news, "new_news_today": news_is_new,
        "travel": travel, "new_travel_today": travel_is_new,
        "recent_travel_titles": travel_history[-45:],
        "fashion": fashion, "recent_news_titles": history[-45:],
        "recent_fashion_titles": fashion_history[-45:],
        "video": {
            "src": "/daily/today-explainer.mp4",
            "title": "NVPI Daily Property Explainer",
            "headline": text_for_video, "source": attribution,
            "kind": "Original text explainer · NO actual location footage",
            "made_at": NOW.isoformat()
        },
        "notice": "Source headlines are attributed, not independently verified. Verify current facts before property decisions."
    }

def get_font(size):
    from PIL import ImageFont
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()

def wrapped(draw, text, font, width):
    words = text.split()
    lines, line = [], ""
    for word in words:
        trial = (line + " " + word).strip()
        if line and draw.textbbox((0, 0), trial, font=font)[2] > width:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return lines[:12]

def slide(path, index, headline, source):
    from PIL import Image, ImageDraw
    W, H = 720, 1280
    im = Image.new("RGB", (W, H), "#09283e")
    draw = ImageDraw.Draw(im)
    draw.rounded_rectangle((34, 40, W-34, H-45), radius=45,
                           fill="#11374c", outline="#b47d5f", width=3)
    draw.rectangle((65, 100, 185, 107), fill="#e2ab80")
    tiny = get_font(28)
    body = get_font(44)
    hfont = get_font(68)
    draw.text((67, 140), "NVPI / PROPERTY DESK", fill="#e2ab80", font=tiny)
    if index == 0:
        top = "TODAY'S PROPERTY UPDATE"
        paragraphs = [headline]
    elif index == 1:
        top = "SOURCE-ATTRIBUTED"
        paragraphs = ["Published headline:", headline]
    else:
        top = "READ BEFORE YOU SHARE"
        paragraphs = ["This video is a text explainer.", "Check the original source for current facts."]
    draw.text((68, 270), top, fill="white", font=get_font(38))
    y = 390
    for para in paragraphs:
        for line in wrapped(draw, para, body, W-135)[:9]:
            draw.text((68, y), line, fill="#f3f0eb", font=body)
            y += 70
        y += 34
    draw.text((68, H-260), "SOURCE / " + source[:34], fill="#e2ab80", font=get_font(24))
    draw.text((68, H-195), "NAIGAON • VASAI • NALASOPARA • VIRAR",
              fill="white", font=get_font(18))
    draw.text((68, H-140), TODAY + "  |  Original NVPI explainer", fill="#c0d4dc", font=get_font(20))
    im.save(path)

def render_video(headline, source):
    with tempfile.TemporaryDirectory() as d:
        folder = Path(d)
        clips = []
        for i in range(3):
            frame = folder / ("frame%d.png" % i)
            clip = folder / ("clip%d.mp4" % i)
            slide(frame, i, headline, source)
            subprocess.run([
                "ffmpeg","-hide_banner","-loglevel","error","-y",
                "-loop","1","-i",str(frame),"-t","4",
                "-r","24","-c:v","libx264","-preset","fast",
                "-crf","29","-pix_fmt","yuv420p","-movflags","+faststart",
                str(clip)
            ], check=True)
            clips.append(clip)
        concat = folder / "clips.txt"
        concat.write_text("".join("file '%s'\n" % str(p) for p in clips), encoding="utf-8")
        target = OUT / "today-explainer.mp4"
        subprocess.run([
            "ffmpeg","-hide_banner","-loglevel","error","-y",
            "-f","concat","-safe","0","-i",str(concat),
            "-c","copy","-movflags","+faststart",str(target)
        ], check=True)
        if target.stat().st_size < 1000:
            raise RuntimeError("Empty video file")
        print("Explainer video:", target.stat().st_size, "bytes")

def main():
    data = select_content()
    render_video(data["video"]["headline"], data["video"]["source"])
    (OUT / "updates.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Published daily package:", TODAY,
          "news-new:", data["new_news_today"],
          "news:", (data["news"] or {}).get("title","none")[:90],
          "fashion:", data["fashion"]["title"][:90],
          "travel-new:", data["new_travel_today"],
          "travel:", (data["travel"] or {}).get("title","none")[:90])

if __name__ == "__main__":
    main()
