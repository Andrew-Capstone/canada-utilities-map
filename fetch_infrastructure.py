"""Download Canadian power and gas infrastructure from OpenStreetMap (Overpass) into one file per province/territory
(data/CA-XX.js) plus data/index.js, for index.html (the map). This is the same OpenStreetMap data Open Infrastructure
Map draws. The map loads a province's file only when you pan to it.

Run:  python fetch_infrastructure.py              (all provinces and territories)
      python fetch_infrastructure.py CA-NL CA-YT  (only these; others keep their existing files)
Re-run whenever you want fresher data. A province that fails keeps its old file; re-run just that code later. Power lines are transmission/sub-transmission only (power=line|cable);
distribution lines are skipped because they would make the file huge.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

MIRRORS = ["https://overpass-api.de/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]
GAS = '"substance"~"gas",i'
PROVINCES = {"CA-BC": "British Columbia", "CA-AB": "Alberta", "CA-SK": "Saskatchewan", "CA-MB": "Manitoba",
             "CA-ON": "Ontario", "CA-QC": "Quebec", "CA-NB": "New Brunswick", "CA-NS": "Nova Scotia",
             "CA-PE": "Prince Edward Island", "CA-NL": "Newfoundland and Labrador", "CA-YT": "Yukon",
             "CA-NT": "Northwest Territories", "CA-NU": "Nunavut"}
QUERY = f"""[out:json][timeout:600];
area["ISO3166-2"="{{code}}"]->.on;
(way["power"~"^(line|cable)$"](area.on);
 nw["power"~"^(substation|plant)$"](area.on);
 relation["power"="plant"](area.on);
 way["man_made"="pipeline"][{GAS}](area.on);
 nw["pipeline"="substation"](area.on);
 nw["man_made"="petroleum_well"](area.on);
 nwr["man_made"="storage_tank"]["content"~"gas",i](area.on););
out geom tags;"""
KEEP = ("power", "name", "voltage", "operator", "circuits", "ref", "plant:source", "plant:output:electricity",
        "man_made", "pipeline", "substation", "substance", "pressure", "diameter", "usage", "location", "content",
        "telecom", "communication", "telecom:medium", "railway", "usage", "owner")
OUT_DIR = "data"  # .js files (not .json) so the map also works when opened straight from disk


def fetch(code, query=QUERY):
    body = urllib.parse.urlencode({"data": query.replace("{code}", code)}).encode()
    for attempt in range(4):
        for url in MIRRORS:
            try:
                print(f"{code}: querying {url} …", flush=True)
                req = urllib.request.Request(url, body, {"User-Agent": "ontario-capacity-map/1.0"})
                with urllib.request.urlopen(req, timeout=900) as r:
                    return json.load(r)["elements"]
            except Exception as e:  # busy mirror: try the next one
                print(f"  failed: {e}", flush=True)
        time.sleep(30 * (attempt + 1))
    return None


def is_gas(t):
    return "pipeline" in t or t.get("man_made") in ("pipeline", "petroleum_well", "storage_tank")


def to_feature(el):
    tags = {k: v for k, v in el.get("tags", {}).items() if k in KEEP}
    if is_gas(tags):
        tags["gas"] = 1  # the map splits power vs gas on this flag
    rnd = lambda g: [round(g["lon"], 5), round(g["lat"], 5)]
    if el["type"] == "node":
        geom = {"type": "Point", "coordinates": rnd(el)}
    elif el["type"] == "way":
        pts = [rnd(g) for g in el["geometry"]]
        linear = (tags.get("power") in ("line", "cable") or tags.get("man_made") == "pipeline"
                  or tags.get("communication") == "line" or tags.get("telecom") in ("line", "cable")
                  or tags.get("railway") == "rail")
        closed = not linear and len(pts) > 3 and pts[0] == pts[-1]
        geom = {"type": "Polygon", "coordinates": [pts]} if closed else {"type": "LineString", "coordinates": pts}
    else:  # relation (multipolygon): keep outer rings only
        rings = [[rnd(g) for g in m["geometry"]] for m in el.get("members", []) if m.get("role") == "outer" and m.get("geometry")]
        if not rings:
            return None
        geom = {"type": "MultiLineString", "coordinates": rings}
    return {"type": "Feature", "properties": tags, "geometry": geom}


def convert(elements):
    return {"type": "FeatureCollection", "features": [f for f in map(to_feature, elements) if f]}


if __name__ == "__main__":
    assert not is_gas({"telecom": "exchange"}) and is_gas({"pipeline": "substation"})
    # self-check of the conversion on a tiny sample
    sample = [{"type": "way", "tags": {"power": "substation", "name": "A"}, "geometry": [{"lat": 0, "lon": 0}, {"lat": 0, "lon": 1}, {"lat": 1, "lon": 1}, {"lat": 0, "lon": 0}]},
              {"type": "way", "tags": {"power": "line", "voltage": "230000", "foo": "x"}, "geometry": [{"lat": 0, "lon": 0}, {"lat": 1, "lon": 1}]},
              {"type": "node", "tags": {"power": "plant"}, "lat": 1.234567, "lon": 2.0},
              {"type": "way", "tags": {"man_made": "pipeline", "substance": "gas"}, "geometry": [{"lat": 0, "lon": 0}, {"lat": 0, "lon": 1}, {"lat": 1, "lon": 1}, {"lat": 0, "lon": 0}]}]
    fc = convert(sample)
    assert [f["geometry"]["type"] for f in fc["features"]] == ["Polygon", "LineString", "Point", "LineString"]
    assert "foo" not in fc["features"][1]["properties"] and fc["features"][2]["geometry"]["coordinates"] == [2.0, 1.23457]
    assert fc["features"][3]["properties"]["gas"] == 1 and "gas" not in fc["features"][0]["properties"]

    os.makedirs(OUT_DIR, exist_ok=True)
    codes = sys.argv[1:] or list(PROVINCES)
    failed = []
    for code in codes:
        elements = fetch(code)
        if elements is None:
            failed.append(code)
            continue
        fc = convert(elements)
        with open(os.path.join(OUT_DIR, f"{code}.js"), "w", encoding="utf-8") as f:
            f.write(f"// {PROVINCES[code]}: OpenStreetMap power and gas data, (c) OpenStreetMap contributors, ODbL.\n")
            f.write(f"INFRA_LOADED({json.dumps(code)}, ")
            json.dump(fc, f, separators=(",", ":"))
            f.write(");\n")
        print(f"{code}: wrote {len(fc['features']):,} features", flush=True)

    # Rebuild the index (name, bounding box, count, date) from every province file present
    index = {}
    for code, name in PROVINCES.items():
        path = os.path.join(OUT_DIR, f"{code}.js")
        if not os.path.exists(path):
            continue
        text = open(path, encoding="utf-8").read()
        start = text.index("INFRA_LOADED(")
        fc = json.loads(text[text.index(", ", start) + 2:text.rindex(")")])
        xs, ys = [], []
        for feat in fc["features"]:
            g = feat["geometry"]
            pts = [g["coordinates"]] if g["type"] == "Point" else g["coordinates"] if g["type"] == "LineString" else [p for ring in g["coordinates"] for p in ring]
            xs += [p[0] for p in pts]; ys += [p[1] for p in pts]
        if xs:
            index[code] = {"name": name, "bbox": [min(xs), min(ys), max(xs), max(ys)], "count": len(fc["features"]),
                           "date": time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(path)))}
    with open(os.path.join(OUT_DIR, "index.js"), "w", encoding="utf-8") as f:
        f.write("// Generated by fetch_infrastructure.py: which province files exist and where they are.\n")
        f.write("window.INFRA_INDEX = " + json.dumps(index, indent=1) + ";\n")
    print(f"Index: {len(index)} provinces/territories")
    if failed:
        sys.exit(f"Overpass failed for {' '.join(failed)}; re-run: python fetch_infrastructure.py {' '.join(failed)}")
