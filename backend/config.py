import os
import json
import re
import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)


def _load_dotenv(path: str = "") -> None:
    """Load .env file into os.environ if not already set."""
    if not path:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r"^\s*([^#=]+)=(.*)\s*$", line)
            if m:
                key = m.group(1).strip()
                val = m.group(2).strip()
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                if val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                if key not in os.environ:
                    os.environ[key] = val


# Auto-load .env on import
_load_dotenv()


@dataclass
class MT5Instance:
    name: str
    path: str
    login: int
    password: str
    server: str


@dataclass
class Config:
    supabase_url: str
    supabase_service_key: str
    supabase_anon_key: str
    mt5_instances: List[MT5Instance] = field(default_factory=list)
    scan_interval_s: int = 1800
    dry_run: bool = False
    batch_size: int = 500
    history_days: int = 90
    webhook_host: str = "0.0.0.0"
    webhook_port: int = 8450
    webhook_secret: str = ""
    log_dir: str = ""
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Config":
        cfg = cls(
            supabase_url=os.environ.get("SUPABASE_URL", "http://localhost:8000"),
            supabase_service_key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""),
            supabase_anon_key=os.environ.get("SUPABASE_ANON_KEY", ""),
            webhook_secret=os.environ.get("WEBHOOK_SECRET", ""),
            scan_interval_s=int(os.environ.get("SCAN_INTERVAL_S", "1800")),
            dry_run=os.environ.get("DRY_RUN", "0") == "1",
            batch_size=int(os.environ.get("BATCH_SIZE", "500")),
            history_days=int(os.environ.get("HISTORY_DAYS", "90")),
            webhook_host=os.environ.get("WEBHOOK_HOST", "0.0.0.0"),
            webhook_port=int(os.environ.get("WEBHOOK_PORT", "8450")),
            log_dir=os.environ.get("LOG_DIR", os.path.join(os.path.dirname(__file__), "logs")),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
        )

        raw = os.environ.get("MT5_INSTANCES", "")
        if raw:
            try:
                for item in json.loads(raw):
                    cfg.mt5_instances.append(MT5Instance(
                        name=item["name"],
                        path=item["path"],
                        login=item.get("login", 0),
                        password=item.get("password", ""),
                        server=item.get("server", ""),
                    ))
            except (json.JSONDecodeError, KeyError) as exc:
                logger.error("MT5_INSTANCES parse error: %s", exc)
        else:
            cfg.mt5_instances = [
                MT5Instance("instance1", r"C:\Program Files\MetaTrader 5 IC Markets EU\terminal64.exe", 0, "", ""),
                MT5Instance("instance2", r"C:\MT5_Portable\Demo1\terminal64.exe", 0, "", ""),
            ]

        return cfg

    def instance_by_name(self, name: str):
        for inst in self.mt5_instances:
            if inst.name == name:
                return inst
        return None
