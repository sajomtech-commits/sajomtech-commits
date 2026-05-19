import os
import time
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple

import MetaTrader5 as mt5
import requests

from config import Config, MT5Instance

logger = logging.getLogger("mt5_sync.scanner")


class SupabaseClient:
    def __init__(self, config: Config):
        self.url = config.supabase_url.rstrip("/")
        key = config.supabase_service_key or config.supabase_anon_key
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        }

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.url}/rest/v1/{path.lstrip('/')}"
        h = {**self.headers}
        h.update(kwargs.pop("headers", {}))
        resp = requests.request(method, url, headers=h, timeout=30, **kwargs)
        if resp.status_code >= 400:
            logger.error("Supabase %s %s -> %s: %s", method, path, resp.status_code, resp.text[:200])
        return resp

    def upsert_account(self, data: dict) -> Optional[int]:
        if not data.get("login"):
            return None
        payload = {
            "instance_name": data["instance_name"],
            "instance_path": data.get("instance_path", ""),
            "login": data["login"],
            "server": data.get("server", ""),
            "account_name": data.get("account_name", ""),
            "balance": data.get("balance", 0),
            "equity": data.get("equity", 0),
            "margin": data.get("margin", 0),
            "margin_free": data.get("margin_free", 0),
            "leverage": data.get("leverage", 0),
            "currency": data.get("currency", "USD"),
            "is_active": True,
            "last_sync_at": datetime.now(timezone.utc).isoformat(),
        }
        resp = self._request(
            "POST",
            "mt5_accounts",
            params={"on_conflict": "instance_name"},
            json=payload,
            headers={"Prefer": "resolution=merge-duplicates,return=representation"},
        )
        if resp.status_code in (200, 201):
            rows = resp.json()
            if isinstance(rows, list) and rows:
                return rows[0].get("id")
            if isinstance(rows, dict):
                return rows.get("id")
        return None

    def upsert_trades(self, trades: List[dict], account_id: int) -> int:
        if not trades:
            return 0
        count = 0
        for i in range(0, len(trades), 500):
            batch = trades[i:i + 500]
            for t in batch:
                t["account_id"] = account_id
            resp = self._request(
                "POST",
                "trades",
                params={"on_conflict": "account_id,ticket"},
                json=batch,
                headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
            )
            if resp.status_code in (200, 201, 204):
                count += len(batch)
            else:
                logger.error("Batch upsert fail at %d: %s", i, resp.text[:200])
        return count

    def close_stale_positions(self, account_id: int, active_tickets: List[int]) -> int:
        if not active_tickets:
            resp = self._request(
                "PATCH",
                "trades",
                params={"account_id": f"eq.{account_id}", "is_open": "eq.true"},
                json={"is_open": False, "close_time": datetime.now(timezone.utc).isoformat()},
            )
            logger.info("Closed all open trades for account %d", account_id)
            return 0

        total = 0
        for i in range(0, len(active_tickets), 500):
            batch = active_tickets[i:i + 500]
            tickets_str = ",".join(str(t) for t in batch)

            resp = self._request(
                "GET",
                "trades",
                params={
                    "account_id": f"eq.{account_id}",
                    "is_open": "eq.true",
                    "select": "ticket",
                    "ticket": f"not.in.({tickets_str})",
                    "limit": "1000",
                },
            )
            if resp.status_code != 200:
                continue
            to_close = resp.json()
            if not to_close:
                continue
            close_ids = ",".join(str(t["ticket"]) for t in to_close)
            close_resp = self._request(
                "PATCH",
                "trades",
                params={"account_id": f"eq.{account_id}", "ticket": f"in.({close_ids})"},
                json={"is_open": False, "close_time": datetime.now(timezone.utc).isoformat()},
            )
            if close_resp.status_code in (200, 204):
                total += len(to_close)
                logger.info("Closed %d stale positions for account %d", len(to_close), account_id)

        return total

    def log_sync(self, instance_name: str, account_id: Optional[int], status: str,
                 trades_found: int, trades_upserted: int, duration_ms: int,
                 error_message: str = "") -> None:
        self._request(
            "POST",
            "sync_log",
            json={
                "instance_name": instance_name,
                "account_id": account_id,
                "status": status,
                "trades_found": trades_found,
                "trades_upserted": trades_upserted,
                "duration_ms": duration_ms,
                "error_message": error_message,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
        )


class MT5Scanner:
    def __init__(self, config: Config, instance: MT5Instance):
        self.config = config
        self.instance = instance
        self._initialized = False

    def initialize(self) -> bool:
        mt5.shutdown()
        path = self.instance.path
        logger.info("Init MT5: %s (%s)", self.instance.name, path)
        if not os.path.isfile(path):
            logger.error("Not found: %s", path)
            return False
        if self.config.dry_run:
            self._initialized = True
            return True
        ok = mt5.initialize(
            path=path,
            login=self.instance.login or None,
            password=self.instance.password or None,
            server=self.instance.server or None,
        )
        self._initialized = ok
        if not ok:
            logger.error("MT5 init fail %s: %s", self.instance.name, mt5.last_error())
        return ok

    def shutdown(self) -> None:
        if self._initialized and not self.config.dry_run:
            mt5.shutdown()
            self._initialized = False

    def get_account_info(self) -> Optional[dict]:
        if self.config.dry_run:
            return {
                "instance_name": self.instance.name,
                "instance_path": self.instance.path,
                "login": self.instance.login,
                "server": self.instance.server,
                "account_name": f"[DRY] {self.instance.name}",
                "balance": 0, "equity": 0, "margin": 0,
                "margin_free": 0, "leverage": 0, "currency": "USD",
            }
        info = mt5.account_info()
        if info is None:
            logger.warning("No account info for %s", self.instance.name)
            return None
        return {
            "instance_name": self.instance.name,
            "instance_path": self.instance.path,
            "login": info.login,
            "server": info.server or "",
            "account_name": info.name or "",
            "balance": info.balance or 0,
            "equity": info.equity or 0,
            "margin": info.margin or 0,
            "margin_free": info.margin_free or 0,
            "leverage": info.leverage or 0,
            "currency": info.currency or "USD",
        }

    def get_open_positions(self) -> List[dict]:
        if self.config.dry_run:
            return []
        positions = mt5.positions_get()
        if positions is None:
            return []
        return [self._position_to_dict(p) for p in positions]

    def get_closed_trades(self, days_back: int = 90) -> List[dict]:
        if self.config.dry_run:
            return []

        now = datetime.now(timezone.utc)
        from_dt = now - timedelta(days=days_back)
        deals = mt5.history_deals_get(from_dt, now + timedelta(days=1))
        if deals is None:
            logger.warning("No history deals for %s", self.instance.name)
            return []

        by_pos = defaultdict(list)
        for d in deals:
            if d.position_id > 0:
                by_pos[d.position_id].append(d)

        open_pids = set()
        positions = mt5.positions_get()
        if positions:
            open_pids = {p.ticket for p in positions}

        result = []
        for pos_id, pos_deals in by_pos.items():
            if pos_id in open_pids:
                continue

            entry_in = None
            entry_out = None
            for d in pos_deals:
                if d.entry == 0:
                    entry_in = d
                elif d.entry == 1:
                    if entry_out is None or d.time > entry_out.time:
                        entry_out = d

            if entry_out is None:
                continue

            src = entry_in or entry_out
            result.append({
                "ticket": pos_id,
                "symbol": src.symbol,
                "type": src.type,
                "volume": src.volume,
                "open_time": datetime.fromtimestamp(
                    (entry_in or entry_out).time, tz=timezone.utc
                ).isoformat(),
                "close_time": datetime.fromtimestamp(
                    entry_out.time, tz=timezone.utc
                ).isoformat(),
                "open_price": (entry_in or entry_out).price,
                "close_price": entry_out.price,
                "sl": 0, "tp": 0,
                "profit": entry_out.profit,
                "swap": entry_out.swap or 0,
                "commission": entry_out.commission or 0,
                "magic": entry_out.magic,
                "comment": entry_out.comment or "",
                "is_open": False,
            })

        return result

    def get_all_trades(self, days_back: int = 90) -> Tuple[List[dict], List[int]]:
        open_positions = self.get_open_positions()
        closed = self.get_closed_trades(days_back=days_back)
        open_tickets = [t["ticket"] for t in open_positions]

        merged = {t["ticket"]: t for t in open_positions}
        for t in closed:
            if t["ticket"] not in merged:
                merged[t["ticket"]] = t

        return list(merged.values()), open_tickets

    @staticmethod
    def _position_to_dict(pos) -> dict:
        return {
            "ticket": pos.ticket,
            "symbol": pos.symbol,
            "type": pos.type,
            "volume": pos.volume,
            "open_time": datetime.fromtimestamp(pos.time, tz=timezone.utc).isoformat(),
            "close_time": None,
            "open_price": pos.price_open,
            "close_price": None,
            "sl": pos.sl or 0,
            "tp": pos.tp or 0,
            "profit": pos.profit,
            "swap": pos.swap or 0,
            "commission": pos.commission or 0,
            "magic": pos.magic,
            "comment": pos.comment or "",
            "is_open": True,
        }


def scan_instance(config: Config, instance: MT5Instance) -> dict:
    start = time.time()
    result = {"instance": instance.name, "status": "error",
              "trades_found": 0, "trades_upserted": 0, "error": ""}

    supabase = SupabaseClient(config)
    scanner = MT5Scanner(config, instance)

    try:
        if not scanner.initialize():
            result["error"] = f"MT5 init fail"
            supabase.log_sync(instance.name, None, "error", 0, 0,
                              int((time.time() - start) * 1000), result["error"])
            return result

        account_info = scanner.get_account_info()
        if not account_info:
            result["error"] = "No account info"
            supabase.log_sync(instance.name, None, "error", 0, 0,
                              int((time.time() - start) * 1000), result["error"])
            return result

        account_id = supabase.upsert_account(account_info)
        if not account_id and not config.dry_run:
            result["error"] = "Account upsert fail"
            supabase.log_sync(instance.name, None, "error", 0, 0,
                              int((time.time() - start) * 1000), result["error"])
            return result

        all_trades, open_tickets = scanner.get_all_trades(days_back=config.history_days)
        result["trades_found"] = len(all_trades)

        if config.dry_run:
            result["status"] = "success"
            result["trades_upserted"] = len(all_trades)
            return result

        upserted = supabase.upsert_trades(all_trades, account_id)
        closed = supabase.close_stale_positions(account_id, open_tickets)

        result["trades_upserted"] = upserted
        result["status"] = "success"

        duration = int((time.time() - start) * 1000)
        supabase.log_sync(instance.name, account_id, "success",
                          len(all_trades), upserted, duration)

        logger.info("Sync %s: %d upserted, %d closed, %dms",
                    instance.name, upserted, closed, duration)

    except Exception as exc:
        logger.exception("Error scanning %s", instance.name)
        result["error"] = str(exc)
        supabase.log_sync(instance.name, None, "error", 0, 0,
                          int((time.time() - start) * 1000), str(exc))
    finally:
        scanner.shutdown()

    return result
