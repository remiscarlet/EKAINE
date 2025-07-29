from sqlalchemy.orm import Session

from ekaine.common.logging import get_logger
from ekaine.postgresql.adapter import (
    FactionPresencesAdapter,
    FactionsAdapter,
    StationsAdapter,
    SystemsAdapter,
)
from ekaine.postgresql.db import MarketCommoditiesDB
from ekaine.postgresql.timeseries import RawMarketCommodityFactionStateTimeseries
from ekaine.postgresql.utils import upsert_all
from gen.eddn_models import commodity_v3_0

logger = get_logger(__name__)


def process_model(session: Session, model: commodity_v3_0.Model) -> None:
    """
    Process commodity-v3.0 EDDN messages

    Updates:
    - MarketCommoditiesDB

    """
    # May want to filter any stations with "invalid characters" like '$' or ';'
    # Some station names come through like '$EXT_PANEL_ColonisationShip; Skvortsov Territory'
    msg = model.message
    system_name = msg.systemName
    station_name = msg.stationName

    # MarketCommoditiesDB

    try:
        with SystemsAdapter() as adapter:
            system = adapter.get_system(system_name)
    except ValueError as e:
        logger.warning(f"Encountered system name that we don't know about! '{system_name}' - {str(e)}")
        return

    try:
        with StationsAdapter(session) as adapter:
            station = adapter.get_station(station_name, system.id)
    except ValueError as e:
        logger.warning(
            "Encountered station name that we don't know about! "
            f"Station name '{station_name}', System id: '{system.id}'"
            f" - {str(e)}"
        )
        return

    commodity_dicts = MarketCommoditiesDB.to_dicts_from_eddn(model, station.id)
    upsert_all(session, MarketCommoditiesDB, commodity_dicts)

    logger.info(
        "[Market Commodities DB Updated] " f"{msg.systemName} - {station_name} - {len(msg.commodities)} Commodities"
    )

    # RawMarketCommodityFactionStateTimeseries

    if system.controlling_faction_id is None:
        logger.warning(
            "Tried saving a RawMarketCommodityFactionStateTimeseries for a system with no controlling faction! "
            f"System: '{system_name}'"
        )
        return

    try:
        with FactionPresencesAdapter(session) as adapter:
            system_controlling_faction = adapter.get_faction_presence(system.controlling_faction_id, system.id)
    except ValueError as e:
        logger.warning(
            "Encountered a faction we didn't know its FactionPresence about! "
            f"System Controlling Faction Id '{system.controlling_faction_id}', System id: '{system.id}'"
            f" - {str(e)}"
        )
        return

    if station.controlling_faction is None:
        logger.warning(
            "Tried saving a RawMarketCommodityFactionStateTimeseries for a station with no controlling faction! "
            f"Station: '{station}'"
        )
        return

    try:
        with FactionsAdapter(session) as adapter:
            station_faction = adapter.get_faction(station.controlling_faction)
    except ValueError as e:
        logger.warning(
            "Encountered a faction we didn't know about! "
            f"Faction Name '{station.controlling_faction}', Station id: '{station.id}'"
            f" - {str(e)}"
        )
        return

    try:
        with FactionPresencesAdapter(session) as adapter:
            station_controlling_faction = adapter.get_faction_presence(station_faction.id, system.id)
    except ValueError as e:
        logger.warning(
            "Encountered a faction we didn't know its FactionPresence about! "
            f"Station Controlling Faction id '{station_faction.id}', System id: '{system.id}'"
            f" - {str(e)}"
        )
        return

    commodity_faction_state_dicts = RawMarketCommodityFactionStateTimeseries.to_dicts_from_eddn(
        model,
        system.id,
        station.id,
        system_controlling_faction,
        station_controlling_faction,
    )

    upsert_all(session, RawMarketCommodityFactionStateTimeseries, commodity_faction_state_dicts)

    logger.info("[Market Commodity Faction State Timeseries Updated] " f"{msg.systemName} - {station_name}")
