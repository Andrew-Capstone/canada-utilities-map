"""Download provincial regulators' gas pipeline data for index.html (the map), in the same format as fetch_aer_gas.py:

- data/gas-bc.js        BC Energy Regulator permitted pipeline segments, active (Open Government Licence - BC).
                        BCER types lines by function, not substance; in BC these are mostly gas.
- data/gas-sk.js        Saskatchewan licensed gas pipelines, operating (Ministry of Energy and Resources)
- data/gas-sk-flow.js   Saskatchewan gas flowlines, operating (loads only when ticked on the map)
- data/gas-on.js        Ontario natural gas pipelines from the MNRF Utility Line layer (Open Government Licence - Ontario)

Manitoba publishes no pipeline data; there the map relies on the CER systems and OpenStreetMap.

Run:  python fetch_gas_regulators.py            (all)
      python fetch_gas_regulators.py bc sk      (only these: bc, sk, on)
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

from fetch_infrastructure import OUT_DIR
from fetch_telecom import simplify, write_js

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
TOL = 0.0002   # ~20 m, same as the Alberta data
SK = "https://gis.saskatchewan.ca/arcgis/rest/services/Economy/Pipelines/MapServer"
SK_GAS = "SUBSTANCE IN ('Natural Gas','Sour Natural Gas','Fuel Gas') AND SEGMENTSTATUS = 'Operating'"
ON = "https://ws.lioservices.lrc.gov.on.ca/arcgis2/rest/services/LIO_OPEN_DATA/LIO_Open05/MapServer/11"
BC = ("https://openmaps.gov.bc.ca/geo/pub/wfs?service=WFS&version=2.0.0&request=GetFeature"
      "&typeName=WHSE_MINERAL_TENURE.OG_PIPELINE_SEGMENT_PERMIT_SP&outputFormat=application/json&srsName=EPSG:4326"
      "&CQL_FILTER=" + urllib.parse.quote("STATUS='Active'"))
GAS_CODE = {"Natural Gas": "sweet", "Sour Natural Gas": "sour", "Fuel Gas": "fuel"}


def get_json(url, tries=4):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=600) as r:
                return json.load(r)
        except Exception as e:  # flaky government servers: retry with backoff
            print(f"  retry {attempt + 1}: {e}", flush=True)
            time.sleep(15 * (attempt + 1))
    raise SystemExit(f"Failed: {url[:120]}")


def arcgis_paths(layer_url, where, fields):
    """Yield (attributes, [path, ...]) from an ArcGIS layer, paging past its record limit, in WGS84."""
    offset = 0
    while True:
        q = urllib.parse.urlencode({"where": where, "outFields": fields, "outSR": 4326, "returnGeometry": "true",
                                    "resultOffset": offset, "resultRecordCount": 1000, "f": "json"})
        d = get_json(f"{layer_url}/query?{q}")
        feats = d.get("features", [])
        for f in feats:
            yield f["attributes"], (f.get("geometry") or {}).get("paths", [])
        if not feats or not d.get("exceededTransferLimit"):
            return
        offset += len(feats)


class Builder:
    """Accumulates features as {"ops": [...], "f": [[[[lat, lon]...], op, diam, maop, gas, licence, group], ...]}."""

    def __init__(self, set_name, source):
        self.d = {"set": set_name, "source": source, "ops": [], "f": []}
        self.idx = {}

    def add(self, paths, op, group, gas=None, lic=None, diam=None, maop=None):
        op = (op or "Unknown operator").strip()
        if op not in self.idx:
            self.idx[op] = len(self.d["ops"])
            self.d["ops"].append(op)
        for path in paths:
            pts = simplify([list(p[:2]) for p in path], TOL)
            if len(pts) >= 2:
                self.d["f"].append([[[round(y, 5), round(x, 5)] for x, y in pts], self.idx[op], diam, maop, gas, lic, group])

    def write(self, name):
        self.d["date"] = time.strftime("%Y-%m-%d")
        write_js(name, "GAS_LOADED", self.d)
        print(f"{name}: {len(self.d['f']):,} segments, {os.path.getsize(os.path.join(OUT_DIR, name)) / 1e6:.1f} MB", flush=True)


def bc_group(line_type):
    return "bc_trans" if line_type == "Transmission" else "bc_other"


if __name__ == "__main__":
    sys.setrecursionlimit(100000)   # simplify() recurses on long pipelines
    assert bc_group("Transmission") == "bc_trans" and bc_group("Gathering") == "bc_other"
    steps = sys.argv[1:] or ["bc", "sk", "on"]
    os.makedirs(OUT_DIR, exist_ok=True)

    if "bc" in steps:
        b = Builder("bc", "BC Energy Regulator")
        for f in get_json(BC)["features"]:
            p, g = f["properties"], f["geometry"] or {}
            if p["LINE_TYPE_DESC"] == "Injection":   # water/CO2 injection, not gas supply
                continue
            paths = [g["coordinates"]] if g.get("type") == "LineString" else g.get("coordinates", []) if g.get("type") == "MultiLineString" else []
            b.add(paths, p["PROPONENT"], bc_group(p["LINE_TYPE_DESC"]), "fuel" if p["LINE_TYPE"] == "FG" else None,
                  f'{p["LINE_TYPE_DESC"]}, project {p["PROJECT_NUMBER"]} seg {p["SEGMENT_NUMBER"]}')
        b.write("gas-bc.js")

    if "sk" in steps:
        fields = "OWNERNAME,SUBSTANCE,LICENCENUMBER,PIPELINENAME"
        for layer, name, group in ((0, "gas-sk.js", "sk_pipe"), (1, "gas-sk-flow.js", "sk_flow")):
            b = Builder("sk-flow" if layer else "sk", "Saskatchewan Ministry of Energy and Resources")
            for a, paths in arcgis_paths(f"{SK}/{layer}", SK_GAS, fields):
                lic = " · ".join(x for x in (a.get("PIPELINENAME"), a.get("LICENCENUMBER") and f"licence {a['LICENCENUMBER']}") if x)
                b.add(paths, a.get("OWNERNAME"), group, GAS_CODE.get(a.get("SUBSTANCE")), lic or None)
            b.write(name)

    if "on" in steps:
        b = Builder("on", "Ontario Ministry of Natural Resources (Utility Line)")
        where = "CLASS_SUBTYPE LIKE '%Natural Gas%' AND (OPERATING_STATUS_IND IS NULL OR OPERATING_STATUS_IND <> 'No')"
        for a, paths in arcgis_paths(ON, where, "CLASS_SUBTYPE,LOCATION_DESCR,GEOG_UNIT_DESCR"):
            b.add(paths, a.get("LOCATION_DESCR") or "Natural gas pipeline", "on_mnrf", "sweet", a.get("GEOG_UNIT_DESCR"))
        b.write("gas-on.js")
