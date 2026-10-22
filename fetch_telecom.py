"""Download Canadian fibre/telecom data for index.html (the map):

- data/telecom.js        OpenStreetMap telecom lines, data centres and exchanges (Open Infrastructure Map's telecom layer)
- data/nbd-backbone.js   ISED National Broadband Data: communities without a nearby fibre backbone, and
                         satellite-dependent communities (Open Government Licence - Canada)
- data/rail-mainlines.js OpenStreetMap mainline railways, shown as a stand-in for long-haul fibre corridors
                         (no public route data exists for Canada's carrier backbones)

Run:  python fetch_telecom.py                 (all three)
      python fetch_telecom.py rail telecom    (only these steps: nbd, telecom, rail)
"""
import csv
import io
import json
import os
import sys
import urllib.request
import zipfile

from fetch_infrastructure import OUT_DIR, convert, fetch

TELECOM_QUERY = """[out:json][timeout:600];
area["ISO3166-1"="CA"][admin_level=2]->.c;
(way["communication"="line"](area.c);
 way["telecom"~"^(line|cable)$"](area.c);
 nw["telecom"~"^(data_center|exchange)$"](area.c););
out geom tags;"""
RAIL_QUERY = """[out:json][timeout:600];
area["ISO3166-1"="CA"][admin_level=2]->.c;
way["railway"="rail"]["usage"="main"][!"service"](area.c);
out geom tags;"""
NBD_ZIP = "https://ised-isde.canada.ca/app/scr/sittibc/web/api/openData/Map_Data_CSV.zip"
NBD_CSV = "Data_Com_Points_Col_Données.csv"


def write_js(name, call, payload):
    with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as f:
        f.write(f"{call}(")
        json.dump(payload, f, separators=(",", ":"))
        f.write(");\n")


def nbd_points(rows):
    """Keep only flagged communities: [lon, lat, name, no_fibre_backbone, satellite_dependent]."""
    out = []
    for r in rows:
        nofibre, sat = r["wo_backbone_fibre_sans_fibre_dorsale"] == "1", r["satellite_dep"] == "1"
        if nofibre or sat:
            out.append([round(float(r["Longitude"]), 5), round(float(r["Latitude"]), 5), r["Name_en"], int(nofibre), int(sat)])
    return out


def simplify(pts, tol):
    """Ramer-Douglas-Peucker on [lon, lat] points; tol in degrees."""
    if len(pts) < 3:
        return pts
    (x0, y0), (x1, y1) = pts[0], pts[-1]
    dx, dy = x1 - x0, y1 - y0
    norm = (dx * dx + dy * dy) ** 0.5 or 1e-12
    dists = [abs(dy * (x - x0) - dx * (y - y0)) / norm for x, y in pts[1:-1]]
    i = max(range(len(dists)), key=dists.__getitem__)
    if dists[i] <= tol:
        return [pts[0], pts[-1]]
    return simplify(pts[:i + 2], tol)[:-1] + simplify(pts[i + 1:], tol)


if __name__ == "__main__":
    assert simplify([[0, 0], [1, 0.0001], [2, 0]], 0.001) == [[0, 0], [2, 0]]
    assert simplify([[0, 0], [1, 1], [2, 0]], 0.001) == [[0, 0], [1, 1], [2, 0]]
    steps = sys.argv[1:] or ["nbd", "telecom", "rail"]
    sample = [{"wo_backbone_fibre_sans_fibre_dorsale": "1", "satellite_dep": "0", "Longitude": "-66.123456", "Latitude": "46.5", "Name_en": "A"},
              {"wo_backbone_fibre_sans_fibre_dorsale": "0", "satellite_dep": "0", "Longitude": "0", "Latitude": "0", "Name_en": "B"}]
    assert nbd_points(sample) == [[-66.12346, 46.5, "A", 1, 0]]
    os.makedirs(OUT_DIR, exist_ok=True)

    if "nbd" in steps:
        # ISED serves the zip with a text/html content type and rejects non-browser clients
        req = urllib.request.Request(NBD_ZIP, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/zip,*/*"})
        with urllib.request.urlopen(req, timeout=600) as r:
            z = zipfile.ZipFile(io.BytesIO(r.read()))
        pts = nbd_points(csv.DictReader(io.TextIOWrapper(z.open(NBD_CSV), encoding="utf-8-sig")))
        write_js("nbd-backbone.js", "NBD_LOADED", pts)
        print(f"ISED: {len(pts):,} flagged communities")

    if "telecom" in steps:
        elements = fetch("CA", TELECOM_QUERY)
        if elements is None:
            sys.exit("Overpass failed for telecom data; re-run later.")
        fc = convert(elements)
        write_js("telecom.js", "TELECOM_LOADED", fc)
        print(f"OpenStreetMap telecom: {len(fc['features']):,} features")

    if "rail" in steps:
        elements = fetch("CA", RAIL_QUERY)
        if elements is None:
            sys.exit("Overpass failed for rail data; re-run later.")
        fc = convert(elements)
        for f in fc["features"]:
            if f["geometry"]["type"] == "LineString":   # ~50 m tolerance: corridor scale, a fraction of the size
                f["geometry"]["coordinates"] = [[round(x, 4), round(y, 4)] for x, y in simplify(f["geometry"]["coordinates"], 0.0005)]
        write_js("rail-mainlines.js", "RAIL_LOADED", fc)
        print(f"OpenStreetMap mainline railways: {len(fc['features']):,} segments")
