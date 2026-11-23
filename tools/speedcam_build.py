#!/usr/bin/env python3
"""全台測速照相點資料：從政府資料開放平臺抓取 → 整理成 App 用的 data/speedcam_tw.json
資料來源（政府資料開放授權條款-第1版）：
  7320  警政署 測速執法設置點
  13940 警政署 國道公路固定式測速照相地點
只輸出有座標、位於台澎金馬範圍內的點；同位置（約 15 公尺內）且同方向的重複點合併。
"""
import csv, io, json, math, os, re, sys, time, urllib.parse, urllib.request, hashlib, datetime, zipfile

UA = {"User-Agent": "Mozilla/5.0 (ldigi speedcam builder)"}
DATASETS = [7320, 13940]

def get(url, tries=3):
    for i in range(tries):
        try:
            url = urllib.parse.quote(url, safe=":/?&=%#+~,;@!$'()*[]")
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:
            print("retry", url, e, file=sys.stderr); time.sleep(3 * (i + 1))
    raise RuntimeError("download failed: " + url)

def resources(ds):
    meta = json.loads(get(f"https://data.gov.tw/api/v2/rest/dataset/{ds}"))
    res = meta.get("result", meta)
    dist = res.get("distribution") or []
    out = []
    for d in dist:
        u = d.get("resourceDownloadUrl") or d.get("downloadURL") or ""
        f = (d.get("resourceFormat") or d.get("format") or "").upper()
        if u: out.append((f, u))
    print(ds, out, file=sys.stderr)
    return out

def decode(b):
    for enc in ("utf-8-sig", "big5", "cp950"):
        try: return b.decode(enc)
        except Exception: pass
    return b.decode("utf-8", "ignore")

def rows_of(ds):
    for fmt, url in sorted(resources(ds), key=lambda x: 0 if "CSV" in x[0] else 1):
        try:
            b = get(url)
            if b[:2] == b"PK":
                z = zipfile.ZipFile(io.BytesIO(b))
                names = [n for n in z.namelist() if n.lower().endswith((".csv", ".json"))]
                print("zip", z.namelist(), file=sys.stderr)
                if not names: continue
                b = z.read(names[0])
            t = decode(b).strip()
            if t.startswith("[") or t.startswith("{"):
                j = json.loads(t)
                if isinstance(j, dict):
                    for k in ("result", "records", "data", "Data"):
                        if k in j:
                            j = j[k]; break
                    if isinstance(j, dict) and "records" in j: j = j["records"]
                if isinstance(j, list) and j: return j
            else:
                r = list(csv.DictReader(io.StringIO(t)))
                if r: return r
        except Exception as e:
            print("skip", url, e, file=sys.stderr)
    return []

def pick(row, *keys):
    for k in row:
        kk = (k or "").strip().lower()
        for want in keys:
            if want.lower() == kk or want.lower() in kk:
                v = row[k]
                if v not in (None, ""): return str(v).strip()
    return ""

def fnum(s):
    try: return float(re.sub(r"[^0-9.\-]", "", s))
    except Exception: return None

# 拍攝方向文字 → 車頭方位角（度）；雙向回傳 -1
def bearing(s):
    s = s or ""
    if "雙向" in s or not s: return -1
    table = [("北向南", 180), ("往南", 180), ("南下", 180), ("南向北", 0), ("往北", 0), ("北上", 0),
             ("東向西", 270), ("往西", 270), ("西向", 270), ("西向東", 90), ("往東", 90), ("東向", 90)]
    for k, v in table:
        if k in s: return v
    return -1

def kind(s):
    s = s or ""
    if "區間" in s: return "avg"
    if "闖紅燈" in s or "紅燈" in s: return "red"
    if "科技" in s or "違規" in s or "噪音" in s: return "tech"
    return "fix"

pts = []
for ds in DATASETS:
    rows = rows_of(ds)
    print(ds, "rows", len(rows), file=sys.stderr)
    if rows: print(ds, "sample", rows[0], file=sys.stderr)
    for r in rows:
        lat = fnum(pick(r, "Latitude", "緯度"))
        lon = fnum(pick(r, "Longitude", "經度"))
        if lat is None or lon is None: continue
        if lat > 100 and lon < 100: lat, lon = lon, lat
        if not (21.8 <= lat <= 26.5 and 118.0 <= lon <= 122.2): continue
        lim = fnum(pick(r, "limit", "速限")) or 0
        d = pick(r, "direct", "拍攝方向")
        city = pick(r, "CityName", "縣市")
        addr = pick(r, "Address", "設置地點", "設置地址")
        item = pick(r, "取締項目", "型式")
        pts.append({"la": round(lat, 6), "lo": round(lon, 6), "lim": int(lim) if 0 < lim < 200 else 0,
                    "b": bearing(d), "k": kind(item + addr), "c": city[:6], "a": addr[:40],
                    "hw": 1 if ds == 13940 else 0})

# 去重：同方向 15 公尺內只留一筆（國道資料優先）
pts.sort(key=lambda p: -p["hw"])
grid, out = {}, []
for p in pts:
    key = (round(p["la"] / 0.00015), round(p["lo"] / 0.00015), p["b"])
    if key in grid: continue
    grid[key] = 1; out.append(p)

if len(out) < 500:
    print("too few points, keep old file:", len(out), file=sys.stderr); sys.exit(1)

body = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
ver = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
os.makedirs("data", exist_ok=True)
doc = {"v": ver, "n": len(out), "sha": hashlib.sha1(body.encode()).hexdigest()[:12],
       "src": "政府資料開放平臺 7320、13940（政府資料開放授權條款-第1版）", "p": out}
open("data/speedcam_tw.json", "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
open("data/speedcam_tw.meta.json", "w").write(json.dumps({"v": ver, "n": len(out), "sha": doc["sha"]}))
print("points", len(out), "kinds", {k: sum(1 for p in out if p["k"] == k) for k in ("fix", "avg", "red", "tech")}, file=sys.stderr)
