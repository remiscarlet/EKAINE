from types import TracebackType
from typing import Any, Self, Sequence, Type

from sqlalchemy import CursorResult, Result, RowMapping, select, text, update
from sqlalchemy.orm import Session, selectinload

from ekaine.common.logging import get_logger
from ekaine.common.timer import Timer
from ekaine.common.utils import dur_to_interval_str
from ekaine.postgresql import SessionLocalEkaine
from ekaine.postgresql.db import (
    BodiesDB,
    FactionPresencesDB,
    FactionsDB,
    MiningMapCommoditiesDB,
    MiningMapsDB,
    RingsDB,
    SystemsDB,
)
from ekaine.postgresql.types import (
    HotspotResult,
    MiningAcquisitionResult,
    MiningReinforcementResult,
    ResolvedStationResult,
    SystemResult,
    TopCommodityResult,
)

logger = get_logger(__name__)


class BaseAdapter:
    def __init__(self, session: Session | None = None) -> None:
        self.session = session or SessionLocalEkaine()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type:
            self.session.rollback()


class ApiCommandAdapter(BaseAdapter):
    def get_acquirable_systems_from_origin(self, system_name: str) -> list[SystemResult]:
        stmt = text("SELECT * FROM api.get_acquirable_systems_from_origin(:system_name)")

        result = self.session.execute(stmt, {"system_name": system_name})

        rows: Sequence[RowMapping] = result.mappings().all()
        return [SystemResult(**row) for row in rows]

    def get_expandable_systems_in_range(self, system_name: str) -> list[SystemResult]:
        stmt = text("SELECT * FROM api.get_expandable_systems_in_range(:system_name)")

        result = self.session.execute(stmt, {"system_name": system_name})

        rows: Sequence[RowMapping] = result.mappings().all()
        return [SystemResult(**row) for row in rows]

    def get_hotspots_in_system(self, system_name: str) -> list[HotspotResult]:
        stmt = text("SELECT * FROM api.get_hotspots_in_system(:system_name)")

        result = self.session.execute(stmt, {"system_name": system_name})

        rows: Sequence[RowMapping] = result.mappings().all()
        return [HotspotResult(**row) for row in rows]

    def get_hotspots_in_system_by_commodities(
        self, system_name: str, commodities_filter: list[str]
    ) -> list[HotspotResult]:
        stmt = text(
            """SELECT * FROM api.get_hotspots_in_system_by_commodities(
                :system_name, :commodities_filter)"""
        )

        timer = Timer("get_hotspots_in_system_by_commodities")
        result = self.session.execute(
            stmt,
            {
                "system_name": system_name,
                "commodities_filter": commodities_filter,
            },
        )

        rows: Sequence[RowMapping] = result.mappings().all()
        rtn = [HotspotResult(**row) for row in rows]

        timer.end()
        return rtn

    def get_mining_expandable_systems_in_range(self, system_name: str) -> list[MiningAcquisitionResult]:
        stmt = text("SELECT * FROM api.get_mining_expandable_systems_in_range(:system_name)")

        result = self.session.execute(stmt, {"system_name": system_name})

        rows: Sequence[RowMapping] = result.mappings().all()
        return [MiningAcquisitionResult(**row) for row in rows]

    def get_top_reinforcement_mining_routes(
        self,
        power_name: str,
        power_states: list[str] | None = None,
        commodity_names: list[str] | None = None,
        ignored_ring_types: list[str] | None = None,
        min_sell_price: int = 50000,
        min_demand: int = 10,
        num_results: int = 25,
        max_data_age_dur_str: str = "3d",
    ) -> list[MiningReinforcementResult]:
        power_states = power_states or ["Exploited", "Fortified"]
        commodity_names = commodity_names or ["Monazite", "Platinum"]
        ignored_ring_types = ignored_ring_types or ["Metal Rich"]

        stmt = text(
            """
            SELECT *
            FROM api.get_top_reinforcement_mining_routes(
                :power_name, :power_states, :commodity_names, :ignored_ring_types,
                :min_sell_price, :min_demand, :num_results, :max_data_age_interval
            )
        """
        )

        max_data_age_interval = dur_to_interval_str(max_data_age_dur_str)

        result = self.session.execute(
            stmt,
            {
                "power_name": power_name,
                "power_states": power_states,
                "commodity_names": commodity_names,
                "ignored_ring_types": ignored_ring_types,
                "min_sell_price": min_sell_price,
                "min_demand": min_demand,
                "num_results": num_results,
                "max_data_age_interval": max_data_age_interval,
            },
        )

        rows: Sequence[RowMapping] = result.mappings().all()
        return [MiningReinforcementResult(**row) for row in rows]

    def get_systems_with_power(self, power_name: str, power_states: list[str] | None = None) -> list[SystemResult]:
        params: dict[str, str | list[str]] = {"power_name": power_name}
        if power_states:
            params["power_states"] = power_states
            stmt = text("SELECT * FROM api.get_systems_with_power(:power_name, :power_states)")
        else:
            stmt = text("SELECT * FROM api.get_systems_with_power(:power_name)")

        logger.debug(str(stmt))
        result = self.session.execute(stmt, params)

        rows: Sequence[RowMapping] = result.mappings().all()
        return [SystemResult(**row) for row in rows]

    def get_top_commodities_in_system(
        self, system_name: str, comms_per_station: int, min_supplydemand: int, is_buying: bool
    ) -> list[TopCommodityResult]:
        stmt = text(
            """SELECT * FROM api.get_top_commodities_in_system(
                :system_name, :comms_per_station, :min_supplydemand, :is_buying)"""
        )

        result = self.session.execute(
            stmt,
            {
                "system_name": system_name,
                "comms_per_station": comms_per_station,
                "min_supplydemand": min_supplydemand,
                "is_buying": is_buying,
            },
        )

        rows: Sequence[RowMapping] = result.mappings().all()
        return [TopCommodityResult(**row) for row in rows]


class SystemsAdapter(BaseAdapter):
    def get_system(self, system_name: str) -> SystemsDB:
        query = select(SystemsDB).where(SystemsDB.name == system_name)
        logger.debug(str(query))
        system = self.session.scalars(query).first()
        if not system:
            raise ValueError(f"System '{system_name}' not found")
        return system

    def get_system_by_substring(self, system_name_substring: str) -> list[SystemsDB]:
        # Can't seem to lower() using sqlalchemy constructs. Indexing is reliant on lower()
        stmt = (
            select(SystemsDB)
            .from_statement(
                text(
                    """select s.*
                        from core.systems s
                        where lower(s.name) like '%' || lower(:system_name_substring) || '%';"""
                )
            )
            .params(system_name_substring=system_name_substring)
        )

        logger.info(str(stmt))
        systems: list[SystemsDB] = list(self.session.scalars(stmt).all())

        if not systems:
            raise ValueError(f"Systems with prefix '{system_name_substring}' not found")
        return list(systems)


class BodiesAdapter(BaseAdapter):
    def get_body(self, body_name: str) -> BodiesDB:
        query = select(BodiesDB).where(BodiesDB.name == body_name)
        logger.debug(str(query))
        body = self.session.scalars(query).first()
        if not body:
            raise ValueError(f"Body '{body_name}' not found")
        return body

    def get_bodies_by_system_id(self, system_id: int) -> list[BodiesDB]:
        query = select(BodiesDB).where(BodiesDB.system_id == system_id)
        logger.debug(str(query))
        logger.debug(system_id)
        bodies = self.session.scalars(query).all()
        if not bodies:
            raise ValueError(f"No bodies in system id '{system_id}' found")
        return list(bodies)

    def get_bodies_by_substring(self, body_name_substring: str) -> list[BodiesDB]:
        # Can't seem to lower() using sqlalchemy constructs. Indexing is reliant on lower()
        stmt = (
            select(BodiesDB)
            .from_statement(
                text(
                    """select b.*
                        from core.systems s
                        join core.bodies b on s.id = b.system_id
                        where lower(b.name) like '%' || lower(:body_name_substring) || '%';"""
                )
            )
            .params(body_name_substring=body_name_substring)
        )

        logger.info(str(stmt))
        bodies: list[BodiesDB] = list(self.session.scalars(stmt).all())

        if not bodies:
            raise ValueError(f"Bodies with prefix '{body_name_substring}' not found")
        return list(bodies)


class RingsAdapter(BaseAdapter):
    def get_ring(self, ring_name: str) -> RingsDB:
        query = select(RingsDB).where(RingsDB.name == ring_name)
        logger.debug(str(query))
        ring = self.session.scalars(query).first()
        if not ring:
            raise ValueError(f"Ring '{ring_name}' not found")
        return ring

    def get_ring_by_system_and_name(self, system: SystemsDB, ring_name: str) -> RingsDB:
        # Can't seem to lower() using sqlalchemy constructs. Indexing is reliant on lower()
        stmt = (
            select(RingsDB)
            .from_statement(
                text(
                    """select r.*
                        from core.systems s
                        join core.bodies b on s.id = b.system_id
                        join core.rings r on b.id = r.body_id
                        where s.id = :system_id
                        and lower(r.name) like lower(:ring_name);"""
                )
            )
            .params(system_id=system.id, ring_name=ring_name)
        )

        logger.info(str(stmt))
        rings: list[RingsDB] = list(self.session.scalars(stmt).all())

        if not rings:
            raise ValueError(f"No rings found in system '{system.id}'")
        elif len(rings) > 1:
            raise ValueError("Supplied name returned multiple rings!")

        return rings[0]

    def get_rings_by_system_and_substring(self, system: SystemsDB, ring_name_substring: str) -> list[RingsDB]:
        # Can't seem to lower() using sqlalchemy constructs. Indexing is reliant on lower()
        stmt = (
            select(RingsDB)
            .from_statement(
                text(
                    """select distinct on (r.name) r.*
                        from core.systems s
                        join core.bodies b on s.id = b.system_id
                        join core.rings r on b.id = r.body_id
                        where s.id = :system_id
                        and lower(r.name) like '%' || lower(:ring_name_substring) || '%';"""
                )
            )
            .params(system_id=system.id, ring_name_substring=ring_name_substring)
        )

        logger.info(str(stmt))
        rings: list[RingsDB] = list(self.session.scalars(stmt).all())

        if not rings:
            raise ValueError(f"No rings found in system '{system.id}'")

        return rings


class MiningMapsAdapter(BaseAdapter):
    def update_mining_map(self, map_id: int, payload: dict[str, Any]) -> Result[Any]:
        stmt = update(MiningMapsDB).where(MiningMapsDB.id == map_id).values(**payload)
        result = self.session.execute(stmt)

        self.session.commit()

        return result

    def get_mining_map(self, mining_map_name: str) -> MiningMapsDB:
        stmt = (
            select(MiningMapsDB)
            .join(MiningMapCommoditiesDB)
            .options(
                selectinload(MiningMapsDB.commodities),
                selectinload(MiningMapsDB.system),
                selectinload(MiningMapsDB.body),
                selectinload(MiningMapsDB.ring),
            )
            .where(MiningMapsDB.name == mining_map_name)
        )
        logger.debug(str(stmt))
        mining_map = self.session.scalars(stmt).first()
        if not mining_map:
            raise ValueError(f"Mining Map '{mining_map_name}' not found")
        return mining_map

    def get_all_mining_maps(self) -> list[MiningMapsDB]:
        stmt = select(MiningMapsDB).options(
            selectinload(MiningMapsDB.commodities),
            selectinload(MiningMapsDB.system),
            selectinload(MiningMapsDB.body),
            selectinload(MiningMapsDB.ring),
        )
        logger.debug(str(stmt))
        mining_maps: list[MiningMapsDB] = list(self.session.scalars(stmt).all())
        return mining_maps

    def get_mining_maps_by_filters(
        self,
        system_name_substring: str | None = None,
        mining_map_substring: str | None = None,
        commodities_list_str: str | None = None,
    ) -> list[MiningMapsDB]:
        """Get mining maps by a variety of filters and pagination options.

        If options are not provided, they are ignored/not applied to the filter.

        Args:
            system_name_substring (str | None, optional): System name substring to search by. Defaults to None.
            mining_map_substring (str | None, optional): Mining map name substring to search by. Defaults to None.
            commodities_list_str (str | None, optional): List of commodity names to search maps by. Defaults to None.

        Returns:
            tuple[list[MiningMapsDB], bool]: Second value indicates whether there are additional pages of results left.
        """

        if commodities_list_str is None:
            commodities = None
        else:
            commodities_and_tonnage = MiningMapCommoditiesDB.parse_commodities_str(commodities_list_str)
            commodities = [tup[0] for tup in commodities_and_tonnage]

        stmt = (
            select(MiningMapsDB)
            .options(
                selectinload(MiningMapsDB.commodities),
                selectinload(MiningMapsDB.system),
                selectinload(MiningMapsDB.body),
                selectinload(MiningMapsDB.ring),
            )
            .from_statement(
                text(
                    """select distinct on (mm.id, mm.name) mm.*
                        from core.systems s
                        join core.mining_maps mm on mm.system_id = s.id
                        join core.mining_map_commodities mmc on mmc.mining_map_id = mm.id
                        where (
                            :mining_map_substring is null
                            or lower(mm.name) like '%' || lower(:mining_map_substring) || '%'
                        )
                        and (
                            :system_name_substring is null
                            or lower(s.name) like '%' || lower(:system_name_substring) || '%'
                        )
                        and (
                            :map_commodities_list IS NULL
                            or mmc.commodity_sym = ANY(:map_commodities_list)
                        )
                        order by mm.name asc
                    ;"""
                )
            )
            .params(
                system_name_substring=system_name_substring,
                mining_map_substring=mining_map_substring,
                map_commodities_list=commodities,
            )
        )

        logger.info(str(stmt))
        mining_maps: list[MiningMapsDB] = list(self.session.scalars(stmt).all())

        return mining_maps


class StationsAdapter(BaseAdapter):
    def get_station(self, station_name: str, system_id: int) -> ResolvedStationResult:
        stmt = text(
            """select *
                 from derived.resolved_stations_view
                where name = :station_name
                  and system_id = :system_id
            """
        )

        result = self.session.execute(
            stmt,
            {
                "station_name": station_name,
                "system_id": system_id,
            },
        )

        rows: Sequence[RowMapping] = result.mappings().all()

        if len(rows) == 0:
            raise ValueError(f"Could not find station with name '{station_name}' and system id '{system_id}'")
        elif len(rows) > 1:
            raise ValueError(f"Somehow got multiple stations with name '{station_name}' and system id '{system_id}'")

        return ResolvedStationResult(**rows[0])

    def get_stations_by_substring(self, station_name_substring: str) -> list[ResolvedStationResult]:
        stmt = text(
            """select rsv.*
            from derived.resolved_stations_view rsv
            where lower(rsv.name) like '%' || lower(:station_name_substring) || '%';"""
        )

        logger.info(str(stmt))
        result = self.session.execute(stmt, {"station_name_substring": station_name_substring})

        rows: Sequence[RowMapping] = result.mappings().all()
        return [ResolvedStationResult(**row) for row in rows]


class FactionsAdapter(BaseAdapter):
    def get_faction(self, faction_name: str) -> FactionsDB:
        query = select(FactionsDB).where(FactionsDB.name == faction_name)
        faction = self.session.scalars(query).first()
        if not faction:
            raise ValueError(f"Faction '{faction_name}' not found")
        return faction


class FactionPresencesAdapter(BaseAdapter):
    def get_faction_presence(self, faction_id: int, system_id: int) -> FactionPresencesDB:
        query = select(FactionPresencesDB).where(
            FactionPresencesDB.faction_id == faction_id, FactionPresencesDB.system_id == system_id
        )
        faction_presence = self.session.scalars(query).first()
        if not faction_presence:
            raise ValueError(f"Faction Presence for faction '{faction_id}' in system '{system_id}' not found")
        return faction_presence
