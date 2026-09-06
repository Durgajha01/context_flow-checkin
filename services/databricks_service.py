"""Local-first storage with an optional, privacy-safe Databricks SQL sink."""
import json, re
from services.privacy_service import sanitize_checkpoint
from utils.config import DATA_FILE, databricks_config
EMPTY = {"projects": [], "checkpoints": [], "code_changes": [], "graph_impact": [], "events": [], "analysis": []}
_last_remote_error = None
def _load():
    if not DATA_FILE.exists(): return {k: list(v) for k,v in EMPTY.items()}
    try: return {**EMPTY, **json.loads(DATA_FILE.read_text(encoding="utf-8"))}
    except (json.JSONDecodeError, OSError): return {k: list(v) for k,v in EMPTY.items()}
def _save(data): DATA_FILE.parent.mkdir(parents=True, exist_ok=True); DATA_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
def _identifier(value):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value or ""): raise ValueError("Databricks catalog/schema must be a simple identifier.")
    return value
def _write_remote(kind, record):
    """Best-effort sink: a Databricks outage never breaks local CheckIN."""
    global _last_remote_error
    config=databricks_config()
    if not config: return
    try:
        from databricks import sql
        catalog,schema=_identifier(config["catalog"]),_identifier(config["schema"]); table=f"{catalog}.{schema}.checkin_records"
        with sql.connect(server_hostname=config["hostname"],http_path=config["http_path"],access_token=config["token"]) as conn:
            with conn.cursor() as cur:
                cur.execute(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
                cur.execute(f"CREATE TABLE IF NOT EXISTS {table} (record_type STRING, record_id STRING, project_id STRING, checkpoint_id STRING, recorded_at STRING, payload_json STRING)")
                cur.execute(f"INSERT INTO {table} VALUES (?, ?, ?, ?, ?, ?)",(kind,record.get("event_id") or record.get("analysis_id") or record.get("project_id") or record.get("checkpoint_id"),record.get("project_id"),record.get("checkpoint_id"),record.get("timestamp"),json.dumps(record)))
        _last_remote_error=None
    except Exception as exc: _last_remote_error=str(exc)
def storage_status(): return {"databricks_configured":bool(databricks_config()),"last_remote_error":_last_remote_error}
def query_projects(): return _load()["projects"]
def store_project(project):
    data=_load(); data["projects"]=[x for x in data["projects"] if x["project_id"] != project["project_id"]]+[project]; _save(data); _write_remote("project",project)
def store_event(event, checkpoint, changes, impacts):
    checkpoint=sanitize_checkpoint(checkpoint)
    data=_load(); pid,cid=event["project_id"],event["checkpoint_id"]
    data["events"]=[x for x in data["events"] if x.get("event_id") != event["event_id"]]+[event]
    data["checkpoints"]=[x for x in data["checkpoints"] if x.get("checkpoint_id") != checkpoint["checkpoint_id"]]+[checkpoint]
    data["code_changes"]=[x for x in data["code_changes"] if not(x["project_id"]==pid and x["checkpoint_id"]==cid)]+changes
    data["graph_impact"]=[x for x in data["graph_impact"] if not(x["project_id"]==pid and x["checkpoint_id"]==cid)]+impacts; _save(data)
    for kind,record in [("event",event),("checkpoint",checkpoint)]+[("code_change",x) for x in changes]+[("graph_impact",x) for x in impacts]: _write_remote(kind,record)
def store_analysis(analysis):
    data=_load(); data["analysis"]=[x for x in data["analysis"] if x["analysis_id"] != analysis["analysis_id"]]+[analysis]; _save(data); _write_remote("analysis",analysis)
def project_rows(name, project_id): return [x for x in _load()[name] if x.get("project_id")==project_id]
def latest_analysis(project_id):
    rows=project_rows("analysis",project_id); return sorted(rows,key=lambda x:x.get("timestamp",""))[-1] if rows else None
def latest_event(project_id):
    rows=project_rows("events",project_id); return sorted(rows,key=lambda x:x.get("timestamp",""))[-1] if rows else None
