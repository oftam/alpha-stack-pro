"""
HUD Sync Module — מושך נתונים מ-Anti-Gravity HUD (SSOT)
===================================================
Bidirectional sync: MEDALLION Dashboard ↔ Anti-Gravity HUD PWA Backend
"""
import logging
import requests

logger = logging.getLogger(__name__)

HUD_API_URL = "https://quantum-ledger-pwa-phvapy257q-ew.a.run.app"


def fetch_hud_state(timeout: int = 10) -> dict | None:
    """מושך את מצב המערכת המלא מ-Anti-Gravity HUD Backend (/api/state)."""
    try:
        resp = requests.get(f"{HUD_API_URL}/api/state", timeout=timeout)
        resp.raise_for_status()
        state = resp.json()
        logger.info(f"✅ HUD sync OK — BTC=${state.get('price', 'N/A')}")
        return state
    except requests.RequestException as e:
        logger.warning(f"⚠️ HUD sync failed: {e}")
        return None


def push_medallion_to_hud(data: dict, timeout: int = 10) -> bool:
    """דוחף נתוני MEDALLION לתוך ה-HUD (POST /api/state)."""
    try:
        resp = requests.post(
            f"{HUD_API_URL}/api/state",
            json=data,
            timeout=timeout,
        )
        resp.raise_for_status()
        logger.info("✅ MEDALLION → HUD push success")
        return True
    except requests.RequestException as e:
        logger.warning(f"⚠️ HUD push failed: {e}")
        return False


def sync_bidirectional() -> dict | None:
    """
    סנכרון דו-כיווני: HUD → MEDALLION.
    מחזיר dict עם שדות ה-HUD הרלוונטיים, או None אם ה-HUD offline.
    """
    hud_state = fetch_hud_state()
    if not hud_state:
        return None

    return {
        "price":       hud_state.get("price"),
        "posterior":   hud_state.get("posterior"),
        "whale_score": hud_state.get("whale_score"),
        "fear_greed":  hud_state.get("fear_greed"),
        "regime":      hud_state.get("regime"),
        "gate_locked": hud_state.get("gate_locked"),
        "kelly":       hud_state.get("kelly"),
        "p10":         hud_state.get("p10"),
        "p50":         hud_state.get("p50"),
        "p90":         hud_state.get("p90"),
        "last_sync":   hud_state.get("last_sync"),
    }
