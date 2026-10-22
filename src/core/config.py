from pathlib import Path


# PROJECT PATHS
BASE_PATH = Path(__file__).resolve().parents[2]
OUTPUT_DIRECTORY = BASE_PATH / "output"
SYNTHETIC_DATA_PATH = OUTPUT_DIRECTORY / "data"
REPORT_OUTPUT_PATH = OUTPUT_DIRECTORY / "pdf" / "aiqon_route_optimization_report.pdf"

# LOGGING
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# DATASET DEFAULTS
DATA_FORMAT_VERSION = 1
DEFAULT_SHIPMENT_COUNT = 30
DEFAULT_SEED = 20261019
DEFAULT_ROUTE_MODE = "ocean"

# ROUTE SCORING
OBJECTIVES = ("cost", "time", "delay", "risk")
PRIORITY_PROFILES = {
    "balanced": {"cost": 0.35, "time": 0.30, "delay": 0.20, "risk": 0.15},
    "cost_saver": {"cost": 0.55, "time": 0.18, "delay": 0.15, "risk": 0.12},
    "time_critical": {"cost": 0.15, "time": 0.55, "delay": 0.18, "risk": 0.12},
    "risk_averse": {"cost": 0.18, "time": 0.20, "delay": 0.35, "risk": 0.27},
}
REFERENCE_SCALES = {"cost": 10_000.0, "time": 45.0, "delay": 0.30, "risk": 0.50}
COMPARISON_TOLERANCE = 1e-9

# SYNTHETIC DATA
ORIGINS = ("Mundra", "Nhava Sheva", "Chennai", "Kolkata", "Singapore")
DESTINATIONS = ("Rotterdam", "Hamburg", "Los Angeles", "Durban", "Felixstowe")
HUBS = (
    "Colombo",
    "Jebel Ali",
    "Singapore Hub",
    "Suez Gateway",
    "Gibraltar Hub",
    "Busan Hub",
    "Panama Hub",
    "Cape Gateway",
    "Salalah",
)
BASE_COST_RANGE_USD = (3_800.0, 7_400.0)
BASE_TRANSIT_RANGE_DAYS = (18.0, 31.0)
LEG_SPLIT_WEIGHT_RANGE = (0.75, 1.25)
SYNTHETIC_TOTAL_VARIATION_RANGE = (0.96, 1.04)
SYNTHETIC_LEG_DELAY_VARIATION_RANGE = (0.90, 1.10)
SYNTHETIC_LEG_DELAY_BOUNDS = (0.005, 0.40)
SYNTHETIC_RISK_BOUNDS = (0.01, 0.95)
SYNTHETIC_RISK_SPREAD = 0.055
COST_SAVER_BUDGET_FACTOR = 1.28
DEFAULT_BUDGET_FACTOR = 1.48
TIME_CRITICAL_DEADLINE_FACTOR = 1.18
DEFAULT_DEADLINE_FACTOR = 1.35
DEFAULT_MAX_RISK_INDEX = 0.52
ROUTE_PROFILES = (
    {
        "key": "economy",
        "name": "Economy / longer transit",
        "cost_factor": 0.76,
        "time_factor": 1.22,
        "delay": 0.19,
        "congestion": 0.38,
        "geopolitical": 0.34,
        "legs": 3,
    },
    {
        "key": "balanced",
        "name": "Balanced / standard service",
        "cost_factor": 1.00,
        "time_factor": 1.00,
        "delay": 0.11,
        "congestion": 0.23,
        "geopolitical": 0.19,
        "legs": 2,
    },
    {
        "key": "express",
        "name": "Express / higher cost",
        "cost_factor": 1.38,
        "time_factor": 0.70,
        "delay": 0.13,
        "congestion": 0.31,
        "geopolitical": 0.23,
        "legs": 2,
    },
    {
        "key": "resilient",
        "name": "Resilient / lower operational risk",
        "cost_factor": 1.20,
        "time_factor": 1.07,
        "delay": 0.045,
        "congestion": 0.12,
        "geopolitical": 0.10,
        "legs": 3,
    },
)

# DASHBOARD LABELS
PROFILE_LABELS = {
    "balanced": "Balanced",
    "cost_saver": "Cost saver",
    "time_critical": "Time critical",
    "risk_averse": "Risk averse",
}

# REPORT COLORS
REPORT_COLORS = {
    "navy": "#17324D",
    "blue": "#1B6A8F",
    "pale_blue": "#EAF3F7",
    "pale_gray": "#F3F5F7",
    "ink": "#25323D",
    "muted": "#5B6872",
    "border": "#D5DDE3",
}
