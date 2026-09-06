import os
from pathlib import Path
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(): return False
load_dotenv()
ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "checkin_local.json"
DEMO_MODE = os.getenv("CHECKIN_DEMO_MODE", "true").lower() == "true"
def has_databricks_config():
    return bool(os.getenv("DATABRICKS_SERVER_HOSTNAME") and os.getenv("DATABRICKS_HTTP_PATH") and os.getenv("DATABRICKS_ACCESS_TOKEN"))
def databricks_config():
    if not has_databricks_config(): return None
    return {"hostname": os.environ["DATABRICKS_SERVER_HOSTNAME"], "http_path": os.environ["DATABRICKS_HTTP_PATH"], "token": os.environ["DATABRICKS_ACCESS_TOKEN"], "catalog": os.getenv("DATABRICKS_CATALOG", "main"), "schema": os.getenv("DATABRICKS_SCHEMA", "checkin")}
