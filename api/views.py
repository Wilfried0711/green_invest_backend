"""
views.py — Endpoints API Green Invest
Supporte les plages de dates (date_from / date_to) pour Copernicus
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
import requests as req

from .copernicus_service import (
    get_token,
    fetch_tiff,
    compute_stats,
    get_ndvi_all_countries,
    UEMOA_BBOX,
    EVALSCRIPTS,
)
from concurrent.futures import ThreadPoolExecutor, as_completed


# ── /api/status/ ─────────────────────────────────────────────────
@require_http_methods(["GET"])
def status(request):
    """Vérifie la connexion Copernicus — lit les clés depuis les headers."""
    try:
        cid    = request.headers.get('X-Cop-Id')
        secret = request.headers.get('X-Cop-Secret')

        if cid and secret:
            r = req.post(
                "https://identity.dataspace.copernicus.eu/auth/realms/CDSE"
                "/protocol/openid-connect/token",
                data={"grant_type": "client_credentials",
                      "client_id": cid, "client_secret": secret},
                timeout=15
            )
            r.raise_for_status()
            data = r.json()
            cache.set("cop_token", data["access_token"],
                      timeout=data["expires_in"] - 30)
            return JsonResponse({
                "ok": True,
                "message": "Copernicus connecté",
                "expires_in": data["expires_in"]
            })
        else:
            token = get_token()
            return JsonResponse({"ok": True, "message": "Copernicus connecté"})

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


# ── /api/ndvi/ ───────────────────────────────────────────────────
@require_http_methods(["GET"])
def ndvi(request):
    """
    NDVI pour UN pays.
    GET params: pays, index, period (YYYY-MM) OU date_from + date_to
    """
    pays   = request.GET.get("pays",   "BEN").upper()
    index  = request.GET.get("index",  "ndvi").lower()
    date_from = request.GET.get("date_from", None)
    date_to   = request.GET.get("date_to",   None)

    if not date_from or not date_to:
        period = request.GET.get("period", "2024-09")
        y, m = map(int, period.split("-"))
        import calendar
        last_day = calendar.monthrange(y, m)[1]
        date_from = f"{y}-{m:02d}-01T00:00:00Z"
        date_to   = f"{y}-{m:02d}-{last_day}T23:59:59Z"

    if pays not in UEMOA_BBOX:
        return JsonResponse({"ok": False, "error": f"Pays inconnu: {pays}"}, status=400)

    try:
        tiff  = fetch_tiff(pays, index, date_from=date_from, date_to=date_to)
        stats = compute_stats(tiff)
        return JsonResponse({"ok": True, "pays": pays, "index": index,
                             "date_from": date_from, "date_to": date_to, **stats})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


# ── /api/ndvi/all/ ───────────────────────────────────────────────
@require_http_methods(["GET"])
def ndvi_all(request):
    """
    NDVI pour les 8 pays UEMOA en parallèle.
    GET params: index, date_from + date_to OU period (YYYY-MM)
    """
    index     = request.GET.get("index",     "ndvi").lower()
    date_from = request.GET.get("date_from", None)
    date_to   = request.GET.get("date_to",   None)

    if not date_from or not date_to:
        period = request.GET.get("period", "2024-09")
        y, m = map(int, period.split("-"))
        import calendar
        last_day = calendar.monthrange(y, m)[1]
        date_from = f"{y}-{m:02d}-01T00:00:00Z"
        date_to   = f"{y}-{m:02d}-{last_day}T23:59:59Z"

    try:
        results = _fetch_all_countries(index, date_from, date_to)
        return JsonResponse({"ok": True, "index": index,
                             "date_from": date_from, "date_to": date_to,
                             "data": results})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


# ── /api/humidity/ ───────────────────────────────────────────────
@require_http_methods(["GET"])
def humidity(request):
    """Humidité via MSI et NDWI pour les 8 pays."""
    date_from = request.GET.get("date_from", None)
    date_to   = request.GET.get("date_to",   None)

    if not date_from or not date_to:
        period = request.GET.get("period", "2024-09")
        y, m = map(int, period.split("-"))
        import calendar
        last_day = calendar.monthrange(y, m)[1]
        date_from = f"{y}-{m:02d}-01T00:00:00Z"
        date_to   = f"{y}-{m:02d}-{last_day}T23:59:59Z"

    try:
        msi_data  = _fetch_all_countries("msi",  date_from, date_to)
        ndwi_data = _fetch_all_countries("ndwi", date_from, date_to)
        combined  = {
            iso: {"pays": iso, "msi": msi_data.get(iso, {}),
                  "ndwi": ndwi_data.get(iso, {})}
            for iso in UEMOA_BBOX
        }
        return JsonResponse({"ok": True, "date_from": date_from,
                             "date_to": date_to, "data": combined})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


# ── Fonction interne : fetch parallèle tous pays ─────────────────
def _fetch_all_countries(index, date_from, date_to):
    """Récupère les données satellite pour les 8 pays en parallèle."""
    results = {}

    def fetch_one(iso):
        try:
            tiff  = fetch_tiff(iso, index, date_from=date_from, date_to=date_to)
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
