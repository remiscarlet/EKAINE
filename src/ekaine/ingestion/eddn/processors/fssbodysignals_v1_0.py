from typing import cast

from sqlalchemy.orm import Session

from ekaine.common.logging import get_logger
from ekaine.postgresql.adapter import SystemsAdapter
from gen.eddn_models import fssbodysignals_v1_0

logger = get_logger(__name__)


def process_model(session: Session, model: fssbodysignals_v1_0.Model) -> None:
    """
    Process fssbodysignals-v1.0 EDDN messages

    Updates:
    - ???

    """
    system_name = cast(str, model.message.StarSystem)
    try:
        with SystemsAdapter(session) as adapter:
            system = adapter.get_system(system_name)
    except ValueError:
        # We currently only track systems with population > 0, so plenty of systems won't be found.
        logger.debug(f"Encountered system we didn't know about! '{system_name}'")
        return

    logger.info(system)
    logger.info(model.message)
