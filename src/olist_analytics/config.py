import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
SETTINGS_PATH = CONFIG_DIR / "settings.yaml"

with open(SETTINGS_PATH, "r") as f:
    settings = yaml.safe_load(f)

# Override paths from environment
if "OLIST_DATA_DIR" in os.environ:
    settings["paths"]["raw_dir"] = os.environ["OLIST_DATA_DIR"]

# Require DATABASE_URL
def get_db_url():
    url = os.getenv(settings["database"]["url_env"])
    if not url:
        raise ValueError(f"{settings['database']['url_env']} is not set")
    return url
