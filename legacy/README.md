# Cafe Finder (prototype)

Finds every cafe in Mumbai, or in one area of it (Bandra, Colaba, the current map view…), and shows them on a map with a filterable list and a CSV export.

## Run

```
py server.py
```

Open http://127.0.0.1:8770.

## Using Google Maps data

Without a key the app uses OpenStreetMap cafes, so it works straight away. To use Google Maps listings:

1. In Google Cloud, enable **Places API (New)** and create an API key.
2. Create a `.env` file next to `server.py`:
   ```
   GOOGLE_MAPS_API_KEY=your-key
   ```
3. Restart the server. The badge in the top right changes to "Google Places".

### How it gets *all* the cafes

A single Google Places Text Search returns at most 60 places. To get past that, the app:

1. splits the area into ~5 km tiles,
2. searches each tile for the `cafe` and `coffee_shop` place types,
3. splits any tile that returned the full 60 into four smaller tiles and searches those, down to ~250 m.

You can watch this on the map: dashed squares are queued, shaded ones are done, orange outlines were split. Results are de-duplicated by Google place ID, and permanently closed places are dropped.

### Cost

Each tile costs 2–6 Text Search calls. A full Mumbai sweep is typically a few hundred to ~1,500 calls. Check current Places API pricing before running it. Every tile response is cached in `./cache`, so running the same search again costs nothing; delete that folder to refresh the data. There is a safety cap of 3,000 calls per search (`MAX_CALLS` in `public/app.js`).

## Adding other cities

Add an entry to `LOCATIONS` in `server.py` with its bounding box, then set `CITY` in `public/app.js`.
