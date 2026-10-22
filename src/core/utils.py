import json
from pathlib import Path
from typing import Any
from src.core.config import DATA_FORMAT_VERSION
from src.core.logger import get_logger
from src.core.schemas import ShipmentRequest


logger = get_logger(__name__)


def load_shipments(path: str | Path):
    source = Path(path)
    logger.debug(f"Reading shipment dataset from {source}")
    try:
        with source.open("r", encoding="utf-8") as stream:
            payload = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError):
        logger.exception(f"Could not read shipment dataset from {source}")
        raise
    return load_shipments_from_payload(payload)


def load_shipments_from_payload(payload: Any):
    if not isinstance(payload, dict):
        logger.warning("Rejected shipment dataset: the top-level JSON value is not an object")
        raise ValueError("The dataset must be a JSON object.")
    if payload.get("format_version") != DATA_FORMAT_VERSION:
        logger.warning("Rejected shipment dataset with unsupported format version")
        raise ValueError(f"Unsupported dataset format_version; expected {DATA_FORMAT_VERSION}.")
    raw_shipments = payload.get("shipments")
    if not isinstance(raw_shipments, list):
        logger.warning("Rejected shipment dataset: the shipments value is not a list")
        raise ValueError("The dataset must contain a 'shipments' list.")
    try:
        shipments = [ShipmentRequest.from_mapping(item) for item in raw_shipments]
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning(f"Rejected shipment dataset due to an invalid shipment: {exc}")
        raise
    if not shipments:
        logger.warning("Rejected shipment dataset: it contains no shipments")
        raise ValueError("The dataset contains no shipments.")
    shipment_ids = [shipment.shipment_id for shipment in shipments]
    if len(shipment_ids) != len(set(shipment_ids)):
        logger.warning("Rejected shipment dataset: it contains duplicate shipment IDs")
        raise ValueError("The dataset contains duplicate shipment IDs.")
    logger.info(f"Validated shipment payload with {len(shipments)} shipment(s)")
    return shipments


def write_dataset(shipments: list[dict[str, Any]], path: str | Path) -> Path:
    destination = Path(path)
    payload = {"format_version": DATA_FORMAT_VERSION, "shipments": shipments}
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise
    logger.info(f"Wrote {len(shipments)} shipment(s) to {destination}")
    return destination
