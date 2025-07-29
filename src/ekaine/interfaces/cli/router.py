import asyncio
import logging
from argparse import ArgumentParser, Namespace
from pprint import pformat
from typing import Any

from tabulate import tabulate

from ekaine.common.logging import configure_logger, get_logger
from ekaine.common.timer import Timer
from ekaine.common.utils import get_time_since
from ekaine.ingestion.eddn.listener import main as invoke_eddn_listener
from ekaine.ingestion.spansh.pipeline import SpanshDataPipeline
from ekaine.postgresql.adapter import (
    ApiCommandAdapter,
    SystemsAdapter,
)
from ekaine.postgresql.types import HotspotResult

logger = get_logger(__name__)


def verbose_count_to_log_level(count: int) -> int:
    match count:
        case 0:
            return logging.INFO
        case 1:
            return logging.DEBUG
        case _:
            return logging.TRACE  # type: ignore # dynamically added


def print_hotspot_results(system_name: str, hotspots: list[HotspotResult]) -> None:
    logger.info("")
    logger.info("====== SYSTEM ======")
    logger.info(f"Name: {system_name}\n")
    if not hotspots:
        print("!! Found NO hotspots in this system!")
        return

    headers = ["Ring", "Ring Type", "Commodity", "Count"]
    table = [[h.ring_name, h.ring_type, h.commodity_sym, h.hotspot_count] for h in hotspots]
    logger.info(tabulate(table, headers))


# Data Ingestion CLI


def run_eddn_listener(args: Namespace) -> None:
    invoke_eddn_listener()


def run_import_spansh(args: Namespace) -> None:
    async def run() -> None:
        pipeline = SpanshDataPipeline(
            start_at_system_idx=args.system_start_idx,
            skipping_past_every=args.skipping_past_every,
            validated_every=args.validated_every,
            process_every=args.process_every,
            max_market_data_age_days=args.max_market_data_age_days,
        )
        await pipeline.run()

    asyncio.run(run())


def run_download_spansh(args: Namespace) -> None:
    SpanshDataPipeline.download_data()


# System CLI


def run_get_world(args: Namespace) -> None:
    with SystemsAdapter() as adapter:
        system = adapter.get_system(args.name)
        print(pformat(system))


# API CLI


def run_get_acquirable_systems_in_range(args: Namespace) -> None:
    timer = Timer("Get Acquirable Systems In Range")
    with ApiCommandAdapter() as adapter:
        systems = adapter.get_acquirable_systems_from_origin(args.system_name)

    logger.info("")
    logger.info("====== CURRENT SYSTEM (ACQUIRING) ======")
    logger.info(f"Name: {args.system_name}\n")

    logger.info("====== ACQUIRABLE SYSTEMS (UNOCCUPIED) ======")
    headers = ["System Name", "Population", "Primary Economy", "Power Conflict Progress"]
    table = [
        [
            s.name,
            f"{s.population:3,}",
            s.primary_economy,
            s.power_conflict_progress_str,
        ]
        for s in systems
    ]
    logger.info(tabulate(table, headers))
    logger.info("")

    timer.end()


def run_get_expandable_systems_in_range(args: Namespace) -> None:
    timer = Timer("Get Expandable Systems In Range")
    with ApiCommandAdapter() as adapter:
        systems = adapter.get_expandable_systems_in_range(args.system_name)

    logger.info("")
    logger.info("====== CURRENT UNOCCUPIED SYSTEM ======")
    logger.info(f"Name: {args.system_name}\n")

    logger.info("====== SYSTEMS THAT CAN EXPAND INTO CURRENT ======")
    headers = ["System Name", "Power State", "Population", "Primary Economy"]
    table = [
        [
            s.name,
            s.power_state,
            f"{s.population:3,}",
            s.primary_economy,
        ]
        for s in systems
    ]
    logger.info(tabulate(table, headers))
    logger.info("")

    timer.end()


def run_get_hotspots_by_commodities(args: Namespace) -> None:
    timer = Timer("Get Hotspots In System By Commodities")
    with ApiCommandAdapter() as adapter:
        hotspots = adapter.get_hotspots_in_system_by_commodities(args.system_name, args.commodities_filter)
    print_hotspot_results(args.system_name, hotspots)
    timer.end()


def run_get_hotspots(args: Namespace) -> None:
    timer = Timer("Get Hotspots In System")
    with ApiCommandAdapter() as adapter:
        hotspots = adapter.get_hotspots_in_system(args.system_name)
        print_hotspot_results(args.system_name, hotspots)
        timer.end()


def run_get_mining_expandable_systems_in_range(args: Namespace) -> None:
    timer = Timer("Get Mining Expandable Systems In Range")
    with ApiCommandAdapter() as adapter:
        routes = adapter.get_mining_expandable_systems_in_range(args.system_name)

    logger.info("")
    logger.info("====== DETAILS ======")
    logger.info(f"Target Unoccupied System: {args.system_name}\n")

    logger.info("====== MINING ACQUISITION ROUTES ======")
    headers = ["Mine", "In", "Sell In", "At", "For", "Demand"]
    table = [
        [r.commodity_sym, r.ring_name, r.unoccupied_system, r.station_name, r.sell_price, r.demand] for r in routes
    ]
    logger.info(tabulate(table, headers))

    timer.end()


def run_get_systems_with_power(args: Namespace) -> None:
    timer = Timer("Get Systems With Power")
    with ApiCommandAdapter() as adapter:
        systems = adapter.get_systems_with_power(args.power_name, args.power_states)

    logger.info("")
    logger.info("====== DETAILS ======")
    logger.info(f"Power: {args.power_name}\n")
    if args.power_states:
        logger.info(f"Systems States: {pformat(args.power_states)}\n")

    logger.info(f"====== SYSTEMS INFLUENCED BY {args.power_name} ======")
    headers = ["System Name", "Power State", "Population", "Primary Economy"]
    table = [
        [
            s.name,
            s.power_state,
            f"{s.population:3,}",
            s.primary_economy,
        ]
        for s in systems
    ]
    logger.info(tabulate(table, headers))

    timer.end()


def run_get_top_commodities(args: Namespace) -> None:
    timer = Timer("Get Top Commodities In System")

    with ApiCommandAdapter() as adapter:
        commodities = adapter.get_top_commodities_in_system(
            args.system_name, args.comms_per_station, args.min_supplydemand, args.is_buying
        )

    logger.info("")
    logger.info("====== SYSTEM ======")
    logger.info(f"Name: {args.system_name}\n")
    if not commodities:
        logger.info("!! Found NO stations with known markets!")

    headers = ["Station Name", "Distance", "Commodity", "Sell Price", "Demand", "Buy Price", "Supply", "Updated Last"]
    table = [
        [
            c.station_name,
            f"{c.distance_to_arrival:.2f} LS",
            c.commodity_sym,
            f"{c.sell_price} CR",
            c.demand,
            f"{c.buy_price} CR",
            c.supply,
            get_time_since(c.updated_at) if c.updated_at else "Unknown",
        ]
        for c in commodities
    ]
    logger.info(tabulate(table, headers))
    logger.info("")
    timer.end()


# Argparse


def configure_ingestion_parser(subparsers: Any) -> None:
    ingestion = subparsers.add_parser("ingestion")
    ingestion_sub = ingestion.add_subparsers(dest="subcommand")

    eddn_listener = ingestion_sub.add_parser("eddn-listener")
    eddn_listener.add_argument("-v", "--verbose", action="count", default=0)
    eddn_listener.set_defaults(func=run_eddn_listener)

    spansh_dl = ingestion_sub.add_parser("download-spansh")
    spansh_dl.add_argument("-v", "--verbose", action="count", default=0)
    spansh_dl.set_defaults(func=run_download_spansh)

    spansh_import = ingestion_sub.add_parser("import-spansh")
    spansh_import.add_argument("-v", "--verbose", action="count", default=0)
    spansh_import.add_argument("-s", "--system-start-idx", type=int, default=0)
    spansh_import.add_argument("-S", "--skipping-past-every", type=int, default=1000)
    spansh_import.add_argument("-V", "--validated-every", type=int, default=500)
    spansh_import.add_argument("-P", "--process-every", type=int, default=1500)
    spansh_import.add_argument("-M", "--max-market-data-age-days", type=int, default=30)
    spansh_import.set_defaults(func=run_import_spansh)


def configure_api_parser(subparsers: Any) -> None:
    api = subparsers.add_parser("api")
    api_sub = api.add_subparsers(dest="subcommand")

    api_acquirable_sys = api_sub.add_parser("get-acquirable-systems")
    api_acquirable_sys.add_argument("system_name")
    api_acquirable_sys.add_argument("-v", "--verbose", action="count", default=0)
    api_acquirable_sys.set_defaults(func=run_get_acquirable_systems_in_range)

    api_expandable_sys = api_sub.add_parser("get-expandable-systems")
    api_expandable_sys.add_argument("system_name")
    api_expandable_sys.add_argument("-v", "--verbose", action="count", default=0)
    api_expandable_sys.set_defaults(func=run_get_expandable_systems_in_range)

    api_hotspots = api_sub.add_parser("get-hotspots")
    api_hotspots.add_argument("system_name")
    api_hotspots.add_argument("-v", "--verbose", action="count", default=0)
    api_hotspots.set_defaults(func=run_get_hotspots)

    api_hotspots_by_comm = api_sub.add_parser("get-hotspots-by")
    api_hotspots_by_comm.add_argument("system_name")
    api_hotspots_by_comm.add_argument("commodities_filter", nargs="+")
    api_hotspots_by_comm.add_argument("-v", "--verbose", action="count", default=0)
    api_hotspots_by_comm.set_defaults(func=run_get_hotspots_by_commodities)

    api_mining_expansion = api_sub.add_parser("get-mining-expandable")
    api_mining_expansion.add_argument("system_name")
    api_mining_expansion.add_argument("-v", "--verbose", action="count", default=0)
    api_mining_expansion.set_defaults(func=run_get_mining_expandable_systems_in_range)

    api_hotspots = api_sub.add_parser("get-systems-with-power")
    api_hotspots.add_argument("power_name")
    api_hotspots.add_argument("power_states", nargs="*")
    api_hotspots.add_argument("-v", "--verbose", action="count", default=0)
    api_hotspots.set_defaults(func=run_get_systems_with_power)

    api_top_commodities = api_sub.add_parser("get-top-commodities")
    api_top_commodities.add_argument("system_name")
    api_top_commodities.add_argument("--comms-per-station", type=int, default=5)
    api_top_commodities.add_argument("--min-supplydemand", type=int, default=1)
    api_top_commodities.add_argument("--is-buying", action="store_true", default=False)
    api_top_commodities.add_argument("-v", "--verbose", action="count", default=0)
    api_top_commodities.set_defaults(func=run_get_top_commodities)


def cli() -> None:
    parser = ArgumentParser(description="Elite Dangerous CLI Tool")
    subparsers = parser.add_subparsers(dest="command")

    configure_ingestion_parser(subparsers)
    configure_api_parser(subparsers)

    args = parser.parse_args()
    if hasattr(args, "func"):
        configure_logger(verbose_count_to_log_level(args.verbose))
        args.func(args)
    else:
        parser.print_help()
