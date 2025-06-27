import re
import typing
from datetime import datetime
from pprint import pformat
from typing import Any, Callable, Optional, Tuple, Union, cast

from geoalchemy2 import Geometry, WKBElement
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Computed,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    SmallInteger,
    Text,
    UniqueConstraint,
    and_,
    literal,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    Mapped,
    Session,
    declared_attr,
    foreign,
    mapped_column,
    relationship,
)

from ekaine.common.game_constants import get_symbol_by_eddn_name
from ekaine.common.logging import get_logger
from ekaine.ingestion.spansh.models.body_spansh import (
    AsteroidsSpansh,
    BodySpansh,
    SignalsSpansh,
)
from ekaine.ingestion.spansh.models.common_spansh import CoordinatesSpansh
from ekaine.ingestion.spansh.models.station_spansh import CommoditySpansh, StationSpansh
from ekaine.ingestion.spansh.models.system_spansh import (
    ControllingFactionSpansh,
    FactionSpansh,
    PowerConflictProgressSpansh,
    SystemSpansh,
    ThargoidWarSpansh,
)
from ekaine.postgresql import BaseModel, BaseModelWithId
from ekaine.postgresql.types import ResolvedStationResult
from gen.eddn_models import commodity_v3_0, journal_v1_0

logger = get_logger(__name__)

"""
Ideally we can split these models out into their own files but doing so
introduces circular dependencies on the imports because we each model name in the Mapped[T] typing
(as well as occasionally in the join conditions)
"""


class BodiesDB(BaseModelWithId):
    unique_columns = ("system_id", "name", "body_id")
    __tablename__ = "bodies"
    __table_args__ = (
        UniqueConstraint(*unique_columns, name="_bodies_uc"),
        {"schema": "core"},
    )

    name: Mapped[str] = mapped_column(Text, nullable=False, index=True)

    id64: Mapped[Optional[int]] = mapped_column(BigInteger)
    id_spansh: Mapped[Optional[int]] = mapped_column(BigInteger)
    id_edsm: Mapped[Optional[int]] = mapped_column(BigInteger)

    body_id: Mapped[Optional[int]] = mapped_column(Integer)  # The "idx" of the body _within the system_

    system_id: Mapped[int] = mapped_column(ForeignKey("core.systems.id"), nullable=False, index=True)
    system: Mapped["SystemsDB"] = relationship(back_populates="bodies")

    stations: Mapped[list["StationsDB"]] = relationship(
        "StationsDB",
        primaryjoin=lambda: and_(foreign(StationsDB.owner_id) == BodiesDB.id, StationsDB.owner_type == literal("body")),
        overlaps="stations",
    )

    atmosphere_composition: Mapped[Optional[dict[str, float]]] = mapped_column(JSONB)
    materials: Mapped[Optional[dict[str, float]]] = mapped_column(JSONB)
    parents: Mapped[Optional[dict[str, int]]] = mapped_column(JSONB)

    absolute_magnitude: Mapped[Optional[float]] = mapped_column(Float)
    age: Mapped[Optional[int]] = mapped_column(Integer)
    arg_of_periapsis: Mapped[Optional[float]] = mapped_column(Float)
    ascending_node: Mapped[Optional[float]] = mapped_column(Float)
    atmosphere_type: Mapped[Optional[str]] = mapped_column(Text)
    axial_tilt: Mapped[Optional[float]] = mapped_column(Float)
    distance_to_arrival: Mapped[Optional[float]] = mapped_column(Float)
    earth_masses: Mapped[Optional[float]] = mapped_column(Float)
    gravity: Mapped[Optional[float]] = mapped_column(Float)
    is_landable: Mapped[Optional[bool]] = mapped_column(Boolean)
    luminosity: Mapped[Optional[str]] = mapped_column(Text)
    main_star: Mapped[Optional[bool]] = mapped_column(Boolean)
    mean_anomaly: Mapped[Optional[float]] = mapped_column(Float)
    orbital_eccentricity: Mapped[Optional[float]] = mapped_column(Float)
    orbital_inclination: Mapped[Optional[float]] = mapped_column(Float)
    orbital_period: Mapped[Optional[float]] = mapped_column(Float)
    radius: Mapped[Optional[float]] = mapped_column(Float)
    reserve_level: Mapped[Optional[str]] = mapped_column(Text)
    rotational_period: Mapped[Optional[float]] = mapped_column(Float)
    rotational_period_tidally_locked: Mapped[Optional[bool]] = mapped_column(Boolean)
    semi_major_axis: Mapped[Optional[float]] = mapped_column(Float)
    solar_masses: Mapped[Optional[float]] = mapped_column(Float)
    solar_radius: Mapped[Optional[float]] = mapped_column(Float)
    solid_composition: Mapped[Optional[dict[str, float]]] = mapped_column(JSONB)
    spectral_class: Mapped[Optional[str]] = mapped_column(Text)
    sub_type: Mapped[Optional[str]] = mapped_column(Text)
    surface_pressure: Mapped[Optional[float]] = mapped_column(Float)
    surface_temperature: Mapped[Optional[float]] = mapped_column(Float)
    terraforming_state: Mapped[Optional[str]] = mapped_column(Text)
    type: Mapped[Optional[str]] = mapped_column(Text)
    volcanism_type: Mapped[Optional[str]] = mapped_column(Text)

    mean_anomaly_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    distance_to_arrival_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    rings: Mapped[list["RingsDB"]] = relationship(back_populates="body")
    signals: Mapped[list["SignalsDB"]] = relationship(back_populates="body")

    def to_cache_key_tuple(self) -> Tuple[Any, ...]:
        return ("BodiesDB", self.system_id, self.name, self.body_id)

    @staticmethod
    def to_dict_from_spansh(spansh_body: BodySpansh, system_id: int) -> dict[str, Any]:
        return {
            "system_id": system_id,
            "id64": spansh_body.id64,
            "body_id": spansh_body.body_id,
            "name": spansh_body.name,
            "absolute_magnitude": spansh_body.absolute_magnitude,
            "age": spansh_body.age,
            "arg_of_periapsis": spansh_body.arg_of_periapsis,
            "ascending_node": spansh_body.ascending_node,
            "atmosphere_composition": spansh_body.atmosphere_composition,
            "atmosphere_type": spansh_body.atmosphere_type,
            "axial_tilt": spansh_body.axial_tilt,
            "distance_to_arrival": spansh_body.distance_to_arrival,
            "earth_masses": spansh_body.earth_masses,
            "gravity": spansh_body.gravity,
            "is_landable": spansh_body.is_landable,
            "luminosity": spansh_body.luminosity,
            "main_star": spansh_body.main_star,
            "materials": spansh_body.materials,
            "mean_anomaly": spansh_body.mean_anomaly,
            "orbital_eccentricity": spansh_body.orbital_eccentricity,
            "orbital_inclination": spansh_body.orbital_inclination,
            "orbital_period": spansh_body.orbital_period,
            "parents": spansh_body.parents,
            "radius": spansh_body.radius,
            "reserve_level": spansh_body.reserve_level,
            "rotational_period": spansh_body.rotational_period,
            "rotational_period_tidally_locked": spansh_body.rotational_period_tidally_locked,
            "semi_major_axis": spansh_body.semi_major_axis,
            "solar_masses": spansh_body.solar_masses,
            "solar_radius": spansh_body.solar_radius,
            "solid_composition": spansh_body.solid_composition,
            "spectral_class": spansh_body.spectral_class,
            "sub_type": spansh_body.sub_type,
            "surface_pressure": spansh_body.surface_pressure,
            "surface_temperature": spansh_body.surface_temperature,
            "terraforming_state": spansh_body.terraforming_state,
            "type": spansh_body.type,
            "volcanism_type": spansh_body.volcanism_type,
            "mean_anomaly_updated_at": getattr(spansh_body.timestamps, "mean_anomaly", None),
            "distance_to_arrival_updated_at": getattr(spansh_body.timestamps, "distance_to_arrival", None),
        }

    @staticmethod
    def to_materials_from_journal_entry(journal_entry: journal_v1_0.Message) -> dict[str, float]:
        materials = {}
        for mat in getattr(journal_entry, "Materials", []):
            name = mat.get("Name")
            if name is None:
                raise ValueError(f"Could not parse material name out of body! '{pformat(mat)}'")
            percent = mat.get("Percent")
            if percent is None:
                raise ValueError(f"Could not parse material percent out of body! '{pformat(mat)}'")
            materials[name] = cast(float, percent)

        return materials

    @staticmethod
    def to_type_from_journal_entry(
        journal_entry: journal_v1_0.Message, body_name: str, luminosity: str | None, sub_type: str | None
    ) -> str | None:
        type = getattr(journal_entry, "BodyType", None)
        if type is None:
            if body_name.endswith("Ring"):
                type = "Ring"
            elif "Belt Cluster" in body_name:
                type = "Belt Cluster"
            elif luminosity is not None:
                type = "Star"
            elif sub_type is not None:
                type = "Planet"
        return type

    @staticmethod
    def to_spectral_class_from_journal_entry(journal_entry: journal_v1_0.Message) -> str | None:
        star_type = getattr(journal_entry, "StarType", None)
        subclass = getattr(journal_entry, "Subclass", None)

        if star_type is None:
            return None
        if subclass is None:
            logger.warning(f"Got a Star body with a star_type but no subclass! '{pformat(journal_entry)}'")
            return None

        return f"{star_type}{subclass}"

    """
    - SAASignalsFound # Hotspots
        'BodyID': 9,
        'BodyName': 'Col 285 Sector XS-E b26-4 1 B Ring',
        'Genuses': [],
        'Signals': [{'Count': 1, 'Type': 'Rhodplumsite'}, {'Count': 1, 'Type': 'Monazite'}],
        'StarPos': [-161.0, -54.875, 200.15625],
        'StarSystem': 'Col 285 Sector XS-E b26-4',
        'SystemAddress': 9464899839481,
        'event': 'SAASignalsFound', 'horizons': True, 'odyssey': True, 'timestamp': '2025-05-22T00:54:04Z'}}
    """

    @staticmethod
    def to_dict_from_eddn(eddn_model: journal_v1_0.Model, system_id: int) -> dict[str, Any] | None:
        journal_entry = eddn_model.message
        body_name = getattr(journal_entry, "Body", None)
        if body_name is None:
            body_name = getattr(journal_entry, "BodyName", None)
        if body_name is None:
            # Journal entry with no body name - no body present.
            return None

        distance_to_arrival: float | None = getattr(journal_entry, "DistanceFromArrivalLS", None)
        is_main_star = (distance_to_arrival == 0) if distance_to_arrival is not None else None
        luminosity = getattr(journal_entry, "Luminosity", None)
        reserve_level = getattr(journal_entry, "ReserveLevel", None)
        radius = getattr(journal_entry, "Radius", None)
        sub_type = getattr(journal_entry, "PlanetClass", None)

        spectral_class = BodiesDB.to_spectral_class_from_journal_entry(journal_entry)
        materials = BodiesDB.to_materials_from_journal_entry(journal_entry)

        type = BodiesDB.to_type_from_journal_entry(journal_entry, body_name, luminosity, sub_type)
        if type == "Ring":
            body_name = RingsDB.ring_to_body_name_re.sub(r"\g<parent_body_name>", body_name)
        elif type is None:
            logger.info(pformat(journal_entry))

        d = {
            "system_id": system_id,
            "body_id": getattr(journal_entry, "BodyID", None),
            "name": body_name,
            "absolute_magnitude": getattr(journal_entry, "AbsoluteMagnitude", None),
            "age": getattr(journal_entry, "Age_MY", None),
            "arg_of_periapsis": getattr(journal_entry, "Periapsis", None),
            "ascending_node": getattr(journal_entry, "AscendingNode", None),
            "atmosphere_composition": getattr(journal_entry, "AtmosphericComposition", None),
            "atmosphere_type": getattr(journal_entry, "AtmosphereType", None),
            "axial_tilt": getattr(journal_entry, "AxialTilt", None),
            "distance_to_arrival": getattr(journal_entry, "DistanceFromArrivalLS", None),
            "earth_masses": getattr(journal_entry, "MassEM", None),
            "gravity": getattr(journal_entry, "SurfaceGravity", None),
            "is_landable": getattr(journal_entry, "Landable", None),
            "luminosity": getattr(journal_entry, "Luminosity", None),
            "main_star": is_main_star,
            "materials": materials if materials else None,
            "mean_anomaly": getattr(journal_entry, "MeanAnomaly", None),
            "orbital_eccentricity": getattr(journal_entry, "Eccentricity", None),
            "orbital_inclination": getattr(journal_entry, "OrbitalInclination", None),
            "orbital_period": getattr(journal_entry, "OrbitalPeriod", None),
            "parents": getattr(journal_entry, "Parents", None),
            "radius": radius if type != "Star" else None,
            "reserve_level": get_symbol_by_eddn_name(reserve_level) if reserve_level is not None else None,
            "rotational_period": getattr(journal_entry, "RotationPeriod", None),
            "rotational_period_tidally_locked": getattr(journal_entry, "TidalLock", None),
            "semi_major_axis": getattr(journal_entry, "SemiMajorAxis", None),
            "solar_masses": getattr(journal_entry, "StellarMass", None),
            "solar_radius": radius if type == "Star" else None,
            "solid_composition": getattr(journal_entry, "Composition", None),
            "spectral_class": spectral_class,
            "sub_type": sub_type,
            "surface_pressure": getattr(journal_entry, "SurfacePressure", None),
            "surface_temperature": getattr(journal_entry, "SurfaceTemperature", None),
            "terraforming_state": getattr(journal_entry, "TerraformState", None),
            "type": type,
            "volcanism_type": getattr(journal_entry, "Volcanism", None),
            "mean_anomaly_updated_at": (
                None if getattr(journal_entry, "MeanAnomaly", None) is None else journal_entry.timestamp
            ),
            "distance_to_arrival_updated_at": (
                None if getattr(journal_entry, "DistanceFromArrivalLS", None) is None else journal_entry.timestamp
            ),
        }

        return {k: v for k, v in d.items() if v is not None}

    def __repr__(self) -> str:
        return f"<BodiesDB(id={self.id}, name={self.name!r})>"


class SignalsDB(BaseModelWithId):
    unique_columns = ("body_id", "signal_type")
    __tablename__ = "signals"
    __table_args__ = (UniqueConstraint(*unique_columns, name="_signal_on_body_uc"), {"schema": "core"})

    body_id: Mapped[int] = mapped_column(ForeignKey("core.bodies.id"), nullable=False, index=True)
    body: Mapped["BodiesDB"] = relationship(back_populates="signals")

    signal_type: Mapped[Optional[str]] = mapped_column(Text)
    count: Mapped[Optional[int]] = mapped_column(Integer)
    updated_at: Mapped[Optional[DateTime]] = mapped_column(DateTime)

    @staticmethod
    def to_dicts_from_spansh(spansh_signal: SignalsSpansh, body_id: int) -> list[dict[str, Any]]:
        return [
            {
                "body_id": body_id,
                "signal_type": signal_type,
                "count": count,
                "updated_at": spansh_signal.updated_at,
            }
            for signal_type, count in spansh_signal.signals.items()
        ]

    def __repr__(self) -> str:
        return f"<SignalsDB(id={self.id}, signal_type={self.signal_type})>"


class RingsDB(BaseModelWithId):
    unique_columns = ("body_id", "name")
    __tablename__ = "rings"
    __table_args__ = (
        UniqueConstraint(*unique_columns, name="_ring_on_body_uc"),
        Index("ix_rings_ring_geom", "ring_geom", postgresql_using="gist"),
        {"schema": "core"},
    )

    id64: Mapped[int] = mapped_column(BigInteger, nullable=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)

    body_id: Mapped[int] = mapped_column(ForeignKey("core.bodies.id"), nullable=False, index=True)
    body: Mapped["BodiesDB"] = relationship(back_populates="rings")

    type: Mapped[Optional[str]] = mapped_column(Text)
    mass: Mapped[Optional[float]] = mapped_column(Float)
    inner_radius: Mapped[Optional[float]] = mapped_column(Float)
    outer_radius: Mapped[Optional[float]] = mapped_column(Float)

    hotspots: Mapped[list["HotspotsDB"]] = relationship(back_populates="ring")

    ring_geom: Mapped[Any] = mapped_column(
        Geometry("POLYGON", srid=0),
        Computed(
            """
            ST_Difference(
                ST_Buffer(ST_MakePoint(0,0), outer_radius),
                ST_Buffer(ST_MakePoint(0,0), inner_radius)
            )
            """,
            persisted=True,
        ),
        nullable=False,
    )

    ring_area: Mapped[float] = mapped_column(
        Float,
        Computed(
            """
            ST_Area(ST_Difference(
                ST_Buffer( ST_MakePoint(0,0), outer_radius ),
                ST_Buffer( ST_MakePoint(0,0), inner_radius )
            ))""",
            persisted=True,
        ),
        nullable=False,
    )

    surface_density: Mapped[float] = mapped_column(
        Float,
        Computed(
            """
            mass / NULLIF(ST_Area(ST_Difference(
                ST_Buffer( ST_MakePoint(0,0), outer_radius ),
                ST_Buffer( ST_MakePoint(0,0), inner_radius )
            )),0)
            """,
            persisted=True,
        ),
        nullable=False,
    )

    def to_cache_key_tuple(self) -> Tuple[Any, ...]:
        # String classname to work around circular imports from body_spansh.py
        return ("RingsDB", self.body_id, self.name)

    @staticmethod
    def to_dict_from_spansh(spansh_asteroid: AsteroidsSpansh, body_id: int) -> dict[str, Any]:
        """Returns a RingsDB dict"""
        return {
            "body_id": body_id,
            "id64": spansh_asteroid.id64,
            "name": spansh_asteroid.name,
            "type": spansh_asteroid.type,
            "mass": spansh_asteroid.mass,
            "inner_radius": spansh_asteroid.inner_radius,
            "outer_radius": spansh_asteroid.outer_radius,
        }

    """
    Message(
        timestamp=datetime.datetime(2025, 6, 16, 0, 16, 50, tzinfo=TzInfo(UTC)),
        event=<Event.Scan: 'Scan'>, horizons=True, odyssey=True,
        StarSystem='Gliese 3680', StarPos=[116.25, 72.90625, 32.65625], SystemAddress=1522339432811,
        Factions=None, AscendingNode=0.0, BodyID=39,
        BodyName='Gliese 3680 6 A Ring',
        DistanceFromArrivalLS=1702.978673,
        Eccentricity=0.0,
        MeanAnomaly=30.131683, OrbitalInclination=0.0,
        OrbitalPeriod=48714.509606,
        Parents=[{'Planet': 38}, {'Null': 37}, {'Star': 0}], Periapsis=0.0,
        ScanType='AutoScan', SemiMajorAxis=142331823.706627, WasDiscovered=True, WasMapped=True)
    """

    @staticmethod
    def to_dicts_from_eddn_ring_body(
        ring_name: str, body_name_to_db_fn: Callable[[str], BodiesDB]
    ) -> list[dict[str, Any]] | None:
        parent_body_name = RingsDB.ring_to_body_name_re.sub(r"\g<parent_body_name>", ring_name)
        try:
            body = body_name_to_db_fn(parent_body_name)
        except ValueError as e:
            logger.warning(f"Could not find a body with name '{parent_body_name}! Err: {str(e)}")
            return None

        return [
            {
                "body_id": body.id,
                "name": ring_name,
            }
        ]

    """
    {
        '$schemaRef': 'https://eddn.edcd.io/schemas/journal/1',
        'header': {
            'gamebuild': 'r313544/r0 ', 'gameversion': '4.1.2.100',
            'gatewayTimestamp': '2025-06-16T01:12:40.409907Z', 'softwareName': 'EDDiscovery',
            'softwareVersion': '18.1.6.0', 'uploaderID': 'f58dd0fea82aed5bb11f7aab23ec464beba594aa'},
        'message': {
            'AbsoluteMagnitude': 9.251236,
            'Age_MY': 4216,
            'AxialTilt': 0.0,
            'BodyID': 0,
            'BodyName': 'Jinoharis',
            'DistanceFromArrivalLS': 0.0,
            'Luminosity': 'Va',
            'Radius': 352292096.0,
            'Rings': [
                {'InnerRad': 581280000.0, 'MassMT': 1091300000.0, 'Name': 'Jinoharis A Belt',
                    'OuterRad': 1837600000.0, 'RingClass': 'eRingClass_MetalRich'}
            ],
            'RotationPeriod': 179751.6339,
            'ScanType': 'AutoScan',
            'StarPos': [74.09375, 7.09375, 29.625],
            'StarSystem': 'Jinoharis',
            'StarType': 'M',
            'StellarMass': 0.375,
            'Subclass': 4,
            'SurfaceTemperature': 2934.0,
            'SystemAddress': 16064922592689, 'WasDiscovered': True, 'WasMapped': False, 'event': 'Scan',
            'horizons': True, 'odyssey': True, 'timestamp': '2025-06-16T01:12:33Z'}}
    {
        '$schemaRef': 'https://eddn.edcd.io/schemas/journal/1',
        'header': {
            'gamebuild': 'r313544/r0 ', 'gameversion': '4.1.2.100', 'gatewayTimestamp': '2025-06-16T01:12:47.860211Z',
            'softwareName': 'EDDiscovery', 'softwareVersion': '18.1.9.0',
            'uploaderID': 'f32da817cc82e258998c0dd25630b3274d530129'},
        'message': {
            'AscendingNode': 167.656986, 'Atmosphere': '',
            'AtmosphereComposition': [
                {'Name': 'Hydrogen', 'Percent': 73.491508}, {'Name': 'Helium', 'Percent': 26.508499}
            ],
            'AxialTilt': -0.327288, 'BodyID': 20,
            'BodyName': 'BD-15 447 A 2',
            'DistanceFromArrivalLS': 1010.523621, 'Eccentricity': 0.000715,
            'Landable': False, 'MassEM': 202.44722, 'MeanAnomaly': 36.052861, 'OrbitalInclination': 0.022825,
            'OrbitalPeriod': 108180999.755859,
            'Parents': [{'Star': 1}, {'Null': 0}], 'Periapsis': 0.611626, 'PlanetClass': 'Sudarsky class I gas giant',
            'Radius': 67883640.0, 'ReserveLevel': 'CommonResources',
            'Rings': [
                {'InnerRad': 112010000.0, 'MassMT': 134080000000.0, 'Name': 'BD-15 447 A 2 A Ring',
                    'OuterRad': 131560000.0, 'RingClass': 'eRingClass_Rocky'},
                {'InnerRad': 131650000.0, 'MassMT': 867260000000.0, 'Name': 'BD-15 447 A 2 B Ring',
                    'OuterRad': 216940000.0, 'RingClass': 'eRingClass_Icy'}
            ],
            'RotationPeriod': 64090.258668, 'ScanType': 'NavBeaconDetail', 'SemiMajorAxis': 303122597932.81555,
            'StarPos': [8.0, -81.25, -40.125], 'StarSystem': 'BD-15 447', 'SurfaceGravity': 17.5102,
            'SurfacePressure': 0.0, 'SurfaceTemperature': 143.07103, 'SystemAddress': 2007997813450,
            'TerraformState': '', 'TidalLock': False, 'Volcanism': '', 'WasDiscovered': False, 'WasMapped': True,
            'event': 'Scan', 'horizons': True, 'odyssey': True, 'timestamp': '2025-06-16T01:12:16Z'}}
    """

    @staticmethod
    def to_dicts_from_eddn_body(
        msg: journal_v1_0.Message, parent_body_name: str, body_name_to_db_fn: Callable[[str], BodiesDB]
    ) -> list[dict[str, Any]] | None:
        try:
            body = body_name_to_db_fn(parent_body_name)
        except ValueError as e:
            logger.warning(f"Could not find a body with name '{parent_body_name}! Err: {str(e)}")
            return None

        rings = []
        for ring in getattr(msg, "Rings", []):
            name = ring.get("Name", None)
            if name is None:
                logger.warning(f"Got a ring with no name! Got: {pformat(ring)}")
                continue
            elif "Belt" in name:
                continue  # We don't store belts/asteroid clusters

            inner_radius = ring.get("InnerRad", None)
            if inner_radius is None:
                logger.warning(f"Got a ring with no inner radius! Got: {pformat(ring)}")
                continue

            outer_radius = ring.get("OuterRad", None)
            if outer_radius is None:
                logger.warning(f"Got a ring with no outer radius! Got: {pformat(ring)}")
                continue

            mass_mt = ring.get("MassMT", None)
            if mass_mt is None:
                logger.warning(f"Got a ring with no mass! Got: {pformat(ring)}")
                continue

            ring_class = ring.get("RingClass", None)
            if ring_class is None:
                logger.warning(f"Got a ring with ring class! Got: {pformat(ring)}")
                continue

            rings.append(
                {
                    "body_id": body.id,
                    "name": name,
                    "inner_radius": inner_radius,
                    "outer_radius": outer_radius,
                    "mass": mass_mt,
                    "type": get_symbol_by_eddn_name(ring_class),
                }
            )

        return rings

    """
    - SAASignalsFound # Hotspots
        'BodyID': 9,
        'BodyName': 'Col 285 Sector XS-E b26-4 1 B Ring',
        'Genuses': [],
        'Signals': [{'Count': 1, 'Type': 'Rhodplumsite'}, {'Count': 1, 'Type': 'Monazite'}],
        'StarPos': [-161.0, -54.875, 200.15625],
        'StarSystem': 'Col 285 Sector XS-E b26-4',
        'SystemAddress': 9464899839481,
        'event': 'SAASignalsFound', 'horizons': True, 'odyssey': True, 'timestamp': '2025-05-22T00:54:04Z'}}
    """
    ring_to_body_name_re = re.compile(r"(?P<parent_body_name>.*)\s+\w+ Ring")

    @staticmethod
    def to_dicts_from_eddn(
        model: journal_v1_0.Model, body_name_to_db_fn: Callable[[str], BodiesDB]
    ) -> list[dict[str, Any]] | None:
        msg = model.message

        body_name = getattr(msg, "BodyName", None)
        if body_name is None:
            return None

        if "Ring" in body_name:
            # Scan events for an actual Ring don't contain ring information.
            # Just store the ring name so we know it exists.
            return RingsDB.to_dicts_from_eddn_ring_body(body_name, body_name_to_db_fn)
        else:
            return RingsDB.to_dicts_from_eddn_body(msg, body_name, body_name_to_db_fn)

    def __repr__(self) -> str:
        return f"<RingsDB(id={self.id}, name={self.name})>"


class HotspotsDB(BaseModelWithId):
    unique_columns = ("ring_id", "commodity_sym")
    __tablename__ = "hotspots"
    __table_args__ = (UniqueConstraint(*unique_columns, name="_ring_and_commodity_uc"), {"schema": "core"})

    ring_id: Mapped[int] = mapped_column(ForeignKey("core.rings.id"), nullable=False, index=True)
    ring: Mapped["RingsDB"] = relationship(back_populates="hotspots")
    commodity_sym: Mapped[str] = mapped_column(
        ForeignKey("core.commodities.symbol"), index=True
    )  # Small lookup table; no index

    count: Mapped[Optional[int]] = mapped_column(Integer)

    updated_at: Mapped[Optional[DateTime]] = mapped_column(DateTime)

    @staticmethod
    def to_dicts_from_spansh(spansh_signal: SignalsSpansh, ring_id: int) -> list[dict[str, Any]]:
        return [
            {
                "ring_id": ring_id,
                "commodity_sym": signal_type,
                "count": count,
                "updated_at": spansh_signal.updated_at,
            }
            for signal_type, count in spansh_signal.signals.items()
        ]

    """
    - SAASignalsFound # Hotspots
        'BodyID': 9,
        'BodyName': 'Col 285 Sector XS-E b26-4 1 B Ring',
        'Genuses': [],
        'Signals': [{'Count': 1, 'Type': 'Rhodplumsite'}, {'Count': 1, 'Type': 'Monazite'}],
        'StarPos': [-161.0, -54.875, 200.15625],
        'StarSystem': 'Col 285 Sector XS-E b26-4',
        'SystemAddress': 9464899839481,
        'event': 'SAASignalsFound', 'horizons': True, 'odyssey': True, 'timestamp': '2025-05-22T00:54:04Z'}}
    """

    @staticmethod
    def to_dicts_from_eddn(
        model: journal_v1_0.Model, ring_name_to_ring_db: Callable[[str], RingsDB]
    ) -> list[dict[str, Any]] | None:
        msg = model.message
        ring_name = getattr(msg, "BodyName", None)
        if ring_name is None:
            return None

        try:
            ring = ring_name_to_ring_db(ring_name)
        except ValueError as e:
            logger.warning(f"Tried saving a hotspot but could not find a ring with name '{ring_name}'! Err: {str(e)}")
            return None

        hotspot_dicts = []
        for signal in getattr(msg, "Signals", []):
            commodity = signal.get("Type", None)
            if commodity is None:
                logger.warning(f"Got a signal with no Type! Got: '{pformat(signal)}'")
                continue

            count = signal.get("Count", None)
            if count is None:
                logger.warning(f"Got a signal with no Count! Got: '{pformat(signal)}'")
                continue

            # For whatever reason, Tritium gets submitted lowercase... The rest are capitalized.
            if commodity == "tritium":
                commodity = "Tritium"

            hotspot_dicts.append(
                {
                    "ring_id": ring.id,
                    "commodity_sym": commodity,
                    "count": count,
                    "updated_at": msg.timestamp,
                }
            )

        return hotspot_dicts

    def __repr__(self) -> str:
        return f"<HotspotsDB(id={self.id}, commodity_sym={self.commodity_sym})>"


class MiningMapsDB(BaseModelWithId):
    unique_columns = ("system_id", "body_id", "ring_id", "name")
    __tablename__ = "mining_maps"
    __table_args__ = (UniqueConstraint(*unique_columns, name="_mining_map_uc"), {"schema": "core"})

    # Probably default to ring name + hotspot
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    system_id: Mapped[int] = mapped_column(ForeignKey("core.systems.id"), nullable=False, index=True)
    body_id: Mapped[int] = mapped_column(ForeignKey("core.bodies.id"), nullable=False, index=True)
    ring_id: Mapped[int] = mapped_column(ForeignKey("core.rings.id"), nullable=False, index=True)

    rock_count: Mapped[int] = mapped_column(SmallInteger)
    map_url: Mapped[str] = mapped_column(Text)
    approximate_merits_solo: Mapped[int] = mapped_column(Integer)  # Approx when _solo_. Wings will get multipliers.

    def __repr__(self) -> str:
        return f"<MiningMapsDB(id={self.id}, name={self.name})>"


class MiningMapCommoditiesDB(BaseModelWithId):
    unique_columns = ("mining_map_id", "commodity_sym")
    __tablename__ = "mining_map_commodities"
    __table_args__ = (UniqueConstraint(*unique_columns, name="_mining_map_commodities_uc"), {"schema": "core"})

    mining_map_id: Mapped[int] = mapped_column(ForeignKey("core.mining_maps.id"), nullable=False, index=True)
    commodity_sym: Mapped[str] = mapped_column(Text, ForeignKey("core.commodities.symbol"), nullable=False, index=True)

    # Optional but potentially useful approximate tonnage of commodity from map, SOLO
    approximate_tonnage_solo: Mapped[int] = mapped_column(Integer)

    def __repr__(self) -> str:
        return (
            f"<MiningMapCommodity(id={self.id}, map_id={self.mining_map_id}, "
            f"commodity={self.commodity_sym}, tons={self.approximate_tonnage_solo})>"
        )


class FarmableCoresDB(BaseModelWithId):
    unique_columns = ("system_id", "body_id", "hotspot_id", "commodity_sym")
    __tablename__ = "farmable_cores"
    __table_args__ = (UniqueConstraint(*unique_columns, name="_farmable_cores_uc"), {"schema": "core"})

    system_id: Mapped[int] = mapped_column(ForeignKey("core.systems.id"), nullable=False, index=True)
    body_id: Mapped[int] = mapped_column(ForeignKey("core.bodies.id"), nullable=False, index=True)
    hotspot_id: Mapped[int] = mapped_column(ForeignKey("core.hotspots.id"), nullable=False, index=True)

    commodity_sym: Mapped[str] = mapped_column(Text, ForeignKey("core.commodities.symbol"), nullable=False, index=True)

    hotspot_from_sc_img: Mapped[int] = mapped_column(ForeignKey("core.binary_data.id"), nullable=False, index=True)
    core_from_drop_img: Mapped[int] = mapped_column(ForeignKey("core.binary_data.id"), nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<FarmableCoresDB(id={self.id}, hotspot_id={self.hotspot_id}, commodity_sym={self.commodity_sym}>"


class BinaryDataDB(BaseModelWithId):
    unique_columns = ("id",)
    __tablename__ = "binary_data"
    __table_args__ = {"schema": "core"}

    # https://amat.su/M067l-
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    type: Mapped[str] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<ImagesDB(id={self.id}, size={len(self.data)}"


class StationsDB(BaseModelWithId):
    unique_columns = ("name", "owner_id")
    __tablename__ = "stations"

    @typing.no_type_check
    @declared_attr
    def __table_args__(cls) -> tuple[Any, ...] | dict[str, Any]:
        return (
            UniqueConstraint(*cls.unique_columns, name="_station_name_owner_distance_uc"),
            Index(
                "ix_core_stations_owner_id_type",
                cls.owner_id,
                cls.owner_type,
            ),
            {"schema": "core"},
        )

    id64: Mapped[Optional[int]] = mapped_column(BigInteger)
    id_spansh: Mapped[Optional[int]] = mapped_column(BigInteger)
    id_edsm: Mapped[Optional[int]] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(Text, nullable=False, index=True)  # Station name is NOT unique

    owner_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    owner_type: Mapped[str] = mapped_column(Text, nullable=False, index=True)

    allegiance: Mapped[Optional[str]] = mapped_column(Text)
    controlling_faction: Mapped[Optional[str]] = mapped_column(Text)
    controlling_faction_state: Mapped[Optional[str]] = mapped_column(Text)
    distance_to_arrival: Mapped[Optional[float]] = mapped_column(Float)
    economies: Mapped[Optional[dict[str, float]]] = mapped_column(JSONB)
    government: Mapped[Optional[str]] = mapped_column(Text)

    large_landing_pads: Mapped[Optional[int]] = mapped_column(Integer)
    medium_landing_pads: Mapped[Optional[int]] = mapped_column(Integer)
    small_landing_pads: Mapped[Optional[int]] = mapped_column(Integer)

    primary_economy: Mapped[Optional[str]] = mapped_column(Text)
    services: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))
    type: Mapped[Optional[str]] = mapped_column(Text)

    # It kind of is a station-level detail...
    prohibited_commodities: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))

    carrier_name: Mapped[Optional[str]] = mapped_column(Text)
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)

    spansh_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    edsm_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    eddn_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    def to_cache_key_tuple(self) -> Tuple[Any, ...]:
        tup = ("StationsDB", self.owner_id, self.name)
        logger.trace(f"STATIONSDB TO CACHE KEY TUPLE: {tup}")
        return tup

    @staticmethod
    def to_dict_from_spansh(spansh_station: StationSpansh, owner_id: int, owner_type: str) -> dict[str, Any]:
        if spansh_station.landing_pads is not None:
            large_pads = spansh_station.landing_pads.get("large", 0)
            medium_pads = spansh_station.landing_pads.get("medium", 0)
            small_pads = spansh_station.landing_pads.get("small", 0)
        else:
            large_pads = 0
            medium_pads = 0
            small_pads = 0
        return {
            "id_spansh": spansh_station.id,
            "owner_id": owner_id,
            "owner_type": owner_type,
            "name": spansh_station.name,
            "allegiance": spansh_station.allegiance,
            "controlling_faction": spansh_station.controlling_faction,
            "controlling_faction_state": spansh_station.controlling_faction_state,
            "distance_to_arrival": spansh_station.distance_to_arrival,
            "economies": spansh_station.economies,
            "government": spansh_station.government,
            "large_landing_pads": large_pads,
            "medium_landing_pads": medium_pads,
            "small_landing_pads": small_pads,
            "primary_economy": spansh_station.primary_economy,
            "prohibited_commodities": getattr(spansh_station.market, "prohibited_commodities", None),
            "services": spansh_station.services,
            "type": spansh_station.type,
            "carrier_name": spansh_station.carrier_name,
            "latitude": spansh_station.latitude,
            "longitude": spansh_station.longitude,
            "spansh_updated_at": spansh_station.update_time,
        }

    planetary_station_types: list[str] = [
        "Planetary Outpost",
        "Planetary Port",
        "Planetary Settlement",
        "Planetary Engineer Base",
        "Unknown Planetary",
        "Odyssey Settlement",
    ]
    starport_station_types: list[str] = [
        "Bernal Starport",
        "Coriolis Starport",
        "Ocellus Starport",
        "Orbis Starport",
        "Outpost",
        "Asteroid base",
        "Mega ship",
    ]

    @staticmethod
    def to_owner_id_and_type_from_eddn(
        journal_entry: journal_v1_0.Message,
        station_type: str,
        system_id: int,
        body_name_to_db_fn: Callable[[str], BodiesDB],
    ) -> Tuple[int, str]:
        owner_type = None
        if station_type in StationsDB.planetary_station_types:
            owner_type = "body"
        elif station_type in StationsDB.starport_station_types:
            owner_type = "system"
        else:
            logger.warning(f"Got a station type we didn't know about! '{station_type}'\n{pformat(journal_entry)}")
            raise ValueError(f"Unknown station type '{station_type}'!")

        if owner_type == "system":
            owner_id = system_id
        elif owner_type == "body":
            body_name = getattr(journal_entry, "Body", None)
            if body_name is None:
                logger.error(
                    "Tried saving a Planetary station but could not find a 'Body' field in the Journal entry! "
                    f"'{pformat(journal_entry)}'"
                )
                raise ValueError("Journal entry has no 'Body' field!")
            try:
                body = body_name_to_db_fn(body_name)
            except Exception:
                logger.error(
                    f"Tried saving a Planetary station but did not know about its planetary body! Body: '{body_name}'"
                )
                raise ValueError(f"Didn't know about a Body name from a Journal Entry! '{body_name}'")
            owner_id = body.id
        else:
            raise Exception(f"Somehow got unknown owner_type: '{owner_type}'")

        return (owner_id, owner_type)

    @staticmethod
    def journal_entry_to_station_name(journal_entry: journal_v1_0.Message) -> str | None:
        station_name = cast(str, getattr(journal_entry, "StationName", None))
        if station_name is None:
            return None  # Has no station information

        station_name = cast(str, getattr(journal_entry, "StationName", None))
        station_name = station_name.replace("$EXT_PANEL_ColonisationShip;", "")

        return station_name

    @staticmethod
    def to_station_type_and_owner_id_type_from_journal_entry(
        eddn_model: journal_v1_0.Model, system_id: int, body_name_to_db_fn: Callable[[str], "BodiesDB"]
    ) -> Tuple[str, int, str] | None:
        journal_entry = eddn_model.message

        station_type = getattr(journal_entry, "StationType", None)
        if station_type is None:
            logger.warning(f"Got a Journal entry with a StationName but no StationType!\n{pformat(eddn_model)}")
            return None  # Has no station type

        sym = get_symbol_by_eddn_name(station_type)
        if sym is None:
            logger.warning(f"==> Skipping Station Type: {station_type}")
            return None  # TODO: Remove after handling FleetCarrier, PlanetaryConstructionDepot, SpaceConstructionDepot
        normalized_station_type = sym

        try:
            [owner_id, owner_type] = StationsDB.to_owner_id_and_type_from_eddn(
                journal_entry, normalized_station_type, system_id, body_name_to_db_fn
            )
        except ValueError:
            return None  # TODO: Remove

        return (normalized_station_type, owner_id, owner_type)

    @staticmethod
    def to_economies_from_journal_entry(journal_entry: journal_v1_0.Message) -> dict[str, float] | None:
        economies: dict[str, float] = {}
        for econ in getattr(journal_entry, "StationEconomies", []):
            econ_type = get_symbol_by_eddn_name(econ["Name"])
            if econ_type is None:
                logger.warning(f"Did not recognize economy type name! Got: '{pformat(econ)}'")
                return None
            try:
                economies[econ_type] = float(econ["Proportion"]) * 100
            except ValueError:
                logger.warning(f"Could not convert economy proportion to a valid float! Got: '{pformat(econ)}'")
                return None
        return economies

    blocklisted_faction_names: list[str] = [
        "FleetCarrier",
        "Felicity Farseer",
        "Juri Ishmaak",
        "Colonel Bris Dekker",
        "The Sarge",
        "Elvira Martuuk",
        "Marco Qwent",
        "Professor Palin",
        "Lori Jameson",
        "Chloe Sedesi",
        "Zacariah Nemo",
        "Mel Brandon",
        "The Dweller",
        "Lei Cheung",
        "Ram Tah",
        "Marsha Hicks",
        "Tod 'The Blaster' McQuinn",
        "Selene Jean",
        "Didi Vatermann",
        "Bill Turner",
        "Petra Olmanova",
        "Liz Ryder",
        "Hera Tani",
        "Broo Tarquin",
        "Tiana Fortune",
        "Etienne Dorn",
        "Hero Ferrari",
        "Wellington Beck",
        "Uma Laszlo",
        "Jude Navarro",
        "Terra Velasquez",
        "Oden Geiger",
        "Domino Green",
        "Kit Fowler",
        "Yarden Bond",
        "Eleanor Bresa",
        "Yi Shen",
        "Rosa Dayette",
        "Baltanos",
    ]

    @staticmethod
    def to_dict_from_eddn(
        eddn_model: journal_v1_0.Model,
        system_id: int,
        body_name_to_db_fn: Callable[[str], BodiesDB],
        station_name_and_system_id_to_db_fn: Callable[[str, int], ResolvedStationResult],
        faction_name_to_db_fn: Callable[[str], "FactionsDB"],
    ) -> dict[str, Any] | None:
        # TODO: Black market, Carrier Name
        journal_entry = eddn_model.message

        station_name = StationsDB.journal_entry_to_station_name(journal_entry)
        if station_name is None:
            return None  # Has no station information

        id64 = getattr(journal_entry, "MarketID", None)
        if id64 is None:
            logger.warning(f"Tried saving a station with no MarketId! '{pformat(journal_entry)}'")
            return None

        try:
            existing_station = station_name_and_system_id_to_db_fn(station_name, system_id)
        except ValueError:
            logger.debug(f"Did not know about station '{station_name}' in system id {system_id}")
            existing_station = None

        # Some Journal entries don't contain a Body field, which makes it impossible to determine
        # which body a planetary station belongs to. In such a case, we must rely on the station already existing in
        # the DB in order to map its correct owner_id (body_id)
        #
        # My hypothesis is that certain journal event enums contain Body while others don't,
        # even for the same logical station (Eg, Docked vs Location). Thus "order matters" with the event ingestion
        if existing_station is not None:
            normalized_station_type = existing_station.type
            owner_id = existing_station.owner_id
            owner_type = existing_station.owner_type
        else:
            result = StationsDB.to_station_type_and_owner_id_type_from_journal_entry(
                eddn_model, system_id, body_name_to_db_fn
            )

            if result is None:
                return None

            [normalized_station_type, owner_id, owner_type] = result

        primary_economy = getattr(journal_entry, "StationEconomy", None)
        government = getattr(journal_entry, "StationGovernment", None)
        economies = StationsDB.to_economies_from_journal_entry(journal_entry)

        # Base Attributes
        d: dict[str, Any] = {
            "id64": id64,
            "name": station_name,
            "type": normalized_station_type,
            "owner_id": owner_id,
            "owner_type": owner_type,
            "distance_to_arrival": getattr(journal_entry, "DistFromStarLS", None),
            "primary_economy": get_symbol_by_eddn_name(primary_economy) if primary_economy is not None else None,
            "economies": economies,
            "government": get_symbol_by_eddn_name(government) if government is not None else None,
            "services": getattr(journal_entry, "StationServices", []),
            "eddn_updated_at": eddn_model.message.timestamp,
            "latitude": getattr(journal_entry, "Latitude", None),
            "longitude": getattr(journal_entry, "Longitude", None),
        }

        # Controlling Faction
        try:
            station_faction = getattr(journal_entry, "StationFaction", {})
            station_faction_name = station_faction.get("Name")
            station_faction_state = station_faction.get("State", None)
        except Exception:
            station_faction_name = None
            station_faction_state = None

        if station_faction_name is not None and station_faction_name not in StationsDB.blocklisted_faction_names:
            try:
                faction = faction_name_to_db_fn(station_faction_name)
            except Exception:
                logger.info(pformat(eddn_model))
                return None
            d["allegiance"] = faction.allegiance
            d["controlling_faction"] = faction.name
            d["controlling_faction_state"] = station_faction_state

        # Landing Pads
        landing_pads = getattr(journal_entry, "LandingPads", None)
        if landing_pads is not None:
            d["small_landing_pads"] = landing_pads.get("Small", 0)
            d["medium_landing_pads"] = landing_pads.get("Medium", 0)
            d["large_landing_pads"] = landing_pads.get("Large", 0)

        return {k: v for k, v in d.items() if v is not None}

    def __repr__(self) -> str:
        return f"<StationsDB(id={self.id}, name={self.name!r})>"

    @property
    def parent(self) -> Union["SystemsDB", BodiesDB]:
        session = Session.object_session(self)
        if session is None:
            raise Exception("Could not find a valid Session attached to StationsDB object!")

        parent: Optional[SystemsDB | BodiesDB] = None
        if self.owner_type == "system":
            parent = session.execute(select(SystemsDB).where(SystemsDB.id == self.owner_id)).scalar_one_or_none()
        elif self.owner_type == "body":
            parent = session.execute(select(BodiesDB).where(BodiesDB.id == self.owner_id)).scalar_one_or_none()
        else:
            raise ValueError(f"Unknown owner_type: {self.owner_type}")

        if parent is None:
            raise Exception("Could not find a valid parent object!")

        return parent


class CommoditiesDB(BaseModel):
    unique_columns = ("symbol",)
    __tablename__ = "commodities"
    __table_args__ = {"schema": "core"}

    id64: Mapped[Optional[int]] = mapped_column(BigInteger)

    symbol: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, index=True)

    # average prices are gathered via materialized view `derived.commodity_prices_view`
    rare_goods: Mapped[Optional[bool]] = mapped_column(Boolean, index=True)
    corrosive: Mapped[Optional[bool]] = mapped_column(Boolean, index=True)

    category: Mapped[Optional[str]] = mapped_column(Text, index=True)
    is_mineable: Mapped[Optional[bool]] = mapped_column(Boolean, index=True)
    ring_types: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), index=True)
    mining_method: Mapped[Optional[str]] = mapped_column(Text, index=True)
    has_hotspots: Mapped[Optional[bool]] = mapped_column(Boolean, index=True)

    def __repr__(self) -> str:
        return f"<CommoditiesDB(id='{self.symbol}', name={self.name!r})>"


class MarketCommoditiesDB(BaseModelWithId):
    unique_columns = ("station_id", "commodity_sym")
    __tablename__ = "market_commodities"

    @typing.no_type_check
    @declared_attr
    def __table_args__(cls):
        return (
            UniqueConstraint(*cls.unique_columns, name="_station_market_commodity_uc"),
            Index(
                "ix_core_market_commodities_supplydemand_updated_at",
                cls.updated_at,
                cls.supply,
                cls.demand,
            ),
            {"schema": "core"},
        )

    station_id: Mapped[int] = mapped_column(Integer, ForeignKey("core.stations.id"), nullable=False, index=True)
    commodity_sym: Mapped[str] = mapped_column(Text, ForeignKey("core.commodities.symbol"), nullable=False, index=True)

    buy_price: Mapped[Optional[int]] = mapped_column(Integer)
    sell_price: Mapped[Optional[int]] = mapped_column(Integer)
    supply: Mapped[Optional[int]] = mapped_column(Integer)
    demand: Mapped[Optional[int]] = mapped_column(Integer)
    updated_at: Mapped[Optional[DateTime]] = mapped_column(DateTime, index=True)

    demand_bracket: Mapped[Optional[int]] = mapped_column(SmallInteger)
    supply_bracket: Mapped[Optional[int]] = mapped_column(SmallInteger)

    @staticmethod
    def to_dict_from_spansh(
        spansh_commodity: CommoditySpansh, station_id: int, commodity_sym: str, market_updated_at: datetime | None
    ) -> dict[str, Any]:
        return {
            "station_id": station_id,
            "commodity_sym": commodity_sym,
            "buy_price": spansh_commodity.buy_price,
            "sell_price": spansh_commodity.sell_price,
            "supply": spansh_commodity.supply,
            "demand": spansh_commodity.demand,
            "updated_at": spansh_commodity.updated_at or market_updated_at,
        }

    @staticmethod
    def to_dicts_from_eddn(eddn_model: commodity_v3_0.Model, station_id: int) -> list[dict[str, Any]]:
        dicts = []
        for commodity in eddn_model.message.commodities:
            symbol = get_symbol_by_eddn_name(commodity.name)
            if symbol is None:
                logger.warning(
                    f"Encountered a commodity in an EDDN Commodity model we didn't know about! Got: '{commodity.name}'"
                )
                continue

            demand_bracket = (
                commodity.demandBracket.value if commodity.demandBracket != commodity_v3_0.LevelType.field_ else -1
            )
            supply_bracket = (
                commodity.stockBracket.value if commodity.stockBracket != commodity_v3_0.LevelType.field_ else -1
            )

            dicts.append(
                {
                    "station_id": station_id,
                    "commodity_sym": symbol,
                    "buy_price": commodity.buyPrice,
                    "sell_price": commodity.sellPrice,
                    "supply": commodity.stock,
                    "demand": commodity.demand,
                    "updated_at": eddn_model.message.timestamp,
                    "demand_bracket": demand_bracket,
                    "supply_bracket": supply_bracket,
                }
            )
        return dicts

    def __repr__(self) -> str:
        return f"<MarketCommoditiesDB(id={self.id}, station_id={self.station_id}, commodity_sym={self.commodity_sym})>"


class ShipsDB(BaseModel):
    __tablename__ = "ships"
    __table_args__ = {"schema": "core"}

    symbol: Mapped[str] = mapped_column(Text, primary_key=True)

    name: Mapped[Optional[str]] = mapped_column(Text)
    ship_id: Mapped[Optional[int]] = mapped_column(Integer)
    updated_at: Mapped[Optional[DateTime]] = mapped_column(DateTime)

    @staticmethod
    def to_dict_from_spansh(station_id: int, ship_id: int) -> dict[str, Any]:
        return {
            "station_id": station_id,
            "ship_id": ship_id,
        }

    def __repr__(self) -> str:
        return f"<ShipsDB(symbol={self.symbol}, name={self.name})>"


class ShipyardShipsDB(BaseModelWithId):
    unique_columns = (
        "station_id",
        "ship_sym",
    )
    __tablename__ = "shipyard_ships"
    __table_args__ = (UniqueConstraint(*unique_columns, name="_station_shipyard_ship_uc"), {"schema": "core"})

    station_id: Mapped[int] = mapped_column(Integer, ForeignKey("core.stations.id"), nullable=False, index=True)
    ship_sym: Mapped[str] = mapped_column(
        Text, ForeignKey("core.ships.symbol"), nullable=False
    )  # Small lookup table; no index

    def __repr__(self) -> str:
        return f"<ShipyardShipsDB(id={self.id}, station_id={self.station_id}, ship_sym={self.ship_sym})>"


class ShipModulesDB(BaseModel):
    __tablename__ = "ship_modules"
    __table_args__ = {"schema": "core"}

    name: Mapped[str] = mapped_column(Text, primary_key=True)

    module_id: Mapped[Optional[int]] = mapped_column(Integer)
    symbol: Mapped[str] = mapped_column(Text)
    category: Mapped[Optional[str]] = mapped_column(Text)
    rating: Mapped[Optional[str]] = mapped_column(Text)
    ship: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[Optional[DateTime]] = mapped_column(DateTime)

    @staticmethod
    def to_dict_from_spansh(station_id: int, module_id: int) -> dict[str, Any]:
        return {
            "station_id": station_id,
            "module_id": module_id,
        }

    def __repr__(self) -> str:
        return f"<ShipModulesDB(name={self.name})>"


class OutfittingShipModulesDB(BaseModelWithId):
    unique_columns = (
        "station_id",
        "module_name",
    )
    __tablename__ = "outfitting_ship_modules"
    __table_args__ = (UniqueConstraint(*unique_columns, name="_station_outfitting_module_uc"), {"schema": "core"})

    station_id: Mapped[int] = mapped_column(Integer, ForeignKey("core.stations.id"), nullable=False, index=True)
    module_name: Mapped[str] = mapped_column(
        Text, ForeignKey("core.ship_modules.name"), nullable=False
    )  # Small lookup table; no index
    updated_at: Mapped[Optional[DateTime]] = mapped_column(DateTime)

    def __repr__(self) -> str:
        return f"<OutfittingShipModulesDB(id={self.id}, station_id={self.station_id}, module_name={self.module_name})>"


class ThargoidWarDB(BaseModelWithId):
    unique_columns = ("system_id",)
    __tablename__ = "thargoid_wars"
    __table_args__ = {"schema": "core"}

    system_id: Mapped[int] = mapped_column(Integer, ForeignKey("core.systems.id"), nullable=False, index=True)

    current_state: Mapped[str] = mapped_column(Text)
    days_remaining: Mapped[float] = mapped_column(Float)
    failure_state: Mapped[str] = mapped_column(Text)
    ports_remaining: Mapped[float] = mapped_column(Float)
    progress: Mapped[float] = mapped_column(Float)
    success_reached: Mapped[bool] = mapped_column(Boolean)
    success_state: Mapped[str] = mapped_column(Text)

    @staticmethod
    def to_dict_from_spansh(war: ThargoidWarSpansh) -> dict[str, Any]:
        # TODO: This isn't actually used oops
        return {
            "current_state": war.current_state,
            "days_remaining": war.days_remaining,
            "failure_state": war.failure_state,
            "ports_remaining": war.ports_remaining,
            "progress": war.progress,
            "success_reached": war.success_reached,
            "success_state": war.success_state,
        }

    def __repr__(self) -> str:
        return f"<ThargoidWarDB(id={self.id}, system_id={self.system_id}, current_state={self.current_state})>"


class FactionsDB(BaseModelWithId):
    unique_columns = ("name",)
    __tablename__ = "factions"
    __table_args__ = {"schema": "core"}

    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    allegiance: Mapped[Optional[str]] = mapped_column(Text)
    government: Mapped[Optional[str]] = mapped_column(Text)
    is_player: Mapped[Optional[bool]] = mapped_column(Boolean)

    faction_presences: Mapped[list["FactionPresencesDB"]] = relationship(back_populates="faction")

    @staticmethod
    def to_dict_from_spansh(spansh_faction: FactionSpansh | ControllingFactionSpansh) -> dict[str, Any]:
        return {
            "name": spansh_faction.name,
            "allegiance": spansh_faction.allegiance,
            "government": spansh_faction.government,
        }

    @staticmethod
    def to_dicts_from_eddn(eddn_model: journal_v1_0.Model) -> list[dict[str, Any]]:
        factions = eddn_model.message.Factions or []

        dicts: list[dict[str, Any]] = []
        for faction in factions:
            if faction.Name is None:
                logger.warning(f"Found a Faction without a Name! {pformat(faction)}")
                continue

            dicts.append(
                {
                    "name": faction.Name,
                    "allegiance": faction.Allegiance,
                    "government": faction.Government,
                }
            )

        return dicts

    def __repr__(self) -> str:
        return f"<FactionsDB(id={self.id}, name={self.name})>"


class FactionPresencesDB(BaseModelWithId):
    unique_columns = ("system_id", "faction_id")
    __tablename__ = "faction_presences"
    __table_args__ = (
        UniqueConstraint(*unique_columns, name="_system_faction_presence_uc"),
        {"schema": "core"},
    )

    system_id: Mapped[int] = mapped_column(ForeignKey("core.systems.id"), nullable=False, index=True)
    system: Mapped["SystemsDB"] = relationship(back_populates="faction_presences")
    faction_id: Mapped[int] = mapped_column(ForeignKey("core.factions.id"), nullable=False, index=True)
    faction: Mapped["FactionsDB"] = relationship(back_populates="faction_presences")

    influence: Mapped[Optional[float]] = mapped_column(Float)
    state: Mapped[Optional[str]] = mapped_column(Text, index=True)
    happiness: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)

    active_states: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), index=True)
    pending_states: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))
    recovering_states: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))

    @staticmethod
    def to_dict_from_spansh(spansh_faction: FactionSpansh, system_id: int, faction_id: int) -> dict[str, Any]:
        return {
            "system_id": system_id,
            "faction_id": faction_id,
            "influence": spansh_faction.influence,
            "state": spansh_faction.state,
        }

    none_filter_bypass = ["happiness"]

    @staticmethod
    def to_dicts_from_eddn(
        eddn_model: journal_v1_0.Model, system_id: int, faction_name_to_id_mapping: dict[str, int]
    ) -> list[dict[str, Any]]:
        factions = eddn_model.message.Factions or []

        dicts: list[dict[str, Any]] = []
        for faction in factions:
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
                "system_id": system_id,
                "faction_id": faction_id,
                "influence": faction.Influence,
                "state": get_symbol_by_eddn_name(faction.FactionState) if faction.FactionState is not None else None,
                "happiness": get_symbol_by_eddn_name(faction.Happiness) if faction.Happiness is not None else None,
                "updated_at": eddn_model.message.timestamp,
                "active_states": [get_symbol_by_eddn_name(state.State) for state in faction.ActiveStates or []],
                "pending_states": [get_symbol_by_eddn_name(state.State) for state in faction.PendingStates or []],
                "recovering_states": [get_symbol_by_eddn_name(state.State) for state in faction.RecoveringStates or []],
            }

            d_filtered = {k: v for k, v in d.items() if v is not None or k in FactionPresencesDB.none_filter_bypass}
            dicts.append(d_filtered)

        return dicts

    def __repr__(self) -> str:
        return f"<FactionPresencesDB(id={self.id}, system_id={self.system_id}, faction_id={self.faction_id})>"


class SystemsDB(BaseModelWithId):
    unique_columns = ("name",)
    __tablename__ = "systems"

    __table_args__ = (
        Index(
            "ix_systems_coords_3d",
            "coords",
            postgresql_using="gist",
            postgresql_ops={"coords": "gist_geometry_ops_nd"},
        ),
        {"schema": "core"},
    )

    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    id64: Mapped[Optional[int]] = mapped_column(BigInteger)
    id_spansh: Mapped[Optional[int]] = mapped_column(BigInteger)
    id_edsm: Mapped[Optional[int]] = mapped_column(BigInteger)

    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    z: Mapped[float] = mapped_column(Float)
    coords: Mapped[WKBElement] = mapped_column(Geometry(geometry_type="POINTZ", srid=0))

    date: Mapped[Optional[datetime]] = mapped_column(DateTime)

    allegiance: Mapped[Optional[str]] = mapped_column(Text)
    population: Mapped[Optional[int]] = mapped_column(BigInteger)
    primary_economy: Mapped[Optional[str]] = mapped_column(Text)
    secondary_economy: Mapped[Optional[str]] = mapped_column(Text)
    security: Mapped[Optional[str]] = mapped_column(Text)
    government: Mapped[Optional[str]] = mapped_column(Text)
    body_count: Mapped[Optional[int]] = mapped_column(Integer)
    controlling_power: Mapped[Optional[str]] = mapped_column(Text)
    power_conflict_progress: Mapped[Optional[list[dict[str, float]]]] = mapped_column(JSONB)
    power_state: Mapped[Optional[str]] = mapped_column(Text)
    power_state_control_progress: Mapped[Optional[float]] = mapped_column(Float)
    power_state_reinforcement: Mapped[Optional[float]] = mapped_column(Float)
    power_state_undermining: Mapped[Optional[float]] = mapped_column(Float)
    powers: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))
    thargoid_war: Mapped[Optional[dict[str, float]]] = mapped_column(JSONB)

    controlling_power_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    power_state_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    powers_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    controlling_faction_id: Mapped[Optional[int]] = mapped_column(ForeignKey("core.factions.id"), index=True)
    controlling_faction: Mapped[Optional["FactionsDB"]] = relationship()

    bodies: Mapped[list["BodiesDB"]] = relationship(back_populates="system")
    faction_presences: Mapped[list["FactionPresencesDB"]] = relationship(back_populates="system")
    stations: Mapped[list["StationsDB"]] = relationship(
        "StationsDB",
        primaryjoin=lambda: and_(
            foreign(StationsDB.owner_id) == SystemsDB.id, StationsDB.owner_type == literal("system")
        ),
        overlaps="stations",
    )

    def to_cache_key_tuple(self) -> Tuple[Any, ...]:
        return ("SystemsDB", self.name)

    @staticmethod
    def coords_spansh_to_wkbelement(coords: CoordinatesSpansh) -> WKBElement:
        return from_shape(Point(coords.x, coords.y, coords.z), srid=0)

    @staticmethod
    def power_conflict_progress_to_dict_from_spansh(participant: PowerConflictProgressSpansh) -> dict[str, str | float]:
        return {
            "power": participant.power,
            "progress": participant.progress,
        }

    @staticmethod
    def to_dict_from_spansh(spansh_system: SystemSpansh, controlling_faction_id: int | None) -> dict[str, Any]:
        return {
            "allegiance": spansh_system.allegiance,
            "controlling_faction_id": controlling_faction_id,
            "x": spansh_system.coords.x,
            "y": spansh_system.coords.y,
            "z": spansh_system.coords.z,
            "coords": SystemsDB.coords_spansh_to_wkbelement(spansh_system.coords),
            "date": spansh_system.date,
            "government": spansh_system.government,
            "id64": spansh_system.id64,
            "name": spansh_system.name,
            "population": spansh_system.population,
            "primary_economy": spansh_system.primary_economy,
            "secondary_economy": spansh_system.secondary_economy,
            "security": spansh_system.security,
            "body_count": spansh_system.body_count,
            "controlling_power": spansh_system.controlling_power,
            "power_conflict_progress": [
                SystemsDB.power_conflict_progress_to_dict_from_spansh(participant)
                for participant in spansh_system.power_conflict_progress or []
            ],
            "power_state": spansh_system.power_state,
            "power_state_control_progress": spansh_system.power_state_control_progress,
            "power_state_reinforcement": spansh_system.power_state_reinforcement,
            "power_state_undermining": spansh_system.power_state_undermining,
            "powers": spansh_system.powers,
            # "thargoid_war": (
            #   spansh_system.thargoid_war.to_sqlalchemy_dict()
            #   if spansh_system.thargoid_war is not None else None
            # ),
            "controlling_power_updated_at": getattr(spansh_system.timestamps, "controlling_power", None),
            "power_state_updated_at": getattr(spansh_system.timestamps, "power_state", None),
            "powers_updated_at": getattr(spansh_system.timestamps, "powers", None),
        }

    @staticmethod
    def starpos_to_wkbelement(coords: tuple[float, float, float]) -> WKBElement:
        return from_shape(Point(coords[0], coords[1], coords[2]), srid=0)

    @staticmethod
    def to_dict_from_eddn(eddn_model: journal_v1_0.Model, controlling_faction_id: int | None) -> dict[str, Any]:
        """
        StarSystem='Catun',
        StarPos=[-4.71875, 25.625, -105.0625],
        SystemAddress=2621817489755,
        Body='Catun',
        BodyID=0,
        BodyType='Star',
        Conflicts=[{
            'Faction1': {'Name': 'Catun PLC', 'Stake': 'Moon Survey', 'WonDays': 0},
            'Faction2': {'Name': 'Catun Resistance', 'Stake': 'Schunmann Cultivation Holdings', 'WonDays': 0},
            'Status': 'pending',
            'WarType': 'civilwar'
        }],
        SystemFaction={'FactionState': 'Expansion', 'Name': 'Caballeros de Sion'},
        """
        msg = eddn_model.message
        government = getattr(msg, "SystemGovernment", None)
        primary_economy = getattr(msg, "SystemEconomy", None)
        secondary_economy = getattr(msg, "SystemSecondEconomy", None)
        security = getattr(msg, "SystemSecurity", None)

        starpos = tuple(msg.StarPos)
        if len(starpos) != 3:
            logger.warning(f"Got a malformed StarPos value! '{msg.StarPos}' - '{pformat(msg)}'")
            raise ValueError(f"Malformed StarPos! '{msg.StarPos}'")

        d = {
            "allegiance": getattr(msg, "SystemAllegiance", None),
            "controlling_faction_id": controlling_faction_id,
            "x": starpos[0],
            "y": starpos[1],
            "z": starpos[2],
            "coords": SystemsDB.starpos_to_wkbelement(starpos),
            "date": msg.timestamp,
            "government": get_symbol_by_eddn_name(cast(str, government)) if government is not None else None,
            # "id64": msg.SystemAddress, # Never update id64?
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
            "power_conflict_progress": [
                SystemsDB.power_conflict_progress_to_dict_from_spansh(participant)
                for participant in getattr(msg, "power_conflict_progress", None) or []
            ],
            "power_state": getattr(msg, "PowerplayState", None),
            "power_state_control_progress": getattr(msg, "PowerplayStateControlProgress", None),
            "power_state_reinforcement": getattr(msg, "PowerplayStateReinforcement", None),
            "power_state_undermining": getattr(msg, "PowerplayStateUndermining", None),
            "powers": getattr(msg, "Powers", None),
            # "thargoid_war": (
            #   spansh_system.thargoid_war.to_sqlalchemy_dict()
            #   if spansh_system.thargoid_war is not None else None
            # ),
            "controlling_power_updated_at": msg.timestamp,
            "power_state_updated_at": msg.timestamp,
            "powers_updated_at": msg.timestamp,
        }

        # Filter out any Nones from the payload
        rtn = {k: v for k, v in d.items() if v is not None}

        # Add back Nones that logically should "clear out" any fields.
        # This is relevant when a system might go back and forth between Unoccupied and an Exploited+ state, where
        # fields like power_state_undermining and power_state_reinforcement need to be cleared out if the system reverts
        # back to Unoccupied

        power_state = rtn.get("power_state", None)
        if power_state == "Unoccupied":
            rtn["controlling_power"] = None
            rtn["power_state_control_progress"] = None
            rtn["power_state_reinforcement"] = None
            rtn["power_state_undermining"] = None
        elif power_state in ["Exploited", "Fortified", "Stronghold"]:
            rtn["power_conflict_progress"] = []

        return rtn

    def __repr__(self) -> str:
        return f"<SystemsDB(id={self.id}, name={self.name!r})>"
