# Data Directory — FloodSense

This directory should contain the following data files:

## Required Files

| File | Description | Source |
|------|-------------|--------|
| `maharashtra_dem.tif` | SRTM elevation raster | [NASA EarthData](https://earthdata.nasa.gov) |
| `maharashtra_boundary.geojson` | Maharashtra district boundary | [data.gov.in](https://data.gov.in) |
| `rivers.geojson` | River network from India WRIS | [India WRIS](https://india-wris.nrsc.gov.in) |
| `villages.geojson` | Settlement points | [Bhuvan](https://bhuvan.nrsc.gov.in) |
| `roads.geojson` | Road network | [Geofabrik OSM](https://download.geofabrik.de/asia/india.html) |

## Download Instructions

See `flood_project_build.md` Phase 1 (Tasks 1.1 - 1.3) for detailed download instructions.

### Quick conversion command (shapefile → GeoJSON):
```bash
ogr2ogr -f GeoJSON output.geojson input.shp
```
