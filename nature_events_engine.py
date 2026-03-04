"""
╔══════════════════════════════════════════════════════════════╗
║  NATURE EVENTS ENGINE — Renaissance Medallion Protocol      ║
║  Module: nature_events_engine.py                            ║
║  Version: 1.0 · Elite v20 CRO                              ║
║  Purpose: Monitor natural disasters & climate events        ║
║           that impact crypto/commodities/macro markets      ║
╚══════════════════════════════════════════════════════════════╝

Jim Simons' Medallion Fund famously used weather data, satellite imagery,
and natural disaster feeds as alternative signals. This module brings
that capability to our system.

INTEGRATION:
    from nature_events_engine import NatureEventsEngine
    nature_engine = NatureEventsEngine()
    nature_engine.render_panel()
"""

import streamlit as st
import requests
import json
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

# ─────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────

@dataclass
class NatureEvent:
    """Single natural disaster / climate event"""
    event_type: str          # EARTHQUAKE, HURRICANE, FLOOD, VOLCANO, WILDFIRE, TSUNAMI, DROUGHT, EXTREME_HEAT
    severity: float          # 0-100
    location: str            # Region/Country
    lat: float = 0.0
    lon: float = 0.0
    magnitude: float = 0.0   # Richter for quakes, Category for hurricanes, etc.
    timestamp: str = ""
    source: str = ""
    description: str = ""
    market_impact_zone: str = ""  # MINING, ENERGY, SUPPLY_CHAIN, OIL, FINANCE_HUB, NUCLEAR

@dataclass
class NatureImpactScore:
    """Aggregated impact on markets from all active events"""
    total_score: float = 0.0        # 0-100 (0=calm, 100=catastrophic)
    btc_impact: float = 0.0         # -50 to +50 (negative=bearish, positive=bullish)
    gold_impact: float = 0.0
    oil_impact: float = 0.0
    chaos_contribution: float = 0.0  # Added to Chaos/Entropy
    active_events: int = 0
    critical_events: int = 0
    affected_zones: List[str] = field(default_factory=list)

# ─────────────────────────────────────────────
# IMPACT ZONES — What matters for markets
# ─────────────────────────────────────────────

CRITICAL_ZONES = {
    # BTC Mining Regions
    "Texas": {"type": "MINING", "btc_weight": 0.25, "description": "30% US hashrate"},
    "Kazakhstan": {"type": "MINING", "btc_weight": 0.15, "description": "Mining hub"},
    "Iceland": {"type": "MINING", "btc_weight": 0.05, "description": "Geothermal mining"},
    "Paraguay": {"type": "MINING", "btc_weight": 0.08, "description": "Hydro mining"},

    # Energy / Oil Regions
    "Persian Gulf": {"type": "OIL", "oil_weight": 0.40, "description": "Strait of Hormuz — 20% global oil"},
    "Gulf of Mexico": {"type": "OIL", "oil_weight": 0.15, "description": "US offshore production"},
    "North Sea": {"type": "OIL", "oil_weight": 0.10, "description": "European energy"},
    "Russia": {"type": "ENERGY", "oil_weight": 0.15, "description": "Gas + Oil supply"},

    # Supply Chain / Chip Manufacturing
    "Taiwan": {"type": "SUPPLY_CHAIN", "macro_weight": 0.30, "description": "TSMC — 90% advanced chips"},
    "Japan": {"type": "SUPPLY_CHAIN", "macro_weight": 0.15, "description": "Semiconductor + Auto"},
    "South Korea": {"type": "SUPPLY_CHAIN", "macro_weight": 0.10, "description": "Samsung + Memory chips"},

    # Financial Hubs
    "Hong Kong": {"type": "FINANCE_HUB", "btc_weight": 0.10, "description": "Asia crypto hub"},
    "Singapore": {"type": "FINANCE_HUB", "btc_weight": 0.05, "description": "Asia finance"},
    "Dubai": {"type": "FINANCE_HUB", "btc_weight": 0.08, "description": "Middle East crypto hub"},

    # Nuclear Risk Zones (Iran conflict specific)
    "Iran": {"type": "NUCLEAR", "oil_weight": 0.20, "chaos_weight": 0.40, "description": "Nuclear + Oil + Hormuz"},
    "Bushehr": {"type": "NUCLEAR", "chaos_weight": 0.50, "description": "Nuclear reactor — seismic zone"},
    "Natanz": {"type": "NUCLEAR", "chaos_weight": 0.45, "description": "Enrichment facility"},
}

# ─────────────────────────────────────────────
# EVENT TYPE WEIGHTS
# ─────────────────────────────────────────────

EVENT_WEIGHTS = {
    "EARTHQUAKE":    {"base_severity": 0.7, "decay_hours": 48, "gold_boost": 0.3},
    "TSUNAMI":       {"base_severity": 0.9, "decay_hours": 72, "gold_boost": 0.5},
    "HURRICANE":     {"base_severity": 0.6, "decay_hours": 96, "gold_boost": 0.2},
    "VOLCANO":       {"base_severity": 0.5, "decay_hours": 168, "gold_boost": 0.2},
    "FLOOD":         {"base_severity": 0.4, "decay_hours": 120, "gold_boost": 0.1},
    "WILDFIRE":      {"base_severity": 0.3, "decay_hours": 168, "gold_boost": 0.1},
    "EXTREME_HEAT":  {"base_severity": 0.3, "decay_hours": 336, "gold_boost": 0.05},
    "DROUGHT":       {"base_severity": 0.2, "decay_hours": 720, "gold_boost": 0.05},
    "NUCLEAR_INCIDENT": {"base_severity": 1.0, "decay_hours": 720, "gold_boost": 0.8},
    "SOLAR_STORM":   {"base_severity": 0.4, "decay_hours": 24, "gold_boost": 0.1},
}


class NatureEventsEngine:
    """
    Renaissance-grade Nature Events Monitor.
    Fetches real-time disaster data and calculates market impact.
    """

    def __init__(self):
        self.events: List[NatureEvent] = []
        self.impact = NatureImpactScore()
        self.last_fetch = None
        self.fetch_interval = 300  # 5 minutes

    # ─────────────────────────────────────────
    # DATA FETCHERS (Free Public APIs)
    # ─────────────────────────────────────────

    def fetch_earthquakes(self) -> List[NatureEvent]:
        """Fetch from USGS Earthquake API (free, no key needed)"""
        events = []
        try:
            url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for feature in data.get("features", [])[:10]:
                    props = feature["properties"]
                    coords = feature["geometry"]["coordinates"]
                    mag = props.get("mag", 0)

                    # Severity: mag 4.5=20, 6.0=50, 7.0=75, 8.0=95
                    severity = min(100, max(0, (mag - 4.0) * 25))

                    # Check if near critical zone
                    impact_zone = self._check_proximity(coords[1], coords[0])

                    events.append(NatureEvent(
                        event_type="EARTHQUAKE",
                        severity=severity,
                        location=props.get("place", "Unknown"),
                        lat=coords[1],
                        lon=coords[0],
                        magnitude=mag,
                        timestamp=datetime.fromtimestamp(
                            props.get("time", 0) / 1000, tz=timezone.utc
                        ).isoformat(),
                        source="USGS",
                        description=f"M{mag} — {props.get('place', '')}",
                        market_impact_zone=impact_zone
                    ))
        except Exception as e:
            pass  # Silent fail — system continues without nature data
        return events

    def fetch_nasa_events(self) -> List[NatureEvent]:
        """Fetch from NASA EONET (Earth Observatory Natural Event Tracker)"""
        events = []
        try:
            url = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=20"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for event in data.get("events", []):
                    cat = event.get("categories", [{}])[0].get("title", "").upper()
                    event_type = self._map_nasa_category(cat)
                    if not event_type:
                        continue

                    geo = event.get("geometry", [{}])
                    coords = geo[-1].get("coordinates", [0, 0]) if geo else [0, 0]

                    impact_zone = self._check_proximity(
                        coords[1] if len(coords) > 1 else 0,
                        coords[0] if len(coords) > 0 else 0
                    )

                    events.append(NatureEvent(
                        event_type=event_type,
                        severity=self._estimate_severity(event_type, event),
                        location=event.get("title", "Unknown"),
                        lat=coords[1] if len(coords) > 1 else 0,
                        lon=coords[0] if len(coords) > 0 else 0,
                        timestamp=geo[-1].get("date", "") if geo else "",
                        source="NASA_EONET",
                        description=event.get("title", ""),
                        market_impact_zone=impact_zone
                    ))
        except Exception:
            pass
        return events

    def fetch_gdacs_events(self) -> List[NatureEvent]:
        """Fetch from GDACS — Global Disaster Alert and Coordination System.
        Covers: EQ, TC (tropical cyclone), FL (flood), VO (volcano),
                DR (drought), WF (wildfire), TS (tsunami).
        Free, no API key. Alert levels: Green / Orange / Red.
        """
        events = []
        try:
            now = datetime.now(timezone.utc)
            from_date = (now - timedelta(days=2)).strftime("%Y-%m-%d")
            to_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
            url = (
                "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
                f"?eventlist=EQ,TC,FL,VO,DR,WF,TS"
                f"&fromdate={from_date}&todate={to_date}"
                f"&alertlevel=Green;Orange;Red"
            )
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                return events

            data = resp.json()
            gdacs_type_map = {
                "EQ": "EARTHQUAKE", "TC": "HURRICANE", "FL": "FLOOD",
                "VO": "VOLCANO", "DR": "DROUGHT", "WF": "WILDFIRE",
                "TS": "TSUNAMI",
            }
            alert_severity = {"Red": 85.0, "Orange": 60.0, "Green": 25.0}

            for feature in data.get("features", [])[:30]:
                props = feature.get("properties", {})
                coords = feature.get("geometry", {}).get("coordinates", [0, 0])

                etype_code = props.get("eventtype", "")
                event_type = gdacs_type_map.get(etype_code)
                if not event_type:
                    continue

                alert = props.get("alertlevel", "Green")
                sev_data = props.get("severitydata", {})
                mag = sev_data.get("severity", 0)

                # For earthquakes, use magnitude-based severity like USGS
                if event_type == "EARTHQUAKE" and mag > 0:
                    severity = min(100, max(0, (mag - 4.0) * 25))
                else:
                    severity = alert_severity.get(alert, 25.0)

                # For wildfires, boost severity by area (hectares)
                if event_type == "WILDFIRE" and mag > 10000:
                    severity = min(100, severity + 20)  # Large fire boost

                lat = coords[1] if len(coords) > 1 else 0
                lon = coords[0] if len(coords) > 0 else 0
                impact_zone = self._check_proximity(lat, lon)

                from_date_str = props.get("fromdate", "")
                try:
                    ts = datetime.fromisoformat(from_date_str.replace("Z", "+00:00")).isoformat()
                except Exception:
                    ts = from_date_str

                events.append(NatureEvent(
                    event_type=event_type,
                    severity=severity,
                    location=props.get("country", props.get("name", "Unknown")),
                    lat=lat,
                    lon=lon,
                    magnitude=mag if event_type == "EARTHQUAKE" else 0,
                    timestamp=ts,
                    source=f"GDACS ({alert.upper()})",
                    description=props.get("name", props.get("description", "")),
                    market_impact_zone=impact_zone
                ))
        except Exception:
            pass
        return events

    # ─────────────────────────────────────────
    # IMPACT CALCULATOR
    # ─────────────────────────────────────────

    def calculate_impact(self) -> NatureImpactScore:
        """Calculate aggregated market impact from all active events"""
        impact = NatureImpactScore()

        if not self.events:
            return impact

        btc_impact = 0.0
        gold_impact = 0.0
        oil_impact = 0.0
        chaos_add = 0.0
        zones = set()

        for event in self.events:
            weight = EVENT_WEIGHTS.get(event.event_type, {"base_severity": 0.3, "decay_hours": 48, "gold_boost": 0.1})

            # Time decay
            try:
                event_time = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
                hours_ago = (datetime.now(timezone.utc) - event_time).total_seconds() / 3600
                decay = math.exp(-0.693 * hours_ago / weight["decay_hours"])  # Half-life decay
            except:
                decay = 0.5

            effective_severity = event.severity * decay * weight["base_severity"]

            # Zone-specific impacts
            zone_info = None
            for zone_name, zone_data in CRITICAL_ZONES.items():
                if zone_name.lower() in event.location.lower() or zone_name.lower() in event.market_impact_zone.lower():
                    zone_info = zone_data
                    zones.add(zone_data["type"])
                    break

            if zone_info:
                btc_impact -= effective_severity * zone_info.get("btc_weight", 0) * 0.5
                oil_impact += effective_severity * zone_info.get("oil_weight", 0) * 0.5
                chaos_add += effective_severity * zone_info.get("chaos_weight", 0) * 0.01
            else:
                # Generic impact
                btc_impact -= effective_severity * 0.02
                oil_impact += effective_severity * 0.01

            # Gold always benefits from disasters (safe haven)
            gold_impact += effective_severity * weight["gold_boost"] * decay

            if effective_severity > 60:
                impact.critical_events += 1

        impact.total_score = min(100, sum(e.severity for e in self.events) / max(1, len(self.events)))
        impact.btc_impact = max(-50, min(50, btc_impact))
        impact.gold_impact = max(-50, min(50, gold_impact))
        impact.oil_impact = max(-50, min(50, oil_impact))
        impact.chaos_contribution = min(0.3, chaos_add)
        impact.active_events = len(self.events)
        impact.affected_zones = list(zones)

        self.impact = impact
        return impact

    # ─────────────────────────────────────────
    # REFRESH
    # ─────────────────────────────────────────

    def refresh(self):
        """Fetch all sources and recalculate.
        Merges USGS + NASA + GDACS with smart deduplication:
        - USGS earthquakes are authoritative (higher detail)
        - GDACS earthquakes are skipped if same location already from USGS
        - GDACS adds floods, cyclones, wildfires, tsunamis, droughts, volcanoes
        """
        now = datetime.now(timezone.utc)
        if self.last_fetch and (now - self.last_fetch).total_seconds() < self.fetch_interval:
            return  # Too soon

        # Fetch from all 3 sources
        usgs_events = self.fetch_earthquakes()
        nasa_events = self.fetch_nasa_events()
        gdacs_events = self.fetch_gdacs_events()

        # Build USGS location fingerprints for dedup
        usgs_locs = set()
        for e in usgs_events:
            # Fingerprint: round coords to ~10km grid
            usgs_locs.add((round(e.lat, 1), round(e.lon, 1), round(e.magnitude, 0)))

        # Filter GDACS: skip earthquakes already in USGS, keep everything else
        deduped_gdacs = []
        for e in gdacs_events:
            if e.event_type == "EARTHQUAKE":
                fp = (round(e.lat, 1), round(e.lon, 1), round(e.magnitude, 0))
                if fp in usgs_locs:
                    continue  # Already have from USGS
            deduped_gdacs.append(e)

        self.events = usgs_events + nasa_events + deduped_gdacs

        # Sort by severity (highest first)
        self.events.sort(key=lambda e: e.severity, reverse=True)

        self.calculate_impact()
        self.last_fetch = now

    # ─────────────────────────────────────────
    # STREAMLIT PANEL
    # ─────────────────────────────────────────

    def render_panel(self):
        """Render the Nature Events panel in Streamlit dashboard"""
        self.refresh()

        st.markdown("---")
        st.markdown("### 🌍 Nature Events Engine — Renaissance Protocol")
        st.caption("Satellite + Seismic + Climate feeds | Jim Simons Methodology")

        # ── Impact Summary ──
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            color = "🟢" if self.impact.total_score < 20 else "🟡" if self.impact.total_score < 50 else "🔴"
            st.metric("Nature Threat", f"{color} {self.impact.total_score:.0f}/100")

        with col2:
            st.metric("Active Events", f"{self.impact.active_events}",
                      delta=f"{self.impact.critical_events} critical" if self.impact.critical_events > 0 else "0 critical")

        with col3:
            btc_arrow = "↓" if self.impact.btc_impact < 0 else "↑" if self.impact.btc_impact > 0 else "—"
            st.metric("BTC Impact", f"{btc_arrow} {self.impact.btc_impact:+.1f}%")

        with col4:
            st.metric("Chaos Add", f"+{self.impact.chaos_contribution:.3f}",
                      delta="Added to Entropy" if self.impact.chaos_contribution > 0 else "None")

        # ── Affected Zones ──
        if self.impact.affected_zones:
            zone_tags = " | ".join([f"⚠️ {z}" for z in self.impact.affected_zones])
            st.warning(f"**Affected Market Zones:** {zone_tags}")

        # ── Safe Haven Flow ──
        col_g, col_o = st.columns(2)
        with col_g:
            gold_bar = min(100, max(0, self.impact.gold_impact * 2 + 50))
            st.progress(gold_bar / 100, text=f"🥇 Gold Safe Haven Flow: {self.impact.gold_impact:+.1f}%")
        with col_o:
            oil_bar = min(100, max(0, self.impact.oil_impact * 2 + 50))
            st.progress(oil_bar / 100, text=f"🛢️ Oil Supply Risk: {self.impact.oil_impact:+.1f}%")

        # ── Event Feed ──
        if self.events:
            st.markdown("#### 📡 Live Event Feed")
            for i, event in enumerate(self.events[:8]):
                icon = self._get_event_icon(event.event_type)
                severity_color = "🔴" if event.severity > 60 else "🟡" if event.severity > 30 else "🟢"

                zone_tag = f" | 🎯 **{event.market_impact_zone}**" if event.market_impact_zone else ""

                st.markdown(
                    f"{icon} **{event.event_type}** — {event.description} | "
                    f"Severity: {severity_color} {event.severity:.0f}/100 | "
                    f"Source: {event.source}{zone_tag}"
                )
        else:
            st.info("🌤️ No significant natural events detected. Calm conditions.")

        # ── Renaissance Note ──
        st.caption(
            "💡 Renaissance Technologies' Medallion Fund used weather patterns, "
            "satellite data, and natural disaster feeds as alternative alpha signals. "
            "Nature events affect energy costs (mining), supply chains (chips), "
            "oil prices (Hormuz), and risk appetite (safe haven flows)."
        )

    # ─────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────

    def _check_proximity(self, lat: float, lon: float) -> str:
        """Check if coordinates are near a critical market zone"""
        zone_coords = {
            "Persian Gulf": (27.0, 51.0, 800),
            "Taiwan": (23.5, 121.0, 300),
            "Japan": (36.0, 138.0, 500),
            "Texas": (31.0, -100.0, 600),
            "Kazakhstan": (48.0, 68.0, 800),
            "Iran": (32.0, 53.0, 700),
            "Bushehr": (28.9, 50.8, 200),
            "Dubai": (25.2, 55.3, 300),
            "Hong Kong": (22.3, 114.2, 200),
        }

        for zone_name, (z_lat, z_lon, radius_km) in zone_coords.items():
            dist = self._haversine(lat, lon, z_lat, z_lon)
            if dist <= radius_km:
                return zone_name
        return ""

    @staticmethod
    def _haversine(lat1, lon1, lat2, lon2) -> float:
        """Calculate distance in km between two coordinates"""
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))

    @staticmethod
    def _map_nasa_category(cat: str) -> Optional[str]:
        mapping = {
            "WILDFIRES": "WILDFIRE",
            "VOLCANOES": "VOLCANO",
            "SEVERE STORMS": "HURRICANE",
            "FLOODS": "FLOOD",
            "EARTHQUAKES": "EARTHQUAKE",
            "DROUGHT": "DROUGHT",
            "SEA AND LAKE ICE": None,
            "TEMPERATURE EXTREMES": "EXTREME_HEAT",
        }
        return mapping.get(cat, None)

    @staticmethod
    def _estimate_severity(event_type: str, event_data: dict) -> float:
        """Estimate severity when not directly available"""
        base = {"WILDFIRE": 35, "VOLCANO": 55, "HURRICANE": 50,
                "FLOOD": 40, "EARTHQUAKE": 60, "EXTREME_HEAT": 25, "DROUGHT": 20}
        return base.get(event_type, 30)

    @staticmethod
    def _get_event_icon(event_type: str) -> str:
        icons = {
            "EARTHQUAKE": "🌍", "TSUNAMI": "🌊", "HURRICANE": "🌀",
            "VOLCANO": "🌋", "FLOOD": "🌧️", "WILDFIRE": "🔥",
            "EXTREME_HEAT": "🌡️", "DROUGHT": "☀️",
            "NUCLEAR_INCIDENT": "☢️", "SOLAR_STORM": "⚡"
        }
        return icons.get(event_type, "⚠️")

    # ─────────────────────────────────────────
    # API FOR BAYESIAN INTEGRATION
    # ─────────────────────────────────────────

    def get_chaos_adjustment(self) -> float:
        """Returns chaos contribution to add to main Chaos/Entropy Level"""
        return self.impact.chaos_contribution

    def get_prior_adjustment(self) -> float:
        """
        Returns prior probability adjustment based on nature events.
        Negative = reduce prior (bearish), Positive = increase (bullish after recovery)
        """
        if self.impact.critical_events > 0:
            return -0.05 * self.impact.critical_events  # -5% per critical event
        return 0.0

    def get_summary_for_nlp(self) -> str:
        """Returns a text summary for NLP Radar integration"""
        if not self.events:
            return "NATURE: Clear — no significant events."

        critical = [e for e in self.events if e.severity > 60]
        if critical:
            return f"NATURE: ⚠️ {len(critical)} critical events — {', '.join(e.description for e in critical[:3])}"
        return f"NATURE: {len(self.events)} minor events monitored."


# ─────────────────────────────────────────────
# INTEGRATION WITH MEDALLION DASHBOARD
# ─────────────────────────────────────────────
#
# In elite_v20_dashboard_MEDALLION.py, add:
#
# 1. Import:
#    from nature_events_engine import NatureEventsEngine
#
# 2. Initialize (after other engines):
#    nature_engine = NatureEventsEngine()
#
# 3. Render panel (after Misdirection Engine):
#    nature_engine.render_panel()
#
# 4. Integrate with Bayesian (in compute_posterior):
#    chaos += nature_engine.get_chaos_adjustment()
#    prior += nature_engine.get_prior_adjustment()
#
# 5. Integrate with NLP Radar:
#    nlp_headlines.append(nature_engine.get_summary_for_nlp())
#
# ─────────────────────────────────────────────
