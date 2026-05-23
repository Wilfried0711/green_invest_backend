"""
copernicus_service.py
Service Copernicus Sentinel-2 — Green Invest UEMOA
Supporte les plages de dates (date_from / date_to)
"""
import io
import calendar
import requests
import numpy as np
from django.core.cache import cache


# ── BBox UEMOA (lon_min, lat_min, lon_max, lat_max) ─────────────
UEMOA_BBOX = {
    "BEN": [1.0,   6.2,  3.8,  12.4],
    "BFA": [-5.5,  9.4,  2.4,  15.1],
    "CIV": [-8.6,  4.3, -2.5,  10.7],
    "GNB": [-16.7, 10.9,-13.6, 12.7],
    "MLI": [-4.2,  10.1, 4.2,  25.0],
    "NER": [2.1,   11.7, 15.9, 23.5],
    "SEN": [-17.5, 12.3,-11.4, 16.7],
    "TGO": [-0.1,  5.9,  1.8,  11.1],
}

# ── Pays sahéliens : tolérance nuages plus élevée ────────────────
# Mali, Niger, Burkina Faso ont peu de végétation
# et les images sont souvent partiellement couvertes
CLOUD_COVER = {
    "MLI": 60,   # Mali — zone sahélienne/désertique
    "NER": 60,   # Niger — zone sahélienne/désertique
    "BFA": 50,   # Burkina Faso — zone semi-aride
    "BEN": 20,   # Bénin — zone tropicale humide
    "CIV": 20,   # Côte d'Ivoire — zone forestière
    "GNB": 20,   # Guinée-Bissau — zone côtière
    "SEN": 30,   # Sénégal — zone sahélienne mais côtière
    "TGO": 20,   # Togo — zone tropicale
}

# ── EvalScripts Sentinel-2 ───────────────────────────────────────
EVALSCRIPTS = {
    "ndvi": """
        //VERSION=3
        function setup(){return{input:["B04","B08","SCL"],output:{bands:1,sampleType:"FLOAT32"}}}
        function evaluatePixel(s){
          if([3,8,9,10,11].includes(s.SCL)) return[-9999];
          return[(s.B08-s.B04)/(s.B08+s.B04+1e-10)];
        }
    """,
    "ndwi": """
        //VERSION=3
        function setup(){return{input:["B03","B08","SCL"],output:{bands:1,sampleType:"FLOAT32"}}}
        function evaluatePixel(s){
          if([3,8,9,10,11].includes(s.SCL)) return[-9999];
          return[(s.B03-s.B08)/(s.B03+s.B08+1e-10)];
        }
    """,
    "msi": """
        //VERSION=3
        function setup(){return{input:["B08","B11","SCL"],output:{bands:1,sampleType:"FLOAT32"}}}
        function evaluatePixel(s){
          if([3,8,9,10,11].includes(s.SCL)) return[-9999];
          return[s.B11/(s.B08+1e-10)];
        }
    """,
    "evi": """
        //VERSION=3
        function setup(){return{input:["B02","B04","B08","SCL"],output:{bands:1,sampleType:"FLOAT32"}}}
        function evaluatePixel(s){
          if([3,8,9,10,11].includes(s.SCL)) return[-9999];
          return[2.5*(s.B08-s.B04)/(s.B08+6*s.B04-7.5*s.B02+1)];
        }
    """,
}


def get_token():
    """Token OAuth2 Copernicus mis en cache Django."""
    cached = cache.get("cop_token")
    if cached:
        return cached

    from django.conf import settings
    r = requests.post(
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE"
        "/protocol/openid-connect/token",
        data={"grant_type":    "client_credentials",
              "client_id":     settings.COP_CLIENT_ID,
              "client_secret": settings.COP_CLIENT_SECRET},
        timeout=15
    )
    r.raise_for_status()
    data = r.json()
    cache.set("cop_token", data["access_token"], timeout=data["expires_in"] - 30)
    return data["access_token"]


def fetch_tiff(pays_iso, index="ndvi", year_month=None,
               date_from=None, date_to=None):
    """
    Appelle la Process API Copernicus et retourne un GeoTIFF en bytes.
    Accepte soit :
      - date_from + date_to  (plage de dates ISO)
      - year_month           (fallback : "YYYY-MM")
    La tolérance nuages est adaptée automatiquement selon le pays.
    """
    if pays_iso not in UEMOA_BBOX:
        raise ValueError(f"Pays inconnu : {pays_iso}")
    if index not in EVALSCRIPTS:
        raise ValueError(f"Indice inconnu : {index}")

    # Construire les dates si non fournies
    if not date_from or not date_to:
        if year_month:
            y, m = map(int, year_month.split("-"))
        else:
            y, m = 2024, 9
        last_day = calendar.monthrange(y, m)[1]
        date_from = f"{y}-{m:02d}-01T00:00:00Z"
        date_to   = f"{y}-{m:02d}-{last_day}T23:59:59Z"

    # Tolérance nuages adaptée selon le pays
    cloud_cover = CLOUD_COVER.get(pays_iso, 30)

    payload = {
        "input": {
            "bounds": {
                "bbox": UEMOA_BBOX[pays_iso],
                "properties": {
                    "crs": "http://www.opengis.net/def/crs/EPSG/0/4326"
                }
            },
            "data": [{
                "type": "sentinel-2-l2a",
                "dataFilter": {
                    "timeRange": {"from": date_from, "to": date_to},
                    "maxCloudCoverage": cloud_cover
                }
            }]
        },
        "output": {
            "width":  512,
            "height": 512,
            "responses": [{
                "identifier": "default",
                "format": {"type": "image/tiff"}
            }]
        },
        "evalscript": EVALSCRIPTS[index]
    }

    r = requests.post(
        "https://sh.dataspace.copernicus.eu/api/v1/process",
        headers={"Authorization": f"Bearer {get_token()}",
                 "Content-Type":  "application/json"},
        json=payload,
        timeout=90
    )
    r.raise_for_status()
    return r.content


def compute_stats(tiff_bytes):
    """Calcule les statistiques depuis un GeoTIFF."""
    try:
        import rasterio
        with rasterio.open(io.BytesIO(tiff_bytes)) as src:
            arr   = src.read(1).astype(float)
            valid = arr[arr != -9999]

            if len(valid) == 0:
                return {"error": "Aucune donnée valide (nuages)"}

            return {
                "mean":     round(float(np.mean(valid)),   3),
                "max":      round(float(np.max(valid)),    3),
                "min":      round(float(np.min(valid)),    3),
                "std":      round(float(np.std(valid)),    3),
                "p10":      round(float(np.percentile(valid, 10)), 3),
                "p90":      round(float(np.percentile(valid, 90)), 3),
                "coverage": round(len(valid) / arr.size * 100, 1),
            }
    except ImportError:
        return {"error": "rasterio non installé — pip install rasterio"}


def get_ndvi_all_countries(index="ndvi", year_month="2024-09"):
    """Compatibilité : appelle fetch pour les 8 pays avec un mois simple."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    results = {}

    def fetch_one(iso):
        try:
            tiff  = fetch_tiff(iso, index, year_month=year_month)
            stats = compute_stats(tiff)
            return iso, {"ok": True, "pays": iso, **stats}
        except Exception as e:
            return iso, {"ok": False, "pays": iso, "error": str(e)}

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fetch_one, iso): iso for iso in UEMOA_BBOX}
        for future in as_completed(futures):
            iso, result = future.result()
            results[iso] = result

    return results
