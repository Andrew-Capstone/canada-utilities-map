"""Download the Alberta Energy Regulator's Enhanced Pipeline shapefile and write Alberta's operating gas pipelines
for index.html (the map):

- data/aer-gas-main.js   operating gas lines 4" (114.3 mm) and up; loads when you pan to Alberta
- data/aer-gas-small.js  operating gas lines under 4"; loads only when that legend row is ticked

Source: AER Enhanced Pipeline Graphics File (all AER-approved oil and gas pipelines, excluding low-pressure
distribution lines). AER terms: informational use; no unauthorized commercial reproduction.

Run:  python fetch_aer_gas.py      (needs pyshp:  python -m pip install --user pyshp)
"""
import io
import json
import os
import sys
import tempfile
import time
import urllib.request
import zipfile

import shapefile

from fetch_infrastructure import OUT_DIR
from fetch_telecom import simplify, write_js

URL = "https://www.aer.ca/data/pipeline/Pipelines_SHP.zip"
SHP = "Pipelines_SHP/Pipelines_GCS_NAD83"   # the lon/lat (NAD83) copy; the zip also has a 10TM copy
GAS = {"Natural Gas": "sweet", "Sour Natural Gas": "sour", "Fuel Gas": "fuel"}
SMALL_MM = 114.3   # 4-inch nominal pipe outside diameter
TOL = 0.0002       # ~20 m simplification: route scale, about half the file size


def num(v):
    try:
        return round(float(v), 1)
    except (TypeError, ValueError):
        return None


def parts(shape):
    idx = list(shape.parts) + [len(shape.points)]
    return [shape.points[i:j] for i, j in zip(idx, idx[1:])]


def convert(reader):
    """-> (main, small): {"ops": [company names], "f": [[[[lat, lon], ...], op_index, diam_mm, maop_kpa, gas, licence], ...]}"""
    out = {"main": {"ops": [], "f": []}, "small": {"ops": [], "f": []}}
    op_index = {"main": {}, "small": {}}
    for sr in reader.iterShapeRecords(fields=["SUBSTANCE1", "SEG_STATUS", "OUT_DIAMET", "PIPE_MAOP", "COMP_NAME", "LIC_LI_NO"]):
        a = sr.record
        if a["SUBSTANCE1"] not in GAS or a["SEG_STATUS"] != "Operating":
            continue
        diam = num(a["OUT_DIAMET"])
        key = "small" if diam is None or diam < SMALL_MM else "main"
        ops, idx = out[key]["ops"], op_index[key]
        if a["COMP_NAME"] not in idx:
            idx[a["COMP_NAME"]] = len(ops)
            ops.append(a["COMP_NAME"])
        for part in parts(sr.shape):
            pts = simplify([list(p) for p in part], TOL)
            if len(pts) >= 2:
                out[key]["f"].append([[[round(y, 5), round(x, 5)] for x, y in pts], idx[a["COMP_NAME"]], diam,
                                      num(a["PIPE_MAOP"]), GAS[a["SUBSTANCE1"]], a["LIC_LI_NO"]])
    return out["main"], out["small"]


if __name__ == "__main__":
    sys.setrecursionlimit(100000)   # simplify() recurses on long pipelines
    assert num("60.3") == 60.3 and num("") is None
    os.makedirs(OUT_DIR, exist_ok=True)
    print("Downloading AER pipelines (~170 MB) …", flush=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        z = zipfile.ZipFile(io.BytesIO(r.read()))
    with tempfile.TemporaryDirectory() as tmp:
        z.extractall(tmp, [m for m in z.namelist() if m.startswith(SHP)])
        with shapefile.Reader(os.path.join(tmp, SHP)) as reader:   # close before Windows deletes the temp dir
            main, small = convert(reader)
    stamp = time.strftime("%Y-%m-%d")
    for key, data in (("main", main), ("small", small)):
        name = f"aer-gas-{key}.js"
        data.update(set=key, date=stamp)
        write_js(name, "AER_LOADED", data)
        print(f"{name}: {len(data['f']):,} segments, {os.path.getsize(os.path.join(OUT_DIR, name)) / 1e6:.1f} MB")
