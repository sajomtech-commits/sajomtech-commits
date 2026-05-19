#!/usr/bin/env python3
"""
FastAPI webhook server.

POST /webhook/scan   — trigger scan
POST /webhook/mt5    — receive trade push from EA
GET  /health
GET  /status
"""

import time
import logging
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from config import Config
from logger import setup_logging
from scan_to_supabase import scan_instance, SupabaseClient

logger = logging.getLogger("mt5_sync.webhook")
config = Config.from_env()


# ── Models ──

class ScanRequest(BaseModel):
    instance: Optional[str] = None


class TradePush(BaseModel):
    ticket: int
    symbol: str
    type: int
    volume: float
    open_time: str
    open_price: float
    close_time: Optional[str] = None
    close_price: Optional[float] = None
    profit: Optional[float] = None
    swap: float = 0
    commission: float = 0
    sl: float = 0
    tp: float = 0
    magic: int = 0
    comment: str = ""


class AccountPush(BaseModel):
    instance: str
    login: int
    server: str = ""
    account_name: str = ""
    balance: float = 0
    equity: float = 0
    margin: float = 0
    margin_free: float = 0
    leverage: int = 0
    currency: str = "USD"


class MT5PushPayload(BaseModel):
    account: AccountPush
    trades: List[TradePush] = []


# ── App ──

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(log_dir=config.log_dir, level=config.log_level)
    logger.info("Webhook on %s:%d", config.webhook_host, config.webhook_port)
    yield
    logger.info("Shutdown")


app = FastAPI(title="MT5 Sync Webhook", version="1.0.0", lifespan=lifespan)


def verify(authorization: Optional[str] = None) -> None:
    if not config.webhook_secret:
        return
    if not authorization:
        raise HTTPException(401, "Missing Authorization")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token != config.webhook_secret:
        raise HTTPException(403, "Invalid secret")


@app.get("/health")
async def health():
    return {"status": "ok", "ts": time.time()}


@app.get("/status")
async def get_status(authorization: Optional[str] = Header(None)):
    verify(authorization)
    client = SupabaseClient(config)
    resp = client._request("GET", "v_last_sync")
    if resp.status_code == 200:
        return resp.json()
    return {"error": "unavailable"}


@app.post("/webhook/scan")
async def webhook_scan(body: ScanRequest, authorization: Optional[str] = Header(None)):
    verify(authorization)
    logger.info("Scan triggered via webhook (instance=%s)", body.instance)
    instances = config.mt5_instances
    if body.instance:
        inst = config.instance_by_name(body.instance)
        instances = [inst] if inst else []
        if not instances:
            raise HTTPException(404, f"Instance '{body.instance}' not found")
    results = [scan_instance(config, i) for i in instances]
    return {"triggered": True, "results": results}


@app.post("/webhook/mt5")
async def webhook_mt5(
    payload: MT5PushPayload,
    authorization: Optional[str] = Header(None),
):
    verify(authorization)
    client = SupabaseClient(config)
    ad = payload.account.model_dump()
    ad["instance_name"] = ad.pop("instance")
    ad["instance_path"] = ""
    account_id = client.upsert_account(ad)
    if not account_id:
        raise HTTPException(500, "Account upsert failed")
    trade_dicts = []
    for t in payload.trades:
        d = t.model_dump()
        d["is_open"] = d["close_time"] is None
        trade_dicts.append(d)
    upserted = client.upsert_trades(trade_dicts, account_id) if trade_dicts else 0
    return {"received": True, "account_id": account_id, "trades_upserted": upserted}


def main():
    import uvicorn
    uvicorn.run(
        "webhook_server:app",
        host=config.webhook_host,
        port=config.webhook_port,
        log_level=config.log_level.lower(),
    )


if __name__ == "__main__":
    main()
