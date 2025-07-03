# Data comes from Spansh and EDSM dumps
import os
from pathlib import Path

PWD = Path.cwd()
REPO_ROOT = Path(__file__).parent.parent.parent.parent
REL_ROOT_PATH = PWD.relative_to(REPO_ROOT)

CONTAINER_NAME = os.getenv("CONTAINER_NAME", "default")
LOG_DIR = REL_ROOT_PATH / "logs" / CONTAINER_NAME
DEFAULT_LOG_LEVEL = "INFO"

# Data dir
DATA_DIR = REL_ROOT_PATH / "data"

DB_DATA_PATH = DATA_DIR / "processed_data.db"
# GALAXY_POPULATED_JSON = DATA_DIR / "galaxy_populated.first100.json"
# GALAXY_POPULATED_JSON = DATA_DIR / "galaxy_populated.truncated.json"
GALAXY_POPULATED_JSON = DATA_DIR / "galaxy_populated.json"
GALAXY_POPULATED_JSON_GZ = DATA_DIR / "galaxy_populated.json.gz"
POWERPLAY_SYSTEMS = DATA_DIR / "powerPlay.json"

GALAXY_POPULATED_JSON_URL = "https://downloads.spansh.co.uk/galaxy_populated.json.gz"

# Metadata Dir
METADATA_DIR = REL_ROOT_PATH / "metadata"
METADATA_SCHEMAS_DIR = METADATA_DIR / "schemas"
ENUMS_SCHEMA = METADATA_SCHEMAS_DIR / "enums.schema.json"
COMMODITIES_SCHEMA = METADATA_SCHEMAS_DIR / "commodities.schema.json"
COMMODITIES_YAML_FMT = "commodities.*.yaml"
STRINGS_SCHEMA = METADATA_SCHEMAS_DIR / "strings.schema.json"
STRINGS_YAML_FMT = "strings.*.yaml"

# EDDN
GEN_DIR = REL_ROOT_PATH / "src" / "gen"  # Hehe...
EDDN_SCHEMAS_DIR = DATA_DIR / "eddn" / "schemas"
EDDN_SCHEMA_MAPPING_FILE = GEN_DIR / "eddn_schema_to_model_mapping.json"

# Others
SQL_DIR = REL_ROOT_PATH / "src" / "ekaine" / "postgresql" / "sql"

SESSION_COOKIE_NAME = "ekaine_session"
SESSION_TTL_SECONDS = 3600

GRAFANA_URL = os.getenv("GRAFANA_URL", None)
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", None)
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", None)
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", None)
SESSION_SECRET = os.getenv("COOKIE_SECRET", None)
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", None)
REDIS_DSN = os.getenv("REDIS_DSN", None)
SESSION_SECRET = os.getenv("COOKIE_SECRET", None)
ENVIRONMENT_TYPE = os.getenv("ENVIRONMENT_TYPE", None)

# These should get overwritten by docker-compose.yaml environment configs.
# Default values are used when running outside a docker context, ie make targets
EKAINE_DATABASE_URL = os.getenv("EKAINE_DATABASE_URL", "postgresql://ekaine:ekaine_pw@localhost:5432/ekaine")
GRAFANA_DATABASE_URL = os.getenv("GRAFANA_DATABASE_URL", "postgresql://ekaine:ekaine_pw@localhost:5432/grafana_meta")

DEV_GUILD_ID = 604536071891714069
