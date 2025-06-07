from typing import cast

from sqlalchemy.orm import Session

from ekaine.common.logging import get_logger
from ekaine.postgresql.adapter import SystemsAdapter
from ekaine.postgresql.timeseries import RawSignalsTimeseries
from ekaine.postgresql.utils import upsert_all
from gen.eddn_models import fsssignaldiscovered_v1_0

logger = get_logger(__name__)


def process_model(session: Session, model: fsssignaldiscovered_v1_0.Model) -> None:
    """
    Process fsssignaldiscovered-v1.0 EDDN messages

    Updates:
    - RawSignalsTimeseries

    """
    system_name = cast(str, model.message.StarSystem)
    try:
        system = SystemsAdapter().get_system(system_name)
    except ValueError:
        # We currently only track systems with population > 0, so plenty of systems won't be found.
        logger.debug(f"Encountered system we didn't know about! '{system_name}'")
        return

    signal_timeseries_dicts = RawSignalsTimeseries.to_dicts_from_fsssignaldiscovered_v1_0(model, system.id)
    # logger.info(pformat(signal_timeseries_dicts))

    upsert_all(session, RawSignalsTimeseries, signal_timeseries_dicts)
    logger.info("[Signals Timeseries Updated] " f"{system_name} - {len(signal_timeseries_dicts)} Signals")
