#!python
import importlib
import json
import traceback
import zlib
from pprint import pformat
from types import ModuleType
from typing import Any, Callable

import zmq
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ekaine.common.logging import get_logger
from ekaine.ingestion.eddn import processors
from ekaine.ingestion.eddn.schemas import get_schema_model_mapping
from ekaine.postgresql import SessionLocal
from ekaine.postgresql.adapter import FactionsAdapter
from gen.eddn_models import (  # fssbodysignals_v1_0,
    approachsettlement_v1_0,
    commodity_v3_0,
    fsssignaldiscovered_v1_0,
    journal_v1_0,
)

logger = get_logger(__name__)

module_mapping: dict[str, ModuleType] = {}


def import_generated_models() -> None:
    for schema, model_file in get_schema_model_mapping().items():
        module_path = f"gen.eddn_models.{model_file}"
        module = importlib.import_module(module_path)
        logger.debug(module.Model)  # Ensure model is valid and importable
        module_mapping[schema] = module


def get_module_from_schema(schema: str) -> ModuleType:
    module = module_mapping.get(schema)
    if module is None:
        raise ValueError(f"Tried getting a module for a schema we didn't know about! '{schema}'")
    return module


# TODO: Consider dependency ordering of inserts for new system/stations
# Eg, if we're seeing market commodities for a system we don't have in the DB, there should be a pending
# upsert for the station/system that needs to go through before we can upsert the market commodities themselves,
# which have a FK on the stations table, ie station needs to be upserted first.
processor_mapping: dict[type[Any], Callable[[Session, Any], None]] = {
    commodity_v3_0.Model: processors.commodity_v3_0.process_model,
    # approachsettlement_v1_0.Model: self.process_approachsettlement_v1_0,
    journal_v1_0.Model: processors.journal_v1_0.process_model,
    fsssignaldiscovered_v1_0.Model: processors.fsssignaldiscovered_v1_0.process_model,
    # fssbodysignals_v1_0.Model: processors.fssbodysignals_v1_0.process_model,
}


def approachsettlement_v1_0_model_to_controlling_faction_id(model: approachsettlement_v1_0.Model) -> int | None:
    faction_id = None
    controlling_faction = getattr(model.message, "SystemFaction", None)
    if controlling_faction is not None:
        faction_name = controlling_faction.get("Name")
        faction = FactionsAdapter().get_faction(faction_name)
        if faction is not None:
            faction_id = faction.id

    return faction_id


def process_approachsettlement_v1_0(session: Session, model: approachsettlement_v1_0.Model) -> None:
    pass
    # controlling_faction_id = EDDNListener.approachsettlement_v1_0_model_to_controlling_faction_id(model)
    # system_dict = SystemsDB.to_dict_from_eddn(model, controlling_faction_id)
    # logger.info(pformat(system_dict))


def run_listener(session: Session) -> None:
    ctx = zmq.Context()
    sub = ctx.socket(zmq.SUB)
    sub.connect("tcp://eddn.edcd.io:9500")
    sub.setsockopt_string(zmq.SUBSCRIBE, "")

    import_generated_models()

    print("Listening for messages...")
    while True:
        msg = sub.recv_multipart()
        raw_json = zlib.decompress(msg[0])
        d = json.loads(raw_json)
        schema = d.get("$schemaRef")
        if schema is None:
            logger.warning("Could not find a valid $schemaRef field in decoded EDDN message!")
            logger.warning(pformat(d))
            continue

        try:
            module = get_module_from_schema(schema)
            obj = module.Model.model_validate(d)
        except ValueError:
            logger.error(traceback.format_exc())
            logger.error(f"Got an unknown schema! '{schema}'")
        except Exception:
            logger.error(traceback.format_exc())
            logger.error(pformat(d))
            continue

        obj_type = type(obj)
        if issubclass(obj_type, BaseModel) and obj_type in processor_mapping:
            try:
                event = d.get("message", {}).get("event")
                if "eRingClass" in raw_json.decode("utf8"):
                    logger.trace("\n")
                    logger.trace("RING RING RING RING")
                    logger.trace(d)
                if event not in ["Scan", "FSDJump", "Docked"]:
                    logger.trace("\n")
                    logger.trace(d)
                processor_mapping[obj_type](session, obj)
            except Exception:
                logger.error(traceback.format_exc())


def main() -> None:
    session = SessionLocal()
    run_listener(session)


if __name__ == "__main__":
    main()
