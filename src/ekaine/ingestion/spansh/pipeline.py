import logging  # noqa: F401
from datetime import datetime, timedelta, timezone
from itertools import chain
from pathlib import Path
from pprint import pformat
from typing import Any, Callable

import aiofiles  # noqa: F401
import ijson  # type: ignore
import yaml

from ekaine.common.constants import (
    COMMODITIES_YAML_FMT,
    GALAXY_POPULATED_JSON,
    GALAXY_POPULATED_JSON_GZ,
    GALAXY_POPULATED_JSON_URL,
    METADATA_DIR,
)
from ekaine.common.logging import get_logger
from ekaine.common.timer import Timer
from ekaine.common.utils import download_file, seconds_to_str, ungzip
from ekaine.ingestion.spansh.models import BaseSpanshModel
from ekaine.ingestion.spansh.models.body_spansh import AsteroidsSpansh, BodySpansh
from ekaine.ingestion.spansh.models.station_spansh import StationSpansh
from ekaine.ingestion.spansh.models.system_spansh import (
    ControllingFactionSpansh,
    FactionSpansh,
    SystemSpansh,
)
from ekaine.postgresql import SessionLocalEkaine
from ekaine.postgresql.db import (
    BodiesDB,
    CommoditiesDB,
    FactionPresencesDB,
    FactionsDB,
    HotspotsDB,
    MarketCommoditiesDB,
    OutfittingShipModulesDB,
    RingsDB,
    ShipModulesDB,
    ShipsDB,
    ShipyardShipsDB,
    SignalsDB,
    StationsDB,
    SystemsDB,
)
from ekaine.postgresql.utils import upsert_all

logger = get_logger(__name__)

EPOCH_ZERO = datetime.fromtimestamp(0)


def insert_layer1(partitioner: "SpanshDataLayerPartitioner", input_systems: list[SystemSpansh]) -> None:
    logger.info(f"Layer 1: Factions ({partitioner.total_running_str_fn()})")

    all_factions: dict[str, FactionSpansh | ControllingFactionSpansh] = {}
    faction_dicts: dict[str, dict[str, Any]] = {}

    for system in input_systems:
        for faction in system.factions or []:
            all_factions[faction.name] = faction
            faction_dicts[faction.name] = FactionsDB.to_dict_from_spansh(faction)

        controlling = system.controlling_faction
        if controlling:
            all_factions[controlling.name] = controlling
            faction_dicts[controlling.name] = FactionsDB.to_dict_from_spansh(controlling)

    faction_objects = upsert_all(partitioner.session, FactionsDB, list(faction_dicts.values()))

    for faction_obj in faction_objects:
        spansh_faction = all_factions.get(faction_obj.name)
        if spansh_faction is None:
            raise Exception(f"Missing faction '{faction_obj.name}' in original Spansh data.")
        partitioner.cache_spansh_entity_id(spansh_faction, faction_obj.id)


def insert_layer2(partitioner: "SpanshDataLayerPartitioner", input_systems: list[SystemSpansh]) -> None:
    logger.info(f"Layer 2: Systems ({partitioner.total_running_str_fn()})")

    systems_dict_set: dict[int, dict[str, Any]] = {}
    system_by_key: dict[int, SystemSpansh] = {}

    for system in input_systems:
        system_by_key[system.to_cache_key()] = system
        controlling_id = (
            partitioner.get_spansh_entity_id(system.controlling_faction) if system.controlling_faction else None
        )
        system_dict = SystemsDB.to_dict_from_spansh(system, controlling_id)
        cache_key = system.to_cache_key()

        if cache_key not in systems_dict_set:
            systems_dict_set[cache_key] = system_dict
        else:
            other_system = systems_dict_set[cache_key]
            if system_dict.get("date", EPOCH_ZERO) > other_system.get("date", EPOCH_ZERO):
                # If the system we're looking at has data newer than the existing one, replace
                systems_dict_set[cache_key] = system_dict

    system_objects = upsert_all(partitioner.session, SystemsDB, list(systems_dict_set.values()))

    for system_obj in system_objects:
        spansh_system = system_by_key.get(system_obj.to_cache_key())
        if spansh_system is None:
            raise Exception(f"Spansh system not found for DB system '{system_obj.to_cache_key_tuple()}'")
        partitioner.cache_spansh_entity_id(spansh_system, system_obj.id)


def insert_layer3(partitioner: "SpanshDataLayerPartitioner", input_systems: list[SystemSpansh]) -> None:
    logger.info(f"Layer 3: FactionPresences and Bodies ({partitioner.total_running_str_fn()})")

    # --- FactionPresences ---
    presence_dicts_set: dict[int, dict[str, Any]] = {}
    for system in input_systems:
        system_id = partitioner.get_spansh_entity_id(system)
        for faction in system.factions or []:
            faction_id = partitioner.get_spansh_entity_id(faction)
            presence_dict = FactionPresencesDB.to_dict_from_spansh(faction, system_id, faction_id)
            presence_dicts_set[faction.to_cache_key()] = presence_dict

    upsert_all(partitioner.session, FactionPresencesDB, list(presence_dicts_set.values()))

    # --- Bodies ---
    body_dicts_set: dict[int, dict[str, Any]] = {}
    spansh_body_by_key: dict[int, BodySpansh] = {}
    for system in input_systems:
        system_id = partitioner.get_spansh_entity_id(system)
        for body in system.bodies or []:
            cache_key = body.to_cache_key(system_id)
            spansh_body_by_key[cache_key] = body
            body_dict = BodiesDB.to_dict_from_spansh(body, system_id)
            body_dicts_set[cache_key] = body_dict

    body_objects = upsert_all(partitioner.session, BodiesDB, list(body_dicts_set.values()))

    for body_obj in body_objects:
        spansh_body = spansh_body_by_key.get(body_obj.to_cache_key())
        if spansh_body is None:
            raise Exception(f"Body not found in spansh cache for: {pformat(body_obj.to_cache_key_tuple())}")
        partitioner.cache_spansh_entity_id_by_key(spansh_body.to_cache_key(body_obj.system_id), body_obj.id)


def insert_layer4(partitioner: "SpanshDataLayerPartitioner", input_systems: list[SystemSpansh]) -> None:
    logger.info(f"Layer 4: Stations, Signals, Rings ({partitioner.total_running_str_fn()})")

    # --- Stations ---
    station_dicts_set: dict[int, dict[str, Any]] = {}
    stations_by_key: dict[int, StationSpansh] = {}

    for system in input_systems:
        system_id = partitioner.get_spansh_entity_id(system)

        for station in system.stations or []:
            cache_key = station.to_cache_key(system_id)
            station_dict = StationsDB.to_dict_from_spansh(station, system_id, "system")

            station_dicts_set[cache_key] = station_dict
            stations_by_key[cache_key] = station

        for body in system.bodies or []:
            body_id = partitioner.get_spansh_entity_id_by_key(body.to_cache_key(system_id))

            for station in body.stations or []:
                cache_key = station.to_cache_key(body_id)
                station_dict = StationsDB.to_dict_from_spansh(station, body_id, "body")

                station_dicts_set[cache_key] = station_dict
                stations_by_key[cache_key] = station

    station_objects = upsert_all(partitioner.session, StationsDB, list(station_dicts_set.values()))

    for station_obj in station_objects:
        partitioner.cache_spansh_entity_id_by_key(station_obj.to_cache_key(), station_obj.id)

    # --- Signals ---
    signal_dicts_set: dict[int, list[dict[str, Any]]] = {}

    for system in input_systems:
        system_id = partitioner.get_spansh_entity_id(system)
        for body in system.bodies or []:
            if body.signals:
                cache_key = body.to_cache_key(system_id)
                body_id = partitioner.get_spansh_entity_id_by_key(cache_key)
                signal_dicts = SignalsDB.to_dicts_from_spansh(body.signals, body_id)
                signal_dicts_set[cache_key] = signal_dicts

    upsert_all(partitioner.session, SignalsDB, list(chain(*signal_dicts_set.values())))

    # --- Rings ---
    ring_dicts_set: dict[int, dict[str, Any]] = {}
    rings_by_key: dict[int, AsteroidsSpansh] = {}
    for system in input_systems:
        system_id = partitioner.get_spansh_entity_id(system)
        for body in system.bodies or []:
            body_id = partitioner.get_spansh_entity_id_by_key(body.to_cache_key(system_id))
            for ring in body.rings or []:
                cache_key = ring.to_cache_key(body_id)
                ring_dict = RingsDB.to_dict_from_spansh(ring, body_id)
                ring_dicts_set[cache_key] = ring_dict
                rings_by_key[cache_key] = ring

    ring_objects = upsert_all(
        partitioner.session, RingsDB, list(ring_dicts_set.values()), list(RingsDB.generated_columns)
    )

    for ring_obj in ring_objects:
        spansh_ring = rings_by_key[ring_obj.to_cache_key()]
        if spansh_ring is None:
            raise Exception(f"Missing Ring: {ring_obj.name}")

        spansh_ring_key = spansh_ring.to_cache_key(ring_obj.body_id)
        partitioner.cache_spansh_entity_id_by_key(spansh_ring_key, ring_obj.id)


def insert_layer5(partitioner: "SpanshDataLayerPartitioner", input_systems: list[SystemSpansh]) -> None:
    logger.info(f"Layer 4: Market, Outfitting, Shipyard, Hotspots ({partitioner.total_running_str_fn()})")

    # --- Market ---

    commodity_dicts_set: dict[int, dict[str, Any]] = {}

    now = datetime.now(timezone.utc)
    max_data_age = timedelta(days=partitioner.max_market_data_age_days)

    def extract_commodities(owner_id: int, station: StationSpansh) -> None:
        if station.market is None:
            return
        elif station.market.update_time is not None:
            data_age = now - station.market.update_time
            if data_age > max_data_age:
                return

        logger.trace(pformat(station.to_cache_key_tuple(owner_id)))
        station_id = partitioner.get_spansh_entity_id_by_key(station.to_cache_key(owner_id))

        for commodity in station.market.commodities or []:
            commodity_dicts_set[commodity.to_cache_key(station_id, commodity.symbol)] = (
                MarketCommoditiesDB.to_dict_from_spansh(
                    commodity, station_id, commodity.symbol, station.market.update_time
                )
            )

    for system in input_systems:
        system_id = partitioner.get_spansh_entity_id(system)
        for station in system.stations or []:
            extract_commodities(system_id, station)
        for body in system.bodies or []:
            body_id = partitioner.get_spansh_entity_id_by_key(body.to_cache_key(system_id))
            for station in body.stations:
                extract_commodities(body_id, station)

    upsert_all(
        partitioner.session,
        MarketCommoditiesDB,
        list(commodity_dicts_set.values()),
    )

    # --- Outfitting ---

    module_dicts_set: dict[int, dict[str, Any]] = {}

    def extract_modules(owner_id: int, station: StationSpansh) -> None:
        if station.outfitting is None:
            return
        station_id = partitioner.get_spansh_entity_id_by_key(station.to_cache_key(owner_id))  # noqa: F841
        # TODO: Import module metadata first
        # for module in station.outfitting.modules:
        #     module_id = partitioner.get_metadata_by_name(module.symbol)
        #     modules.append(module.to_sqlalchemy_dict(station_id, module_id))

    for system in input_systems:
        system_id = partitioner.get_spansh_entity_id(system)
        for station in system.stations or []:
            extract_modules(system_id, station)
        for body in system.bodies or []:
            body_id = partitioner.get_spansh_entity_id_by_key(body.to_cache_key(system_id))
            for station in body.stations:
                extract_modules(body_id, station)

    upsert_all(partitioner.session, OutfittingShipModulesDB, list(module_dicts_set.values()))

    # --- Shipyard ---
    ship_dicts_set: dict[int, dict[str, Any]] = {}

    def extract_ships(owner_id: int, station: StationSpansh) -> None:
        if station.outfitting is None:
            return
        station_id = partitioner.get_spansh_entity_id_by_key(station.to_cache_key(owner_id))  # noqa: F841
        # for ship in station.shipyard.ships:
        #     ship_id = partitioner.get_metadata_by_name(ship.symbol)
        #     ships.append(ship.to_sqlalchemy_dict(station_id, ship_id))

    for system in input_systems:
        system_id = partitioner.get_spansh_entity_id(system)
        for station in system.stations or []:
            extract_ships(system_id, station)
        for body in system.bodies or []:
            body_id = partitioner.get_spansh_entity_id_by_key(body.to_cache_key(system_id))
            for station in body.stations:
                extract_ships(body_id, station)

    upsert_all(partitioner.session, ShipyardShipsDB, list(ship_dicts_set.values()))

    # --- Hotspots ---
    hotspot_dicts_set: dict[int, list[dict[str, Any]]] = {}
    for system in input_systems:
        system_id = partitioner.get_spansh_entity_id(system)
        for body in system.bodies or []:
            if body.rings is None:
                continue

            body_id = partitioner.get_spansh_entity_id_by_key(body.to_cache_key(system_id))

            for ring in body.rings:
                if ring.signals is None:
                    continue
                cache_key = ring.to_cache_key(body_id)
                ring_id = partitioner.get_spansh_entity_id_by_key(cache_key)
                hotspot_dicts = HotspotsDB.to_dicts_from_spansh(ring.signals, ring_id)
                hotspot_dicts_set[cache_key] = hotspot_dicts
    upsert_all(partitioner.session, HotspotsDB, list(chain(*hotspot_dicts_set.values())))


type MetadataDB = CommoditiesDB | ShipsDB | ShipModulesDB


class SpanshDataLayerPartitioner:
    """Processes Spansh data dumps into data "layers"

    Data layers are defined as the layers of tables that
    must be inserted in layer order to adhere to FK relation requirements.
    Ie, cannot insert a row needing an FK if the FK table's row doesn't exist yet.

    Layer 1:
      - FactionsDB
        - Used in SystemsDB.controlling_faction_id
      - CommoditiesDB, ShipsDB, and ShipModulesDB too technically
        - However, they get loaded as metadata in load_metadata_yaml_into_pg()
        - Used in MarketCommoditiesDB.commodity_sym, ShipsDB.ship_id, ShipModulesDB.module_id
    Layer 2:
      - SystemsDB (Use)
        - Used in FactionPresencesDB.system_id, BodiesDB.system_id, etc
    Layer 3:
      - FactionPresencesDB
      - BodiesDB
        - Used in StationsDB.owner_id, SignalsDB.body_id, RingsDB.body_id
    Layer 4:
      - StationsDB
        - Used in MarketCommoditiesDB.station_id, ShipyardShipsDB.station_id, OutfittingShipModulesDB.station_id
      - SignalsDB
      - RingsDB
        - Used in HotspotsDB.ring_id
    Layer 5:
      - MarketCommoditiesDB
      - ShipyardShipsDB
      - OutfittingShipModulesDB
      - HotspotsDB

    """

    def __init__(self, total_running_str_fn: Callable[[], str], max_market_data_age_days: int) -> None:
        self.session = SessionLocalEkaine()
        self.id_cache: dict[int, int] = {}
        self.total_running_str_fn = total_running_str_fn
        self.max_market_data_age_days = max_market_data_age_days

    def cache_spansh_entity_id(self, entity: BaseSpanshModel, db_id: int) -> None:
        self.cache_spansh_entity_id_by_key(entity.to_cache_key(), db_id, False)
        logger.trace(f"CACHED Spansh entity: '{db_id}' - '{repr(entity)}'")

    def cache_spansh_entity_id_by_key(self, key: int, db_id: int, log: bool = True) -> None:
        if db_id is None:
            raise ValueError(f"Cannot cache None id for key: {key}")

        self.id_cache[key] = db_id

        if log:
            logger.trace(f"CACHED Spansh Key: '{db_id}' - '{key}'")

    def get_spansh_entity_id(self, entity: BaseSpanshModel) -> int:
        return self.get_spansh_entity_id_by_key(entity.to_cache_key())

    def get_spansh_entity_id_by_key(self, key: int) -> int:
        if key not in self.id_cache:
            raise KeyError(f"Key not cached: {key}")
        return self.id_cache[key]

    metadata_cache: dict[str, MetadataDB] = {}

    def cache_metadata_by_name(self, data: MetadataDB, name: str) -> None:
        if not name:
            raise ValueError(f"Cannot cache Falsey id for metadata: {data}")
        self.metadata_cache[name] = data

    def get_metadata_by_name(self, name: str) -> MetadataDB:
        if name not in self.metadata_cache:
            raise KeyError(f"Metadata not cached: {name}")
        return self.metadata_cache[name]

    commodity_names_by_category: dict[str, set[str]] = {}

    def store_commodity_name_by_category(self, commodity_name: str, category: str) -> None:
        if category not in self.commodity_names_by_category:
            self.commodity_names_by_category[category] = set()
        self.commodity_names_by_category[category].add(commodity_name)

    def get_commodity_names_by_category(self, category: str) -> set[str]:
        return self.commodity_names_by_category[category]

    def load_metadata_yaml_into_pg(self, path: Path) -> None:
        logger.debug(f"Inserting '{path}'")

        with open(path, "r") as f:
            dict = yaml.load(f.read(), Loader=yaml.Loader)
            commodities = []
            for sym, values in dict.items():
                name = values.get("name")
                if name is None:
                    raise ValueError("Got a commodity with a None name!")

                category = values.get("category")
                if category is None:
                    raise ValueError("Got a commodity with a None category!")

                self.store_commodity_name_by_category(name, category)

                commodities.append(
                    {
                        "symbol": sym,
                        "name": name,
                        "rare_goods": values.get("rare_goods"),
                        "corrosive": values.get("corrosive"),
                        "category": category,
                        "is_mineable": values.get("is_mineable"),
                        "ring_types": values.get("ring_types"),
                        "mining_method": values.get("mining_method"),
                        "has_hotspots": values.get("has_hotspots", False),
                    }
                )

            commodity_objects = upsert_all(self.session, CommoditiesDB, commodities)
            logger.debug(pformat(commodity_objects))
            for commodity in commodity_objects:
                self.cache_metadata_by_name(commodity, commodity.name)

        logger.info(f"Imported {path.name} successfully")

    def insert_systems(self, input_systems: list[SystemSpansh]) -> None:
        insert_layer1(self, input_systems)
        insert_layer2(self, input_systems)
        insert_layer3(self, input_systems)
        insert_layer4(self, input_systems)
        insert_layer5(self, input_systems)


class SpanshDataPipeline:
    def __init__(
        self,
        start_at_system_idx: int = 0,
        skipping_past_every: int = 1000,
        validated_every: int = 500,
        process_every: int = 1500,
        max_market_data_age_days: int = 30,
    ) -> None:
        self.start_at_system_idx = start_at_system_idx
        self.skipping_past_every = skipping_past_every
        self.validated_every = validated_every
        self.process_every = process_every
        self.max_market_data_age_days = max_market_data_age_days

        self.session = SessionLocalEkaine()
        self.pipeline_timer = Timer("Spansh data import pipeline")
        self.partitioner = SpanshDataLayerPartitioner(self.total_running_str, self.max_market_data_age_days)

    def total_running_str(self) -> str:
        return f"Total Running: {self.pipeline_timer.running_for_str()}"

    @staticmethod
    def download_data() -> None:
        GALAXY_POPULATED_JSON_GZ.parent.mkdir(parents=True, exist_ok=True)

        download_file(GALAXY_POPULATED_JSON_URL, GALAXY_POPULATED_JSON_GZ)
        ungzip(GALAXY_POPULATED_JSON_GZ, GALAXY_POPULATED_JSON)

    async def load_and_process_data(self, batch_process_fn: Callable[[list[SystemSpansh]], None]) -> None:
        skip_timer = Timer("Skipping rows to known min index")
        validate_timer = Timer("Pydantic validation timer")

        batch: list[SystemSpansh] = []

        idx = 0
        async with aiofiles.open(GALAXY_POPULATED_JSON, mode="r") as f:
            async for system_dict in ijson.items(f, "item"):
                idx += 1

                if idx < self.start_at_system_idx:
                    if idx % self.skipping_past_every == 0:
                        time_elapsed = seconds_to_str(skip_timer.lap(False))
                        logger.info(f"Skipping past {idx} (Took {time_elapsed})({self.total_running_str()})")
                    continue

                try:
                    model = SystemSpansh.model_validate(system_dict)
                    batch.append(model)
                except Exception as e:
                    logger.warning(f"Validation failed at item {idx}: {e}")
                    continue

                if idx % self.validated_every == 0:
                    time_elapsed = seconds_to_str(skip_timer.lap(False))
                    logger.info(
                        f"Validated {self.validated_every} systems in {time_elapsed} "
                        f"({idx} total)({self.total_running_str()})"
                    )

                if idx % self.process_every == 0:
                    old_batch = batch
                    batch = []

                    batch_process_fn(old_batch)

                    validate_timer.reset()

            if batch:
                batch_process_fn(batch)

        logger.info(f">> {idx} Systems")
        self.pipeline_timer.end()

        return None

    def process_data_batch(self, system_batch: list[SystemSpansh]) -> None:
        process_timer = Timer(f"Spansh datadump batch process {len(system_batch)}")

        self.partitioner.insert_systems(system_batch)

        upsert_time = process_timer.running_for_str()
        logger.info(
            (f"Upserted {len(system_batch)} systems into postgres " f"(Took {upsert_time})({self.total_running_str()})")
        )

    async def run(self) -> None:
        for path in METADATA_DIR.rglob(COMMODITIES_YAML_FMT):
            self.partitioner.load_metadata_yaml_into_pg(path)

        await self.load_and_process_data(self.process_data_batch)
