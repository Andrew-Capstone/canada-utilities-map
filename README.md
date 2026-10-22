# Ontario Grid Capacity Map

One map combining:

- **OEB Centralized Capacity Information Map (CCIM):** available load and DER hosting capacity by feeder area, loaded live from the OEB's public ArcGIS service.
- **Fibre & telecom:** OpenStreetMap telecom lines, data centres and exchanges; official Northwestel and N.W.T. fibre routes (live from the N.W.T. government); ISED-flagged communities without a fibre backbone or that rely on satellite.
- **Power and gas infrastructure across Canada** from OpenStreetMap, the same data shown on [Open Infrastructure Map](https://openinframap.org). Each province loads when you pan to it (zoom 5 or closer).

Open `index.html` (or the published GitHub Pages link). Tick or untick legend rows to filter capacity ranges, voltage classes and gas facility types.

## Refresh the infrastructure data

```
python fetch_infrastructure.py
```

This rewrites `data/CA-XX.js` (one file per province/territory) and `data/index.js` from OpenStreetMap. To refresh only some, list their codes, e.g. `python fetch_infrastructure.py CA-AB CA-BC`. The capacity data is always live and needs no refresh.

For the fibre & telecom data (OpenStreetMap telecom and ISED National Broadband Data):

```
python fetch_telecom.py
```

## Data and licences

- Capacity: Ontario Energy Board CCIM. Values are indicative; confirm with the local distributor. No reuse licence is stated, so check with the OEB before commercial use.
- Infrastructure and telecom: © OpenStreetMap contributors, ODbL.
- Community backbone flags: ISED National Broadband Data, Open Government Licence – Canada.
- Northwestel / N.W.T. fibre routes: Government of the Northwest Territories ArcGIS service.
- Basemaps: Esri Light/Dark Gray Canvas, World Imagery (satellite), World Hillshade and World Topographic.
- Contour lines: generated in the browser from AWS Terrain Tiles (NRCan CDEM, SRTM), accurate to a few metres.
