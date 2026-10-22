"""Download Ontario power and gas infrastructure from OpenStreetMap (Overpass) into infrastructure-ontario.js
for index.html (the map). This is the same OpenStreetMap data Open Infrastructure Map draws.

Run:  python fetch_infrastructure.py
Re-run whenever you want fresher data. Power lines are transmission/sub-transmission only (power=line|cable);
distribution lines are skipped because they would make the file huge.
"""
import json
import sys
import time
import urllib.parse
import urllib.request

MIRRORS = ["https://overpass-api.de/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]
GAS = '"substance"~"gas",i'
QUERY = f"""[out:json][timeout:600];
area["ISO3166-2"="CA-ON"]->.on;
(way["power"~"^(line|cable)$"](area.on);
 nw["power"~"^(substation|plant)$"](area.on);
 relation["power"="plant"](area.on);
 way["man_made"="pipeline"][{GAS}](area.on);
 nw["pipeline"="substation"](area.on);
 nw["man_made"="petroleum_well"](area.on);
 nwr["man_made"="storage_tank"]["content"~"gas",i](area.on););
out geom tags;"""
KEEP = ("power", "name", "voltage", "operator", "circuits", "ref", "plant:source", "plant:output:electricity",
        "man_made", "pipeline", "substation", "substance", "pressure", "diameter", "usage", "location", "content")
OUT = "infrastructure-ontario.js"  # a script (not .json) so the map works when opened straight from disk


def fetch():
    body = urllib.parse.urlencode({"data": QUERY}).encode()
    for attempt in range(4):
        for url in MIRRORS:
            try:
                print(f"Querying {url} …", flush=True)
                req = urllib.request.Request(url, body, {"User-Agent": "ontario-capacity-map/1.0"})
                with urllib.request.urlopen(req, timeout=900) as r:
                    return json.load(r)["elements"]
            except Exception as e:  # busy mirror: try the next one
                print(f"  failed: {e}", flush=True)
        time.sleep(30 * (attempt + 1))
    sys.exit("All Overpass servers failed. Try again later.")


def is_gas(t):
    return "power" not in t


def to_feature(el):
    tags = {k: v for k, v in el.get("tags", {}).items() if k in KEEP}
    if is_gas(tags):
        tags["gas"] = 1  # the map splits power vs gas on this flag
    rnd = lambda g: [round(g["lon"], 5), round(g["lat"], 5)]
    if el["type"] == "node":
        geom = {"type": "Point", "coordinates": rnd(el)}
    elif el["type"] == "way":
        pts = [rnd(g) for g in el["geometry"]]
        linear = tags.get("power") in ("line", "cable") or tags.get("man_made") == "pipeline"
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
    # self-check of the conversion on a tiny sample
    sample = [{"type": "way", "tags": {"power": "substation", "name": "A"}, "geometry": [{"lat": 0, "lon": 0}, {"lat": 0, "lon": 1}, {"lat": 1, "lon": 1}, {"lat": 0, "lon": 0}]},
              {"type": "way", "tags": {"power": "line", "voltage": "230000", "foo": "x"}, "geometry": [{"lat": 0, "lon": 0}, {"lat": 1, "lon": 1}]},
              {"type": "node", "tags": {"power": "plant"}, "lat": 1.234567, "lon": 2.0},
              {"type": "way", "tags": {"man_made": "pipeline", "substance": "gas"}, "geometry": [{"lat": 0, "lon": 0}, {"lat": 0, "lon": 1}, {"lat": 1, "lon": 1}, {"lat": 0, "lon": 0}]}]
    fc = convert(sample)
    assert [f["geometry"]["type"] for f in fc["features"]] == ["Polygon", "LineString", "Point", "LineString"]
    assert "foo" not in fc["features"][1]["properties"] and fc["features"][2]["geometry"]["coordinates"] == [2.0, 1.23457]
    assert fc["features"][3]["properties"]["gas"] == 1 and "gas" not in fc["features"][0]["properties"]

    fc = convert(fetch())
    today = time.strftime("%Y-%m-%d")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(f"// OpenStreetMap power and gas data, (c) OpenStreetMap contributors, ODbL. Generated {today}.\n")
        f.write(f"window.INFRA_DATE = {json.dumps(today)};\nwindow.INFRA = ")
        json.dump(fc, f, separators=(",", ":"))
        f.write(";\n")
    print(f"Wrote {len(fc['features']):,} features to {OUT}")
