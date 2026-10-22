# Ontario Grid Capacity Map

One map combining:

- **OEB Centralized Capacity Information Map (CCIM):** available load and DER hosting capacity by feeder area, loaded live from the OEB's public ArcGIS service.
- **Power and gas infrastructure** from OpenStreetMap, the same data shown on [Open Infrastructure Map](https://openinframap.org).

Open `index.html` (or the published GitHub Pages link). Tick or untick legend rows to filter capacity ranges, voltage classes and gas facility types.

## Refresh the infrastructure data

```
python fetch_infrastructure.py
```

This rewrites `infrastructure-ontario.js` from OpenStreetMap. The capacity data is always live and needs no refresh.

## Data and licences

- Capacity: Ontario Energy Board CCIM. Values are indicative; confirm with the local distributor. No reuse licence is stated, so check with the OEB before commercial use.
- Infrastructure: © OpenStreetMap contributors, ODbL.
- Basemaps: Esri Light/Dark Gray Canvas, World Imagery (satellite), World Hillshade and World Topographic.
- Contour lines: generated in the browser from AWS Terrain Tiles (NRCan CDEM, SRTM), accurate to a few metres.
