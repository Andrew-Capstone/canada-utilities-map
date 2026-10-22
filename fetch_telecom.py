"""Download Canadian fibre/telecom data for index.html (the map):

- data/telecom.js        OpenStreetMap telecom lines, data centres and exchanges (Open Infrastructure Map's telecom layer)
- data/nbd-backbone.js   ISED National Broadband Data: communities without a nearby fibre backbone, and
                         satellite-dependent communities (Open Government Licence - Canada)

Run:  python fetch_telecom.py
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


if __name__ == "__main__":
    sample = [{"wo_backbone_fibre_sans_fibre_dorsale": "1", "satellite_dep": "0", "Longitude": "-66.123456", "Latitude": "46.5", "Name_en": "A"},
              {"wo_backbone_fibre_sans_fibre_dorsale": "0", "satellite_dep": "0", "Longitude": "0", "Latitude": "0", "Name_en": "B"}]
    assert nbd_points(sample) == [[-66.12346, 46.5, "A", 1, 0]]
    os.makedirs(OUT_DIR, exist_ok=True)

    # ISED serves the zip with a text/html content type and rejects non-browser clients
    req = urllib.request.Request(NBD_ZIP, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/zip,*/*"})
    with urllib.request.urlopen(req, timeout=600) as r:
        z = zipfile.ZipFile(io.BytesIO(r.read()))
    pts = nbd_points(csv.DictReader(io.TextIOWrapper(z.open(NBD_CSV), encoding="utf-8-sig")))
    write_js("nbd-backbone.js", "NBD_LOADED", pts)
    print(f"ISED: {len(pts):,} flagged communities")

    elements = fetch("CA", TELECOM_QUERY)
    if elements is None:
        sys.exit("Overpass failed for telecom data; re-run later.")
    fc = convert(elements)
    write_js("telecom.js", "TELECOM_LOADED", fc)
    print(f"OpenStreetMap telecom: {len(fc['features']):,} features")
