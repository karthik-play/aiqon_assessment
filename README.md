# Shipment Route Recommender

A Streamlit app for comparing candidate shipment routes. It ranks routes by cost, transit time, delay probability, and operational risk using a weighted scoring method. It does not use a trained machine-learning model.

## What the app does

- Generates synthetic shipment data with four route options per shipment.
- Saves generated data to `output/data/synthetic_shipments.json` and lets you download it.
- Loads an uploaded JSON dataset and lets you select a shipment.
- Shows the recommended route, its metrics, and a comparison of the route options.

The app starts without a dataset. Generate one in the app or upload a JSON file.

## How route ranking works

The app calculates route metrics from the legs in each route:

- Cost and transit time are summed across legs.
- Route delay probability is `1 - product(1 - leg delay probability)`.
- Congestion and geopolitical risk are averaged using leg transit times as weights. The risk index is the mean of those two values.

Each metric is divided by a reference scale in `src/core/config.py`. The normalized values are multiplied by the shipment's weights and added to form a score. Lower scores rank ahead. The app checks cost, transit-time, and risk limits first; a route that breaks a limit is marked excluded.

Weights and limits are part of each shipment in the uploaded dataset. The app does not provide a separate optimization-focus selector.

## Data format

The JSON file must have `format_version: 1` and a non-empty `shipments` list. Each shipment includes an ID, origin, destination, and candidate routes. It can also include a priority profile, weights, and service limits. Each route contains one or more legs. Delay and risk values are decimal fractions, such as `0.12` for 12%.

The loader checks the dataset structure and required fields. The schemas are intentionally lightweight and do not check every numeric value or business rule.

```json
{
  "format_version": 1,
  "shipments": [
    {
      "shipment_id": "SHP-001",
      "origin": "Singapore",
      "destination": "Durban",
      "priority_profile": "balanced",
      "weights": {
        "cost": 0.35,
        "time": 0.30,
        "delay": 0.20,
        "risk": 0.15
      },
      "constraints": {
        "max_cost_usd": 8000,
        "max_transit_days": 40,
        "max_risk_index": 0.52
      },
      "routes": [
        {
          "route_id": "SHP-001-R1",
          "name": "Economy",
          "legs": [
            {
              "leg_id": "SHP-001-R1-L1",
              "origin": "Singapore",
              "destination": "Colombo",
              "mode": "ocean",
              "cost_usd": 2500,
              "transit_days": 9,
              "delay_probability": 0.08,
              "congestion_risk": 0.2,
              "geopolitical_risk": 0.15
            },
            {
              "leg_id": "SHP-001-R1-L2",
              "origin": "Colombo",
              "destination": "Durban",
              "mode": "ocean",
              "cost_usd": 2500,
              "transit_days": 9,
              "delay_probability": 0.08,
              "congestion_risk": 0.2,
              "geopolitical_risk": 0.15
            }
          ]
        }
      ]
    }
  ]
}
```

The generator creates four route types: economy, balanced, express, and resilient. Its values are illustrative and are not live carrier or port data.

## Project structure

```text
src/
  ui/app.py                    Streamlit page
  components/
    recommendation.py          Recommendation orchestration
    synthetic_data.py          Synthetic shipment and route generation
  core/
    config.py                  Paths, defaults, weights, and generation settings
    logger.py                  Logger setup
    schemas.py                 Shipment, route, and result data classes
    scoring.py                 Metric aggregation, limits, and route ranking
    utils.py                   JSON loading and writing
  pipelines/
    generate_data.py           Data generation entry point
    recommend.py               Recommendation entry point
    evaluate.py                Dataset evaluation functions
    build_report.py            PDF report functions
static/
  Aiqon_Take_Home_Assignment_Context.pdf
output/
  data/                        Generated JSON datasets
  pdf/                         PDF report output
```

The Streamlit app uses the data-generation and recommendation pipelines. The evaluation module calculates coverage, Pareto selection, regret, and preference sensitivity. The PDF module builds a report with the method, sample evaluation results, and an example recommendation. These two functions are implemented separately and are not currently exposed in the app.

## Setup

### Without Docker

Requirements: Python 3.10 or newer and pip.

From the project root, create and activate a virtual environment.

**Windows PowerShell**

```powershell
python -m venv .venv
.\venv\Scripts\activate
```

**macOS or Linux**

```sh
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies and start Streamlit:

```sh
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run src/ui/app.py
```

Generate or upload data in the app. Generated files are saved under `output/data/`.

### With Docker

Requirements: Docker with the Compose plugin.

From the project root, build the image and start the app:

```sh
docker compose up --build
```

Open [http://localhost:8501](http://localhost:8501). Compose maps the project `output/` directory into the container, so generated data stays on the host. To run in the background, use `docker compose up --build -d`; view logs with `docker compose logs -f dashboard`, and stop the app with `docker compose down`.

The default host port is `8501`. To use another port, add a `.env` file in the project root with, for example:

```text
STREAMLIT_PORT=8502
```
