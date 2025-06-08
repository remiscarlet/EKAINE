from datetime import datetime
from pprint import pformat
from typing import Any, Optional, cast

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    PrimaryKeyConstraint,
    SmallInteger,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TEXT
from sqlalchemy.orm import Mapped, mapped_column

from ekaine.common.game_constants import get_symbol_by_eddn_name
from ekaine.common.logging import get_logger
from ekaine.postgresql import BaseModel
from ekaine.postgresql.db import FactionPresencesDB
from gen.eddn_models import commodity_v3_0, fsssignaldiscovered_v1_0, journal_v1_0

logger = get_logger(__name__)

#
# Signals Timeseries
#


class SignalsTimeseriesMixin:
    id: Mapped[int] = mapped_column(Integer, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)

    system_id: Mapped[int] = mapped_column(Integer, nullable=False)

    signal_type: Mapped[Optional[str]] = mapped_column(TEXT)
    signal_name: Mapped[Optional[str]] = mapped_column(TEXT)

    is_station: Mapped[Optional[bool]] = mapped_column(Boolean)
    uss_type: Mapped[Optional[str]] = mapped_column(TEXT)

    spawning_state: Mapped[Optional[str]] = mapped_column(TEXT)
    spawning_faction: Mapped[Optional[str]] = mapped_column(TEXT)
    spawning_power: Mapped[Optional[str]] = mapped_column(TEXT)
    opposing_power: Mapped[Optional[str]] = mapped_column(TEXT)

    threat_level: Mapped[Optional[int]] = mapped_column(SmallInteger)

    fields = [
        "id",
        "signal_type",
        "signal_name",
        "is_station",
        "uss_type",
        "spawning_state",
        "spawning_faction",
        "spawning_power",
        "opposing_power",
        "threat_level",
    ]

    def __repr__(self) -> str:
        non_none_fields = []
        for field in self.fields:
            val = getattr(self, field)
            if val is not None:
                if isinstance(val, str):
                    val = f'"{val}"'
                non_none_fields.append(f"{field}={val}")

        return f"<{type(self).__name__}({', '.join(non_none_fields)})>"


class RawSignalsTimeseries(BaseModel, SignalsTimeseriesMixin):
    unique_columns = ("id", "timestamp")
    __tablename__ = "signals"
    __table_args__ = (
        PrimaryKeyConstraint("id", "timestamp"),
        {"schema": "raw_timescaledb"},
    )

    @staticmethod
    def to_dicts_from_fsssignaldiscovered_v1_0(
        model: fsssignaldiscovered_v1_0.Model, system_id: int
    ) -> list[dict[str, Any]]:
        dicts = []
        for signal in model.message.signals:
            if "Warzone_PointRace" in signal.SignalName or "Warzone_Powerplay" in signal.SignalName:
                # Ignore for now - spammy
                continue
            signal_name = get_symbol_by_eddn_name(signal.SignalName) or signal.SignalName
            if len(signal_name) and signal_name[0] == "$":
                logger.warning(
                    "Encountered dollarstring SignalName we didn't know about! "
                    f"Skipping signal... '{signal.SignalName}'"
                )
                continue

            uss_type = None
            if signal.USSType is not None:
                uss_type = get_symbol_by_eddn_name(signal.USSType) or signal.USSType

            if uss_type is not None and len(uss_type) and uss_type[0] == "$":
                logger.warning(
                    "Encountered dollarstring USSType we didn't know about! " f"Skipping signal... '{signal.USSType}'"
                )
                continue

            spawning_state = None
            if signal.SpawningState is not None:
                spawning_state = get_symbol_by_eddn_name(signal.SpawningState) or signal.SpawningState
            if spawning_state is not None and len(spawning_state) and spawning_state[0] == "$":
                logger.warning(
                    "Encountered dollarstring SpawningState we didn't know about! "
                    f"Skipping signal... '{signal.SpawningState}'"
                )
                continue

            dicts.append(
                {
                    "system_id": system_id,
                    "timestamp": signal.timestamp,
                    "signal_type": signal.SignalType,
                    "signal_name": signal_name,
                    "is_station": signal.IsStation,
                    "uss_type": uss_type,
                    "spawning_state": spawning_state,
                    "spawning_faction": signal.SpawningFaction,
                    "spawning_power": signal.SpawningPower,
                    "opposing_power": signal.OpposingPower,
                    "threat_level": signal.ThreatLevel,
                }
            )
        return dicts


class ProcessedSignalsTimeseries(BaseModel, SignalsTimeseriesMixin):
    # This models the EDDN fsssignaldiscovered-v1.0's Signals object shape
    #   (gen.eddn_models.fsssignaldiscovered_v1_0.Signal)
    # Note: EDDN mandates the 'time_remaining' field MUST NOT be present (Can be PII)
    unique_columns = ("id", "timestamp")
    __tablename__ = "signals"
    __table_args__ = (
        PrimaryKeyConstraint("id", "timestamp"),
        {"schema": "timescaledb"},
    )


# Faction Presences Timeseries


class FactionPresencesTimeseriesMixin:
    id: Mapped[int] = mapped_column(Integer, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)

    system_id: Mapped[int] = mapped_column(Integer, nullable=False)
    faction_id: Mapped[int] = mapped_column(Integer, nullable=False)

    influence: Mapped[float] = mapped_column(Float)
    state: Mapped[str] = mapped_column(Text)
    happiness: Mapped[str] = mapped_column(Text)

    active_states: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))
    pending_states: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))
    recovering_states: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))

    updated_at: Mapped[datetime] = mapped_column(DateTime)
    is_backfilled: Mapped[bool] = mapped_column(Boolean)

    def __repr__(self) -> str:
        return f"<{type(self).__name__}(id={self.id}, system_id={self.system_id}, faction_id={self.faction_id})>"


class RawFactionPresencesTimeseries(BaseModel, FactionPresencesTimeseriesMixin):
    # This models timeseries-interesting fields from the core.faction_presences table
    unique_columns = ("id", "timestamp")
    __tablename__ = "faction_presences"
    __table_args__ = (
        PrimaryKeyConstraint("id", "timestamp"),
        Index("ix_raw_tsdb_faction_presences_s_f_id_ts", "system_id", "faction_id", "timestamp"),
        {"schema": "raw_timescaledb"},
    )

    @staticmethod
    def to_dicts_from_eddn(
        eddn_model: journal_v1_0.Model, system_id: int, faction_name_to_id_mapping: dict[str, int]
    ) -> list[dict[str, Any]]:
        msg = eddn_model.message
        dicts = []
        for faction in msg.Factions or []:
            if faction.Name is None:
                logger.warning(f"Found a Faction without a Name! {pformat(faction)}")
                continue

            faction_id = faction_name_to_id_mapping.get(faction.Name)
            if faction_id is None:
                logger.warning(
                    "Found a Faction Name that wasn't in the provided id mapping: "
                    f"'{faction.Name}' - {pformat(faction_name_to_id_mapping)}"
                )
                continue
            d = {
                "timestamp": msg.timestamp,
                "system_id": system_id,
                "faction_id": faction_id,
                "influence": faction.Influence,
                "state": get_symbol_by_eddn_name(faction.FactionState) if faction.FactionState is not None else None,
                "happiness": get_symbol_by_eddn_name(faction.Happiness) if faction.Happiness is not None else None,
                "active_states": [get_symbol_by_eddn_name(state.State) for state in faction.ActiveStates or []],
                "pending_states": [get_symbol_by_eddn_name(state.State) for state in faction.PendingStates or []],
                "recovering_states": [get_symbol_by_eddn_name(state.State) for state in faction.RecoveringStates or []],
                "updated_at": msg.timestamp,
                "is_backfilled": False,
            }

            dicts.append(d)

        return dicts


class ProcessedFactionPresencesTimeseries(BaseModel, FactionPresencesTimeseriesMixin):
    # This models timeseries-interesting fields from the core.faction_presences table
    unique_columns = ("id", "timestamp")
    __tablename__ = "faction_presences"
    __table_args__ = (
        PrimaryKeyConstraint("id", "timestamp"),
        UniqueConstraint("system_id", "faction_id", "timestamp", name="_tsdb_faction_presences_s_f_id_ts_uc"),
        {"schema": "timescaledb"},
    )


# Power Conflict Progress Timeseries


class PowerConflictProgressTimeseriesMixin:
    id: Mapped[int] = mapped_column(Integer, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)

    system_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    power_name: Mapped[str] = mapped_column(Text, nullable=False, index=True)

    progress: Mapped[float] = mapped_column(Float, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_backfilled: Mapped[bool] = mapped_column(Boolean, nullable=False)

    def __repr__(self) -> str:
        return f"<{type(self).__name__}(id={self.id}, power={self.power_name}, system_id={self.system_id})>"


class RawPowerConflictProgressTimeseries(BaseModel, PowerConflictProgressTimeseriesMixin):
    # This models the core.systems table's power_conflict_progress as its own hypertable for querying ergonomics
    unique_columns = ("id", "timestamp")
    __tablename__ = "power_conflict_progress"
    __table_args__ = (
        PrimaryKeyConstraint("id", "timestamp"),
        Index("ix_raw_tsdb_power_conflict_progress_s_id_p_name_ts", "system_id", "power_name", "timestamp"),
        {"schema": "raw_timescaledb"},
    )

    @staticmethod
    def to_dicts_from_eddn(eddn_model: journal_v1_0.Model, system_id: int) -> list[dict[str, Any]]:
        msg = eddn_model.message
        dicts = []

        for conflict in getattr(msg, "PowerplayConflictProgress", []):
            # 'PowerplayConflictProgress': [{'ConflictProgress': 0.0, 'Power': 'Felicia Winters'}],

            power_name = conflict.get("Power", None)
            if power_name is None:
                logger.warning(
                    "Encountered PowerplayConflictProgress object with no Power field! "
                    f"'{pformat(conflict)}' (type: {type(conflict)})"
                )
                continue

            progress = conflict.get("ConflictProgress", None)
            if progress is None:
                logger.warning(
                    "Encountered PowerplayConflictProgress object with no ConflictProgress field! "
                    f"'{pformat(conflict)}' (type: {type(conflict)})"
                )
                continue

            dicts.append(
                {
                    "timestamp": msg.timestamp,
                    "system_id": system_id,
                    "power_name": power_name,
                    "progress": progress,
                    "updated_at": msg.timestamp,
                    "is_backfilled": False,
                }
            )

        return dicts


class ProcessedPowerConflictProgressTimeseries(BaseModel, PowerConflictProgressTimeseriesMixin):
    # This models the core.systems table's power_conflict_progress as its own hypertable for querying ergonomics
    unique_columns = ("id", "timestamp")
    __tablename__ = "power_conflict_progress"
    __table_args__ = (
        PrimaryKeyConstraint("id", "timestamp"),
        UniqueConstraint(
            "system_id", "power_name", "timestamp", name="_tsdb_power_conflict_progress_s_id_p_name_ts_uc"
        ),
        {"schema": "timescaledb"},
    )


# Systems Timeseries


class SystemsTimeseriesMixin:
    id: Mapped[int] = mapped_column(Integer, autoincrement=True)
    system_id: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)

    allegiance: Mapped[Optional[str]] = mapped_column(Text)
    population: Mapped[Optional[int]] = mapped_column(BigInteger)
    primary_economy: Mapped[Optional[str]] = mapped_column(Text)
    secondary_economy: Mapped[Optional[str]] = mapped_column(Text)
    security: Mapped[Optional[str]] = mapped_column(Text)
    government: Mapped[Optional[str]] = mapped_column(Text)

    controlling_faction_id: Mapped[Optional[int]] = mapped_column(Integer)

    controlling_power: Mapped[Optional[str]] = mapped_column(Text)
    power_conflict_progress: Mapped[Optional[list[dict[str, float]]]] = mapped_column(JSONB)
    power_state: Mapped[Optional[str]] = mapped_column(Text)
    power_state_control_progress: Mapped[Optional[float]] = mapped_column(Float)
    power_state_reinforcement: Mapped[Optional[float]] = mapped_column(Float)
    power_state_undermining: Mapped[Optional[float]] = mapped_column(Float)
    powers: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))

    updated_at: Mapped[datetime] = mapped_column(DateTime)
    is_backfilled: Mapped[bool] = mapped_column(Boolean)

    def __repr__(self) -> str:
        return f"<{type(self).__name__}(id={self.id}, name={self.name})>"


class RawSystemsTimeseries(BaseModel, SystemsTimeseriesMixin):
    # This models timeseries-interesting fields from the core.systems table
    unique_columns = ("id", "timestamp")
    __tablename__ = "systems"
    __table_args__ = (
        PrimaryKeyConstraint("id", "timestamp"),
        {"schema": "raw_timescaledb"},
    )

    @staticmethod
    def to_dict_from_eddn(
        eddn_model: journal_v1_0.Model, system_id: int, controlling_faction_id: int | None
    ) -> dict[str, Any]:
        msg = eddn_model.message
        government = getattr(msg, "SystemGovernment", None)
        primary_economy = getattr(msg, "SystemEconomy", None)
        secondary_economy = getattr(msg, "SystemSecondEconomy", None)
        security = getattr(msg, "SystemSecurity", None)

        d = {
            "system_id": system_id,
            "timestamp": msg.timestamp,
            "allegiance": getattr(msg, "SystemAllegiance", None),
            "controlling_faction_id": controlling_faction_id,
            "government": get_symbol_by_eddn_name(cast(str, government)) if government is not None else None,
            "name": msg.StarSystem,
            "population": getattr(msg, "Population", None),
            "primary_economy": (
                get_symbol_by_eddn_name(cast(str, primary_economy)) if primary_economy is not None else None
            ),
            "secondary_economy": (
                get_symbol_by_eddn_name(cast(str, secondary_economy)) if secondary_economy is not None else None
            ),
            "security": get_symbol_by_eddn_name(cast(str, security)) if security is not None else None,
            "controlling_power": getattr(msg, "ControllingPower", None),
            # "power_conflict_progress": [] # Split out into PowerConflictProgressTimeseries
            "power_state": getattr(msg, "PowerplayState", None),
            "power_state_control_progress": getattr(msg, "PowerplayStateControlProgress", None),
            "power_state_reinforcement": getattr(msg, "PowerplayStateReinforcement", None),
            "power_state_undermining": getattr(msg, "PowerplayStateUndermining", None),
            "powers": getattr(msg, "Powers", None),
            "updated_at": msg.timestamp,
            "is_backfilled": False,
        }

        return {k: v for k, v in d.items() if v is not None}


class ProcessedSystemsTimeseries(BaseModel, SystemsTimeseriesMixin):
    # This models timeseries-interesting fields from the core.systems table
    unique_columns = ("id", "timestamp")
    __tablename__ = "systems"
    __table_args__ = (
        PrimaryKeyConstraint("id", "timestamp"),
        {"schema": "timescaledb"},
    )


# Systems Timeseries


class MarketCommodityFactionStateTimeseriesMixin:
    id: Mapped[int] = mapped_column(Integer, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)

    system_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    system_controlling_faction_id: Mapped[int] = mapped_column("sy_cf_id", Integer, nullable=False, index=True)
    system_controlling_faction_state: Mapped[str] = mapped_column("sy_cf_state", Text, nullable=False, index=True)
    system_controlling_faction_active_states: Mapped[Optional[str]] = mapped_column(
        "sy_cf_active_states", ARRAY(Text), nullable=True
    )

    station_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    station_controlling_faction_id: Mapped[int] = mapped_column("st_cf_id", Integer, nullable=False, index=True)
    station_controlling_faction_state: Mapped[str] = mapped_column("st_cf_state", Text, nullable=False, index=True)
    station_controlling_faction_active_states: Mapped[Optional[str]] = mapped_column(
        "st_cf_active_states", ARRAY(Text), nullable=True
    )

    commodity_sym: Mapped[str] = mapped_column(Text, nullable=False, index=True)

    # Multiplifer versus galactic average
    sell_price_multiplier: Mapped[str] = mapped_column(Float, nullable=False)
    buy_price_multiplier: Mapped[str] = mapped_column(Float, nullable=False)


class RawMarketCommodityFactionStateTimeseries(BaseModel, MarketCommodityFactionStateTimeseriesMixin):
    # This models timeseries information about market commodity prices,
    # their relative price to galactic average, and the state of the station's controlling faction
    # This hopes to gather empiral data on the effects of Faction states, particularly the combination of multiple
    # active states, to commodity prices.

    unique_columns = ("id", "timestamp")
    __tablename__ = "market_commodity_faction_state"
    __table_args__ = (
        PrimaryKeyConstraint("id", "timestamp"),
        {"schema": "raw_timescaledb"},
    )

    @staticmethod
    def to_dicts_from_eddn(
        eddn_model: commodity_v3_0.Model,
        system_id: int,
        station_id: int,
        system_controlling_faction: FactionPresencesDB,
        station_controlling_faction: FactionPresencesDB,
    ) -> list[dict[str, Any]]:
        dicts = []
        for commodity in eddn_model.message.commodities:
            commodity_sym = get_symbol_by_eddn_name(commodity.name)
            if commodity_sym is None:
                logger.warning(
                    f"Encountered a commodity in an EDDN Commodity model we didn't know about! Got: '{commodity.name}'"
                )
                continue

            buy_price_multiplier = commodity.buyPrice / commodity.meanPrice if commodity.meanPrice else -1
            sell_price_multiplier = commodity.sellPrice / commodity.meanPrice if commodity.meanPrice else -1

            dicts.append(
                {
                    "timestamp": eddn_model.message.timestamp,
                    "system_id": system_id,
                    "system_controlling_faction_id": system_controlling_faction.id,
                    "system_controlling_faction_state": system_controlling_faction.state,
                    "system_controlling_faction_active_states": system_controlling_faction.active_states,
                    "station_id": station_id,
                    "station_controlling_faction_id": station_controlling_faction.id,
                    "station_controlling_faction_state": station_controlling_faction.state,
                    "station_controlling_faction_active_states": station_controlling_faction.active_states,
                    "commodity_sym": commodity_sym,
                    "buy_price_multiplier": buy_price_multiplier,
                    "sell_price_multiplier": sell_price_multiplier,
                }
            )
        return dicts


class ProcessedMarketCommodityFactionStateTimeseries(BaseModel, MarketCommodityFactionStateTimeseriesMixin):
    # This models timeseries information about market commodity prices,
    # their relative price to galactic average, and the state of the station's controlling faction
    # This hopes to gather empiral data on the effects of Faction states, particularly the combination of multiple
    # active states, to commodity prices.

    unique_columns = ("id", "timestamp")
    __tablename__ = "market_commodity_faction_state"
    __table_args__ = (
        PrimaryKeyConstraint("id", "timestamp"),
        {"schema": "timescaledb"},
    )
