# Canada Utilities Map

One map combining:

- **OEB Centralized Capacity Information Map (CCIM):** available load and DER hosting capacity by feeder area, loaded live from the OEB's public ArcGIS service.
- **Fibre & telecom:** CN/CP mainline railways as a stand-in for long-haul fibre corridors (no public route data exists); Alberta SuperNet sites (Edmonton region); OpenStreetMap telecom lines, data centres and exchanges; official Northwestel and N.W.T. fibre routes (live from the N.W.T. government); ISED-flagged communities without a fibre backbone or that rely on satellite.
- **Power and gas infrastructure across Canada** from OpenStreetMap, the same data shown on [Open Infrastructure Map](https://openinframap.org). Each province loads when you pan to it (zoom 5 or closer).

Open `index.html` (or the published GitHub Pages link). Tick or untick legend rows to filter capacity ranges, voltage classes and gas facility types.

- **Search** an address or place (Esri World Geocoder); picking a result opens a site report for it.
- **Check a site:** click the button, then the map, for the nearest substation, power line, gas line, rail corridor, data centre and exchange, plus Ontario capacity at that point.
- **Copy link:** the address bar keeps the view, basemap, layers and any site report, so a copied link reopens exactly what you see.

## Refresh the infrastructure data

```
python fetch_infrastructure.py
```

This rewrites `data/CA-XX.js` (one file per province/territory) and `data/index.js` from OpenStreetMap. To refresh only some, list their codes, e.g. `python fetch_infrastructure.py CA-AB CA-BC`. The capacity data is always live and needs no refresh.

For the fibre & telecom data (OpenStreetMap telecom and mainline railways, ISED National Broadband Data):

```
python fetch_telecom.py
```

For Alberta's gas pipelines (AER Enhanced Pipeline file, ~170 MB download; needs `python -m pip install --user pyshp`):

```
python fetch_aer_gas.py
```

For BC, Saskatchewan and Ontario gas pipelines (provincial regulators):

```
python fetch_gas_regulators.py
```

## Data and licences

- Capacity: Ontario Energy Board CCIM. Values are indicative; confirm with the local distributor. No reuse licence is stated, so check with the OEB before commercial use.
- Infrastructure and telecom: © OpenStreetMap contributors, ODbL.
- Community backbone flags: ISED National Broadband Data, Open Government Licence – Canada.
- Northwestel / N.W.T. fibre routes: Government of the Northwest Territories ArcGIS service.
- Alberta gas pipelines: Alberta Energy Regulator Enhanced Pipeline file; informational use, no commercial reproduction.
- BC pipelines: BC Energy Regulator permitted pipeline segments (DataBC), Open Government Licence – BC.
- Saskatchewan gas pipelines and flowlines: Ministry of Energy and Resources, Government of Saskatchewan.
- Ontario gas pipelines: MNRF Utility Line (Ontario GeoHub), Open Government Licence – Ontario.
- TC Canadian Mainline and other federal gas systems: Canada Energy Regulator pipeline map service, personal and non-commercial use only.
- Basemaps: Esri Light/Dark Gray Canvas, World Imagery (satellite), World Hillshade and World Topographic.
- Contour lines: generated in the browser from AWS Terrain Tiles (NRCan CDEM, SRTM), accurate to a few metres.
