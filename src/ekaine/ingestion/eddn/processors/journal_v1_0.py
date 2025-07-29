import traceback
from pprint import pformat
from typing import cast

from sqlalchemy.orm import Session

from ekaine.common.logging import get_logger
from ekaine.postgresql.adapter import (
    BodiesAdapter,
    FactionsAdapter,
    RingsAdapter,
    StationsAdapter,
)
from ekaine.postgresql.db import (
    BodiesDB,
    FactionPresencesDB,
    FactionsDB,
    HotspotsDB,
    RingsDB,
    StationsDB,
    SystemsDB,
)
from ekaine.postgresql.timeseries import (
    RawFactionPresencesTimeseries,
    RawPowerConflictProgressTimeseries,
    RawSystemsTimeseries,
)
from ekaine.postgresql.utils import upsert_all
from gen.eddn_models import journal_v1_0

logger = get_logger(__name__)


def model_to_faction_name_to_id_mapping(model: journal_v1_0.Model) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for faction in model.message.Factions or []:
        faction_name = faction.Name
        if faction_name is None:
            logger.warning(f"Encountered Faction object with no Name! '{pformat(faction)}'")
            continue
        with FactionsAdapter() as adapter:
            faction_obj = adapter.get_faction(faction_name)
        if faction_obj is not None:
            mapping[faction_name] = faction_obj.id

    return mapping


def process_saa_signals_found(model: journal_v1_0.Model) -> None:
    if model.message.event.value != "SAASignalsFound":
        raise ValueError(f"Expected a SAASignalsFound Journal event but got '{model.message.event}'!")
    pass


def process_system_entities(
    session: Session, model: journal_v1_0.Model, faction_id_mapping: dict[str, int]
) -> SystemsDB:
    """Process System related entries from the journal-v1.0 EDDN event"""
    controlling_faction_name = getattr(model.message, "SystemFaction", {}).get("Name")
    controlling_faction_id = (
        faction_id_mapping.get(cast(str, controlling_faction_name)) if controlling_faction_name is not None else None
    )

    system_dict = SystemsDB.to_dict_from_eddn(model, controlling_faction_id)
    systems = upsert_all(session, SystemsDB, [system_dict])

    if len(systems) == 0:
        raise RuntimeError("Upserted a system but got no object back!")
    system = systems[0]
    logger.info(f"[System DB Updated] {system.name}")

    system_dict = RawSystemsTimeseries.to_dict_from_eddn(model, system.id, controlling_faction_id)
    upsert_all(session, RawSystemsTimeseries, [system_dict])

    return system


def process_station_entities(session: Session, model: journal_v1_0.Model, system: SystemsDB) -> None:
    """Process Station related entries from the journal-v1.0 EDDN event"""

    station_dict = StationsDB.to_dict_from_eddn(
        model,
        system.id,
        lambda body_name: BodiesAdapter().get_body(body_name),
        lambda station_name, system_id: StationsAdapter().get_station(station_name, system_id),
        lambda faction_name: FactionsAdapter().get_faction(faction_name),
    )

    if station_dict is None:
        # Was not a station-including Journal entry
        return

    stations = upsert_all(session, StationsDB, [station_dict])
    logger.info(f"[Stations DB Updated] {stations[0].name} ({stations[0].type})")

    # if len(systems) == 0:
    #     raise RuntimeError("Upserted a system but got no object back!")
    # system = systems[0]

    # system_dict = RawSystemsTimeseries.to_dict_from_eddn(model, system.id, controlling_faction_id)
    # upsert_all(session, RawSystemsTimeseries, [system_dict])


def process_faction_entities(session: Session, model: journal_v1_0.Model) -> None:
    """Process Factions entries from the journal-v1.0 EDDN event"""
    faction_dicts = FactionsDB.to_dicts_from_eddn(model)
    try:
        upsert_all(session, FactionsDB, faction_dicts)
    except Exception:
        logger.warning(traceback.format_exc())
        logger.warning(pformat(faction_dicts))
        logger.warning(pformat(model.message.Factions))
        return

    if faction_dicts:
        logger.info(f"[Factions DB Updated] {model.message.StarSystem} - {len(faction_dicts)} factions")


def process_body_entities(session: Session, model: journal_v1_0.Model, system: SystemsDB) -> None:
    """Process Bodies entries from the journal-v1.0 EDDN event"""
    body_dict = BodiesDB.to_dict_from_eddn(model, system.id)
    if body_dict is None:
        return

    try:
        upsert_all(session, BodiesDB, [body_dict])
    except Exception:
        logger.warning(traceback.format_exc())
        logger.warning(pformat(body_dict))
        logger.warning(pformat(model.message.Factions))
        return

    logger.info(f"[Bodies DB Updated] {model.message.StarSystem} - {body_dict['name']}")


def process_ring_entities(session: Session, model: journal_v1_0.Model) -> None:
    """Process Rings entries from the journal-v1.0 EDDN event"""
    ring_dicts = RingsDB.to_dicts_from_eddn(
        model,
        lambda body_name: BodiesAdapter().get_body(body_name),
    )
    if not ring_dicts:
        return None

    try:
        upsert_all(session, RingsDB, ring_dicts, list(RingsDB.generated_columns))
    except Exception:
        logger.warning(traceback.format_exc())
        logger.warning(pformat(ring_dicts))
        return None

    logger.info(f"[Rings DB Updated] {model.message.StarSystem} - {[r['name'] for r in ring_dicts]}")


def process_faction_presence_entities(
    session: Session, model: journal_v1_0.Model, system: SystemsDB, faction_id_mapping: dict[str, int]
) -> None:
    """Process Faction Presences entries from the journal-v1.0 EDDN event"""
    faction_presence_dicts = FactionPresencesDB.to_dicts_from_eddn(model, system.id, faction_id_mapping)
    faction_presence_ts_dicts = RawFactionPresencesTimeseries.to_dicts_from_eddn(model, system.id, faction_id_mapping)
    try:
        upsert_all(session, FactionPresencesDB, faction_presence_dicts)
        upsert_all(session, RawFactionPresencesTimeseries, faction_presence_ts_dicts)
    except Exception:
        logger.warning(traceback.format_exc())
        logger.warning(pformat(faction_presence_dicts))
        logger.warning(pformat(model.message.Factions))
        return

    if len(faction_presence_dicts + faction_presence_ts_dicts):
        if len(faction_presence_dicts) == len(faction_presence_ts_dicts):
            logger.info(
                f"[Faction Presence DB + Timeseries Updated] {system.name} - {len(faction_presence_dicts)} factions"
            )
        else:
            logger.warning("?? Updated different numbers of rows in the DB vs Timeseries for Faction Presence!")
            logger.info(
                f"[Faction Presence DB + Timeseries Updated] {system.name} - {len(faction_presence_dicts)} factions"
            )
            logger.info(
                f"[Faction Presence Timeseries Updated] {system.name} - {len(faction_presence_ts_dicts)} factions"
            )


def process_powerplay_entities(session: Session, model: journal_v1_0.Model, system: SystemsDB) -> None:
    """Process Powerplay related entries from the journal-v1.0 EDDN event"""
    power_conflict_progress_dicts = RawPowerConflictProgressTimeseries.to_dicts_from_eddn(model, system.id)

    if power_conflict_progress_dicts:
        try:
            upsert_all(session, RawPowerConflictProgressTimeseries, power_conflict_progress_dicts)
        except Exception:
            logger.warning(traceback.format_exc())
            logger.warning(pformat(power_conflict_progress_dicts))
            return

        logger.info(
            "[Power Conflict Progress Timeseries Updated] "
            f"{system.name} - {len(power_conflict_progress_dicts)} powers"
        )


def process_hotspot_entities(session: Session, model: journal_v1_0.Model, system: SystemsDB) -> None:
    msg = model.message
    body_name = getattr(msg, "BodyName", None)
    if body_name is None:
        return None
    elif "Ring" not in body_name:
        return None

    hotspot_dicts = HotspotsDB.to_dicts_from_eddn(
        model,
        lambda ring_name: RingsAdapter().get_ring(ring_name),
    )

    if hotspot_dicts:
        try:
            upsert_all(session, HotspotsDB, hotspot_dicts)
        except Exception:
            logger.warning(traceback.format_exc())
            logger.warning(pformat(hotspot_dicts))
            return

        logger.info("[Hotspots DB Updated] " f"{body_name} - {len(hotspot_dicts)} Hotspots")


def process_model(session: Session, model: journal_v1_0.Model) -> None:
    """
    Process journal-v1.0 EDDN messages

    Updates:
    - SystemsDB
    - RawSystemsTimeseries
    - FactionPresencesDB
    - RawFactionPresencesTimeseries
    - SignalsTimeseries
    - RawPowerConflictProgressTimeseries
    """
    event_name = model.message.event.value
    logger.trace(f"Processing event {event_name} in {model.message.StarSystem}")

    # Handle FactionPresences updates
    if event_name in ["FSDJump", "Location"]:
        process_faction_entities(session, model)

    # Handle SystemsDB updates
    faction_id_mapping = model_to_faction_name_to_id_mapping(model)
    system = process_system_entities(session, model, faction_id_mapping)

    if system is None:
        logger.error(f"Could not upsert system! '{model.message.StarSystem}'")
        return

    if event_name in ["Scan", "Location", "SAASignalsFound"]:
        process_body_entities(session, model, system)

    if event_name in ["Scan", "Location", "SAASignalsFound"]:
        process_ring_entities(session, model)

    if event_name in ["FSDJump", "Location"]:
        process_faction_presence_entities(session, model, system, faction_id_mapping)

    if event_name in ["Docked", "Location"]:
        # Order matters - must come after FactionPresences
        process_station_entities(session, model, system)

    if event_name in ["FSDJump"]:
        process_powerplay_entities(session, model, system)

    if event_name in ["SAASignalsFound"]:
        process_hotspot_entities(session, model, system)


"""
    - Docked
        'Body': 'Col 285 Sector RK-N c7-15 A 6',
        'BodyType': 'Planet',
        'DistFromStarLS': 307.31049,
        'LandingPads': {'Large': 16, 'Medium': 8, 'Small': 8},
        'MarketID': 3955798530,
        'Multicrew': False,
        'StarPos': [-305.09375, 36.4375, -31.90625],
        'StarSystem': 'Col 285 Sector RK-N c7-15',
        'StationEconomies': [{'Name': '$economy_Colony;', 'Proportion': 1.0}],
        'StationEconomy': '$economy_Colony;',
        'StationFaction': {'Name': 'Brewer Corporation'},
        'StationGovernment': '$government_Corporate;',
        'StationName': "$EXT_PANEL_ColonisationShip; Dovzhenko's Pride",
        'StationServices': ['dock', 'autodock', 'commodities', 'contacts', 'missions', 'rearm','refuel', 'repair',
                            'engineer', 'facilitator', 'flightcontroller', 'stationoperations', 'searchrescue',
                            'stationMenu', 'colonisationcontribution'],
        'StationType': 'SurfaceStation',
        'SystemAddress': 4206484296394,
        'Taxi': False,
        'event': 'Docked', 'horizons': True, 'odyssey': True, 'timestamp': '2025-05-22T00:52:11Z'}}
        ------
        'DistFromStarLS': 263.984648,
        'LandingPads': {'Large': 5, 'Medium': 12, 'Small': 6},
        'MarketID': 4252975619,
        'Multicrew': False,
        'StarPos': [-272.40625, 0.9375, -194.3125],
        'StarSystem': 'Col 285 Sector JO-O b7-6',
        'StationEconomies': [
            {'Name': '$economy_Refinery;', 'Proportion': 1.4}, {'Name': '$economy_Industrial;', 'Proportion': 1.4},
            {'Name': '$economy_Military;', 'Proportion': 0.05}
        ],
        'StationEconomy': '$economy_Refinery;',
        'StationFaction': {'FactionState': 'Expansion', 'Name': 'Selous Syndicate'},
        'StationGovernment': '$government_Corporate;',
        'StationName': 'Wordsworth Enterprise',
        'StationServices': [
            'dock', 'autodock', 'commodities', 'contacts', 'missions', 'outfitting', 'crewlounge', 'rearm', 'refuel',
            'repair', 'shipyard', 'engineer', 'missionsgenerated', 'flightcontroller', 'stationoperations',
            'powerplay', 'searchrescue', 'stationMenu', 'shop', 'livery', 'socialspace', 'registeringcolonisation'
        ],
        'StationType': 'Coriolis',
        'SystemAddress': 13861335934297,
        'Taxi': False, 'event': 'Docked', 'horizons': True, 'odyssey': True, 'timestamp': '2025-06-25T04:08:55Z'}}
    - FSDJump
        'Body': 'HIP 69230 A',
        'BodyID': 1,
        'BodyType': 'Star',
        'Factions': [
            {'Allegiance': 'Federation', 'FactionState': 'None', 'Government': 'Democracy',
                'Happiness': '$Faction_HappinessBand2;', 'Influence': 0.086913, 'Name': 'HIP 69913 Resistance'},
            {'Allegiance': 'Federation', 'FactionState': 'None', 'Government': 'Confederacy',
                'Happiness': '$Faction_HappinessBand2;', 'Influence': 0.240759, 'Name': 'Confederacy of HIP 69230'},
            {'Allegiance': 'Alliance', 'FactionState': 'None', 'Government': 'Anarchy',
                'Happiness': '$Faction_HappinessBand2;', 'Influence': 0.05994, 'Name': 'Negasta Family'},
            {'ActiveStates': [{'State': 'CivilUnrest'}], 'Allegiance': 'Independent', 'FactionState': 'CivilUnrest',
                'Government': 'Anarchy', 'Happiness': '$Faction_HappinessBand2;',
                'Influence': 0.026973, 'Name': 'HIP 69230 Mafia'},
            {'Allegiance': 'Independent', 'FactionState': 'None', 'Government': 'Corporate',
                'Happiness': '$Faction_HappinessBand2;', 'Influence': 0.14985, 'Name': 'Skyline Monopoly',
                'RecoveringStates': [{'State': 'Expansion', 'Trend': 0}]},
            {'Allegiance': 'Independent', 'FactionState': 'None', 'Government': 'Theocracy',
                'Happiness': '$Faction_HappinessBand2;', 'Influence': 0.093906, 'Name': 'Wild Priest Corps'},
            {'Allegiance': 'Independent', 'FactionState': 'None', 'Government': 'Cooperative',
                'Happiness': '$Faction_HappinessBand2;', 'Influence': 0.341658,
                'Name': 'Institute of Galactic Exploration and Research (IGER)'}],
        'Multicrew': False,
        'Population': 30632,
        'PowerplayConflictProgress': [{'ConflictProgress': 0.0, 'Power': 'Felicia Winters'}],
        'PowerplayState': 'Unoccupied',
        'Powers': ['Felicia Winters'],
        'StarPos': [-30.4375, 150.15625, 38.28125],
        'StarSystem': 'HIP 69230',
        'SystemAddress': 1487946156395,
        'SystemAllegiance': 'Independent',
        'SystemEconomy': '$economy_Extraction;',
        'SystemFaction': {'Name': 'Institute of Galactic Exploration and Research (IGER)'},
        'SystemGovernment': '$government_Cooperative;',
        'SystemSecondEconomy': '$economy_Agri;',
        'SystemSecurity': '$SYSTEM_SECURITY_low;',
        'Taxi': False,
        'event': 'FSDJump', 'horizons': True, 'odyssey': True, 'timestamp': '2025-05-22T00:52:14Z'}}
    - Scan
        'AscendingNode': -168.247415,
        'Atmosphere': 'thin ammonia atmosphere',
        'AtmosphereComposition': [{'Name': 'Ammonia', 'Percent': 100.0}],
        'AtmosphereType': 'Ammonia',
        'AxialTilt': -0.103357,
        'BodyID': 7,
        'BodyName': 'Gru Dryou KA-D c1-18 2',
        'Composition': {'Ice': 0.0, 'Metal': 0.332021, 'Rock': 0.667979},
        'DistanceFromArrivalLS': 855.406092,
        'Eccentricity': 0.003465,
        'Landable': True,
        'MassEM': 0.005602,
        'Materials': [{'Name': 'iron', 'Percent': 21.163963}, {'Name': 'nickel', 'Percent': 16.007536},
                        {'Name': 'sulphur', 'Percent': 15.097793}, {'Name': 'carbon', 'Percent': 12.695681},
                        {'Name': 'chromium', 'Percent': 9.518136}, {'Name': 'manganese', 'Percent': 8.7405},
                        {'Name': 'phosphorus', 'Percent': 8.127993}, {'Name': 'vanadium', 'Percent': 5.197133},
                        {'Name': 'molybdenum', 'Percent': 1.381994}, {'Name': 'tellurium', 'Percent': 1.145087},
                        {'Name': 'mercury', 'Percent': 0.924195}],
        'MeanAnomaly': 115.536092,
        'OrbitalInclination': 1.131212,
        'OrbitalPeriod': 78393130.302429,
        'Parents': [{'Star': 0}],
        'Periapsis': 217.599729,
        'PlanetClass': 'High metal content body',
        'Radius': 1166545.25,
        'RotationPeriod': 61065.702246,
        'ScanType': 'AutoScan',
        'SemiMajorAxis': 256059342622.75696,
        'StarPos': [6284.34375, -295.8125, 5383.875],
        'StarSystem': 'Gru Dryou KA-D c1-18',
        'SurfaceGravity': 1.640703,
        'SurfacePressure': 127.8787,
        'SurfaceTemperature': 158.528915,
        'SystemAddress': 5042190718730,
        'TerraformState': '',
        'TidalLock': False,
        'Volcanism': '',
        'WasDiscovered': True,
        'WasMapped': False,
        'event': 'Scan', 'horizons': True, 'odyssey': True, 'timestamp': '2025-05-22T00:52:11Z'}}
    Message(
        timestamp=datetime.datetime(2025, 6, 10, 7, 47, 12, tzinfo=TzInfo(UTC)),
        event=<Event.Scan: 'Scan'>, horizons=True, odyssey=True,
        StarSystem='Blu Aec NW-A c27-11',
        StarPos=[7674.78125, -2.59375, 12932.8125],
        SystemAddress=3120394411242,
        Factions=None,
        AscendingNode=-107.497578,
        Atmosphere='helium atmosphere',
        AtmosphereComposition=[{'Name': 'Helium', 'Percent': 86.773819},
            {'Name': 'Hydrogen', 'Percent': 8.186209}, {'Name': 'Nitrogen', 'Percent': 2.866912}],
        AtmosphereType='Helium',
        AxialTilt=-0.166192,
        BodyID=65,
        BodyName='Blu Aec NW-A c27-11 6',
        Composition={'Ice': 0.654312, 'Metal': 0.097244, 'Rock': 0.201581},
        DistanceFromArrivalLS=4029.519929,
        Eccentricity=0.000281,
        Landable=False,
        MassEM=14.891384,
        MeanAnomaly=90.438053,
        OrbitalInclination=0.328763,
        OrbitalPeriod=825363802.909851,
        Parents=[{'Star': 0}],
        Periapsis=272.068599,
        PlanetClass='Icy body',
        Radius=17632382.0,
        ReserveLevel='PristineResources',
        Rings=[
            {'InnerRad': 29300000.0, 'MassMT': 12501000000.0, 'Name': 'Blu Aec NW-A c27-11 6 A Ring',
             'OuterRad': 35610000.0, 'RingClass': 'eRingClass_Rocky'},
            {'InnerRad': 35710000.0, 'MassMT': 185190000000.0, 'Name': 'Blu Aec NW-A c27-11 6 B Ring',
             'OuterRad': 85649000.0, 'RingClass': 'eRingClass_Icy'}],
        RotationPeriod=73887.364778,
        ScanType='Detailed',
        SemiMajorAxis=1208016991615.2954,
        SurfaceGravity=19.090726,
        SurfacePressure=195433.140625,
        SurfaceTemperature=67.860588,
        TerraformState='',
        TidalLock=False,
        Volcanism='water geysers volcanism',
        WasDiscovered=False,
        WasMapped=False)

    Message(
        timestamp=datetime.datetime(2025, 6, 10, 7, 47, 5, tzinfo=TzInfo(UTC)),
        event=<Event.Scan: 'Scan'>,
        horizons=True,
        odyssey=True,
        StarSystem='Eta Corvi',
        StarPos=[36.71875, 43.03125, 18.78125],
        SystemAddress=2381316098411,
        Factions=None,
        AbsoluteMagnitude=6.306061,
        Age_MY=1664,
        AscendingNode=-71.248025,
        AxialTilt=0.0,
        BodyID=4,
        BodyName='Eta Corvi C',
        DistanceFromArrivalLS=6239.961907,
        Eccentricity=0.008687,
        Luminosity='Vab',
        MeanAnomaly=180.137658,
        OrbitalInclination=-22.55414,
        OrbitalPeriod=727324604.988098,
        Parents=[{'Null': 0}],
        Periapsis=247.23819,
        Radius=522919712.0,
        RotationPeriod=288500.489116,
        ScanType='AutoScan',
        SemiMajorAxis=1488530218601.2268,
        StarType='K',
        StellarMass=0.691406,
        Subclass=3,
        SurfaceTemperature=4744.0,
        WasDiscovered=True,
        WasMapped=False)
    - Location
        'Body': 'HIP 77263 ABC 2 a',
        'BodyID': 28,
        'BodyType': 'Planet',
        'DistFromStarLS': 661.385721,
        'Docked': True,
        'Factions': [
            {'Allegiance': 'Independent', 'FactionState': 'None', 'Government': 'Corporate',
                'Happiness': '$Faction_HappinessBand2;', 'Influence': 0.237713, 'Name': 'Sirius Corporation',
                'PendingStates': [{'State': 'Expansion', 'Trend': 0}]},
            {'Allegiance': 'Independent', 'FactionState': 'None', 'Government': 'Corporate',
                'Happiness': '$Faction_HappinessBand2;', 'Influence': 0.517553, 'Name': 'Rajukru Blue AdvInt'},
            {'Allegiance': 'Independent', 'FactionState': 'None', 'Government': 'Anarchy',
                'Happiness': '$Faction_HappinessBand2;', 'Influence': 0.052156,
                'Name': 'Vodyakamana Purple Syndicate'},
            {'Allegiance': 'Independent', 'FactionState': 'None', 'Government': 'Democracy',
            'Happiness': '$Faction_HappinessBand2;', 'Influence': 0.192578, 'Name': 'United Systems Commonwealth'}],
        'MarketID': 3956812290,
        'Multicrew': False,
        'Population': 110483,
        'StarPos': [-126.8125, 149.3125, 21.5],
        'StarSystem': 'HIP 77263',
        'StationEconomies': [{'Name': '$economy_Colony;', 'Proportion': 1.0}],
        'StationEconomy': '$economy_Colony;',
        'StationFaction': {'Name': 'Brewer Corporation'},
        'StationGovernment': '$government_Corporate;',
        'StationName': 'Orbital Construction Site: Kerbosch Point',
        'StationServices': ['dock', 'autodock', 'commodities', 'contacts', 'rearm', 'refuel', 'repair',
                            'flightcontroller', 'stationoperations', 'stationMenu', 'colonisationcontribution'],
        'StationType': 'SpaceConstructionDepot',
        'SystemAddress': 83651334874,
        'SystemAllegiance': 'Independent',
        'SystemEconomy': '$economy_Industrial;',
        'SystemFaction': {'Name': 'Rajukru Blue AdvInt'},
        'SystemGovernment': '$government_Corporate;',
        'SystemSecondEconomy': '$economy_Extraction;',
        'SystemSecurity': '$SYSTEM_SECURITY_low;',
        'Taxi': False,
        'event': 'Location', 'horizons': True, 'odyssey': True, 'timestamp': '2025-05-22T00:53:53Z'}}
    - SAASignalsFound # Hotspots
        'BodyID': 9,
        'BodyName': 'Col 285 Sector XS-E b26-4 1 B Ring',
        'Genuses': [],
        'Signals': [{'Count': 1, 'Type': 'Rhodplumsite'}, {'Count': 1, 'Type': 'Monazite'}],
        'StarPos': [-161.0, -54.875, 200.15625],
        'StarSystem': 'Col 285 Sector XS-E b26-4',
        'SystemAddress': 9464899839481,
        'event': 'SAASignalsFound', 'horizons': True, 'odyssey': True, 'timestamp': '2025-05-22T00:54:04Z'}}

        Message(
            timestamp=datetime.datetime(2025, 6, 16, 2, 8, 5, tzinfo=TzInfo(UTC)),
            event=<Event.SAASignalsFound: 'SAASignalsFound'>, horizons=True, odyssey=True,
            StarSystem='Blo Eurl VX-T d3-19', StarPos=[3764.4375, 400.1875, 4446.625], SystemAddress=664101014307,
            Factions=None, BodyID=10, BodyName='Blo Eurl VX-T d3-19 B 2',
            Genuses=[
                {'Genus': '$Codex_Ent_Aleoids_Genus_Name;'},
                {'Genus': '$Codex_Ent_Bacterial_Genus_Name;'},
                {'Genus': '$Codex_Ent_Stratum_Genus_Name;'},
                {'Genus': '$Codex_Ent_Shrubs_Genus_Name;'},
                {'Genus': '$Codex_Ent_Tussocks_Genus_Name;'}
            ], Signals=[{'Count': 5, 'Type': '$SAA_SignalType_Biological;'}]))
    - CarrierJump
        'Body': 'Pipe (stem) Sector JH-V b2-5 3',
        'BodyID': 11,
        'BodyType': 'Planet',
        'Docked': True,
        'MarketID': 3708895232,
        'Population': 0,
        'StarPos': [-44.25, 13.875, 456.03125],
        'StarSystem': 'Pipe (stem) Sector JH-V b2-5',
        'StationEconomies': [{'Name': '$economy_Carrier;', 'Proportion': 1.0}],
        'StationEconomy': '$economy_Carrier;',
        'StationFaction': {'Name': 'FleetCarrier'},
        'StationGovernment': '$government_Carrier;',
        'StationName': 'T9Z-22F',
        'StationServices': ['dock', 'autodock', 'commodities', 'contacts', 'exploration', 'crewlounge', 'rearm',
                            'refuel', 'repair', 'engineer', 'flightcontroller', 'stationoperations', 'stationMenu',
                            'carriermanagement', 'carrierfuel', 'voucherredemption', 'socialspace', 'bartender',
                            'vistagenomics', 'pioneersupplies'],
        'StationType': 'FleetCarrier',
        'SystemAddress': 11665533904481,
        'SystemAllegiance': '',
        'SystemEconomy': '$economy_None;',
        'SystemFaction': {'Name': 'Brewer Corporation'},
        'SystemGovernment': '$government_None;',
        'SystemSecondEconomy': '$economy_None;',
        'SystemSecurity': '$GAlAXY_MAP_INFO_state_anarchy;',
        'event': 'CarrierJump', 'horizons': True, 'odyssey': True, 'timestamp': '2025-05-22T00:52:11Z'}}
    - CodexEntry
"""
