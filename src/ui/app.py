"""Simple Streamlit interface for shipment route recommendations."""

import json
import sys
from pathlib import Path

import streamlit as st

# Allow `streamlit run src/ui/app.py` from the repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import (
    DATA_FORMAT_VERSION,
    DEFAULT_SEED,
    DEFAULT_SHIPMENT_COUNT,
    PROFILE_LABELS,
    SYNTHETIC_DATA_PATH,
)
from src.core.logger import get_logger
from src.core.schemas import Recommendation, ShipmentRequest
from src.core.utils import load_shipments_from_payload, write_dataset
from src.pipelines.generate_data import generate_dataset
from src.pipelines.recommend import recommend_shipment


logger = get_logger(__name__)


def render_data_generator() -> None:
    """Generate and save a JSON dataset that can be uploaded below."""
    with st.expander("Generate a dataset"):
        count_column, seed_column = st.columns(2)
        count = count_column.number_input(
            "Number of shipments",
            min_value=1,
            max_value=1000,
            value=DEFAULT_SHIPMENT_COUNT,
            step=1,
        )
        seed = seed_column.number_input(
            "Random seed",
            min_value=-(2**31),
            max_value=2**31 - 1,
            value=DEFAULT_SEED,
            step=1,
        )

        if st.button("Generate JSON", type="primary"):
            st.session_state.pop("generated_json", None)
            try:
                payload = {
                    "format_version": DATA_FORMAT_VERSION,
                    "shipments": generate_dataset(int(count), int(seed)),
                }
                load_shipments_from_payload(payload)
                saved_path = write_dataset(
                    payload["shipments"],
                    SYNTHETIC_DATA_PATH / "synthetic_shipments.json",
                )
                st.session_state["generated_json"] = json.dumps(
                    payload, indent=2, ensure_ascii=False
                )
                relative_path = saved_path.relative_to(PROJECT_ROOT).as_posix()
                st.success(f"Saved {int(count)} shipments to {relative_path}.")
            except Exception as exc:
                logger.error(f"Could not generate shipment data: {exc}", exc_info=True)
                st.error(f"Could not generate the dataset: {exc}")

        if st.session_state.get("generated_json"):
            st.download_button(
                "Download generated JSON",
                data=st.session_state["generated_json"],
                file_name="synthetic_shipments.json",
                mime="application/json",
            )
            st.caption("Upload the downloaded file below to get a recommendation.")


def load_uploaded_shipments() -> tuple[list[ShipmentRequest] | None, str]:
    """Read and validate the JSON file selected by the user."""
    uploaded = st.file_uploader("Upload a shipment JSON file", type=["json"])
    if uploaded is None:
        return None, ""

    try:
        payload = json.loads(uploaded.getvalue().decode("utf-8-sig"))
        return load_shipments_from_payload(payload), uploaded.name
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        logger.warning(f"Could not load {uploaded.name}: {exc}")
        st.error(f"Could not load this dataset: {exc}")
        return None, uploaded.name


def route_rows(result: Recommendation) -> list[dict[str, str]]:
    """Create a compact table of the route scores."""
    rows = []
    for rank, scored in enumerate(result.ranked_routes, start=1):
        metrics = scored.metrics
        status = (
            "Recommended"
            if scored is result.selected
            else "Feasible"
            if scored.feasible
            else "Excluded"
        )
        rows.append(
            {
                "Rank": str(rank) if scored.feasible else "—",
                "Route": scored.route.name,
                "Status": status,
                "Cost": f"${metrics.cost_usd:,.0f}",
                "Transit": f"{metrics.transit_days:.1f} days",
                "Delay": f"{metrics.delay_probability:.1%}",
                "Risk": f"{metrics.risk_index:.3f}",
                "Score": f"{scored.score:.4f}" if scored.feasible else "—",
            }
        )
    return rows


def render_recommendation(shipments: list[ShipmentRequest], dataset_name: str) -> None:
    """Show a recommendation for the selected shipment."""
    shipment_index = st.selectbox(
        "Shipment",
        range(len(shipments)),
        format_func=lambda index: (
            f"{shipments[index].shipment_id}: "
            f"{shipments[index].origin} to {shipments[index].destination}"
        ),
    )
    shipment = shipments[shipment_index]
    result = recommend_shipment(shipment)
    profile = PROFILE_LABELS.get(result.priority_profile, result.priority_profile)
    st.caption(f"{dataset_name} · {len(shipments)} shipments · {profile} focus")

    selected = result.selected
    if selected is None:
        st.warning("No route meets this shipment's limits.")
    else:
        st.subheader(selected.route.name)
        metrics = selected.metrics
        cost, transit, delay, risk = st.columns(4)
        cost.metric("Estimated cost", f"${metrics.cost_usd:,.0f}")
        transit.metric("Transit time", f"{metrics.transit_days:.1f} days")
        delay.metric("Delay chance", f"{metrics.delay_probability:.1%}")
        risk.metric("Risk index", f"{metrics.risk_index:.3f}")
        st.caption(f"Decision score: {selected.score:.4f}. Lower scores rank ahead.")

    st.subheader("Route options")
    st.dataframe(route_rows(result), hide_index=True, width="stretch")


def main() -> None:
    st.set_page_config(page_title="Shipment Route Recommender", layout="wide")
    st.title("Shipment Route Recommender")
    st.caption("Upload shipment data to compare routes and get a recommendation.")

    render_data_generator()
    shipments, dataset_name = load_uploaded_shipments()
    if shipments is not None:
        render_recommendation(shipments, dataset_name)
    else:
        st.info("Generate a dataset above, then upload its JSON file here.")


if __name__ == "__main__":
    main()
