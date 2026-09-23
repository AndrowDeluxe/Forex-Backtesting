"""Read-only MT5-Abzug aller Live-Konten -- die IST-Seite des Soll/Ist-Vergleichs.

Hebt das bisher woechentlich neu geschriebene Wegwerf-Skript
(`_kw37_pull.py`, `_kw37_fk_pull.py`, ...) auf ein festes Modul mit
Parametern statt hartkodierter Datumsgrenzen.

NUR LESEND. Verwendet ausschliesslich account_info(), history_deals_get()
und positions_get() -- niemals order_send/order_check/modify/cancel. Dieses
Modul darf unter keinen Umstaenden Handelsfunktionen aufrufen; es laeuft im
Weekly-Report-Kontext unbeaufsichtigt gegen ECHTGELD-Konten.

Aufruf:
    python scripts/reports/mt5_pull.py --from 2026-09-07 --to 2026-09-14
    python scripts/reports/mt5_pull.py --week 2026-W37

Zugangsdaten kommen aus den Bridge-config.py-Dateien AUSSERHALB des Repos
(siehe knowledge/CLAUDE.md) -- dieses Modul haelt selbst keine Passwoerter.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "scripts" / "reports"

EK_BRIDGE = Path(r"C:\Users\andre\EK-Portfolio-Bridge")
FUNDED_BRIDGE = Path(r"C:\Users\andre\Funded-Portfolio-Bridge")
FK_BRIDGE = Path(r"C:\Users\andre\FKInstantFunding-MT5-Bridge")


@dataclass(frozen=True)
class AccountRef:
    """Ein MT5-Konto, wie es fuer den Abzug gebraucht wird."""
    label: str          # Anzeigename im Report
    bridge: str         # "ek" | "funded" | "fk" -- Zuordnung zur Soll-Seite
    state_id: str       # bridge_state_<id>.json bei funded; "" sonst
    login: int
    password: str
    server: str
    terminal_path: str


def _load_bridge_config(bridge_dir: Path, module_name: str):
    """Laedt die config.py einer Bridge, ohne sie ins Repo zu kopieren.

    Die drei Bridge-Ordner liegen bewusst ausserhalb des Git-Repos (echte
    Zugangsdaten). importlib statt sys.path-Manipulation, damit sich die
    gleichnamigen `config`-Module der drei Bridges nicht gegenseitig
    ueberschreiben.
    """
    path = bridge_dir / "config.py"
    if not path.exists():
        raise FileNotFoundError(f"config.py nicht gefunden: {path}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def discover_accounts() -> list[AccountRef]:
    """Liest die Kontoliste aus den drei Bridge-Configs statt sie zu duplizieren.

    Damit wandert ein neu hinzugefuegtes oder entferntes Konto automatisch in
    den Report -- genau der Fehlermodus, den die hartkodierten Wegwerf-Skripte
    hatten (IQ 15514 stand dort noch drin, nachdem es am 2026-09-07 entfernt
    worden war).
    """
    accounts: list[AccountRef] = []

    ek = _load_bridge_config(EK_BRIDGE, "ek_bridge_config")
    accounts.append(AccountRef(
        label="EK-Portfolio-Bridge / Tickmill", bridge="ek", state_id="",
        login=ek.MT5_LOGIN, password=ek.MT5_PASSWORD, server=ek.MT5_SERVER,
        terminal_path=ek.TERMINAL_PATH,
    ))

    funded = _load_bridge_config(FUNDED_BRIDGE, "funded_bridge_config")
    for acc in funded.ACCOUNTS:
        accounts.append(AccountRef(
            label=f"Funded / {acc.telegram_title} ({acc.state_id})", bridge="funded",
            state_id=acc.state_id, login=acc.mt5_login, password=acc.mt5_password,
            server=acc.mt5_server, terminal_path=acc.mt5_terminal_path,
        ))

    fk = _load_bridge_config(FK_BRIDGE, "fk_bridge_config")
    accounts.append(AccountRef(
        label="FK Instant Funding", bridge="fk", state_id="",
        login=fk.ACCOUNT.mt5_login, password=fk.ACCOUNT.mt5_password,
        server=fk.ACCOUNT.mt5_server, terminal_path=fk.ACCOUNT.mt5_terminal_path,
    ))
    return accounts


_DEAL_FIELDS = ("ticket", "order", "time", "type", "entry", "position_id", "symbol",
                "volume", "price", "profit", "commission", "swap", "fee", "comment",
                "magic", "reason")
_POS_FIELDS = ("ticket", "time", "type", "magic", "symbol", "volume", "price_open",
               "sl", "tp", "price_current", "swap", "profit", "comment")
_ACC_FIELDS = ("login", "server", "currency", "balance", "equity", "profit",
               "margin", "margin_free", "leverage", "trade_mode")


def pull(frm: datetime, to: datetime, accounts: list[AccountRef] | None = None) -> dict:
    """Zieht Kontostand, abgeschlossene Deals und offene Positionen je Konto.

    Ein fehlschlagendes Konto bricht den Lauf NICHT ab -- der Fehler landet
    als "error" im Ergebnis, die uebrigen Konten werden weiter abgezogen.
    Grund: im Weekly-Report ist ein unvollstaendiger Abzug deutlich besser als
    gar keiner, und ein nicht erreichbares Terminal ist der Normalfall, nicht
    die Ausnahme (siehe die IPC-Timeout-Historie in CHANGELOG.md).
    """
    import MetaTrader5 as mt5  # lokal: nur hier gebraucht, haelt Import-Fehler lokal

    if accounts is None:
        accounts = discover_accounts()

    out: dict = {"from": frm.isoformat(), "to": to.isoformat(), "accounts": {}}
    for acc in accounts:
        rec: dict = {"login": acc.login, "server": acc.server, "bridge": acc.bridge,
                     "state_id": acc.state_id}
        try:
            ok = mt5.initialize(path=acc.terminal_path, login=acc.login,
                                password=acc.password, server=acc.server, timeout=60000)
        except Exception as exc:  # noqa: BLE001 -- jede Ursache soll geloggt, nicht geworfen werden
            rec["error"] = f"initialize raised: {exc}"
            out["accounts"][acc.label] = rec
            continue
        if not ok:
            rec["error"] = f"initialize failed: {mt5.last_error()}"
            out["accounts"][acc.label] = rec
            mt5.shutdown()
            continue

        try:
            ai = mt5.account_info()
            if ai is None:
                rec["error"] = f"account_info None: {mt5.last_error()}"
            else:
                d = ai._asdict()
                rec["account"] = {k: d.get(k) for k in _ACC_FIELDS}

            # Fenster bewusst beidseitig um einen Tag geweitet und danach selbst
            # gefiltert (Fund 2026-09-23). `history_deals_get()` wertet die naiven
            # Grenzen NICHT in Serverzeit aus -- derselbe Abzug lieferte mit
            # `--to 2026-09-24` 13 Deals und mit `--to 2026-09-25` 22, es fehlten
            # genau die Buchungen ab ~22:40 Serverzeit. Der Ausfall ist still (keine
            # Warnung, nur weniger Zeilen), weist also das Ergebnis des letzten Tages
            # zu niedrig aus. Gefiltert wird gegen DIESELBE Zeitbasis, die unten als
            # `time_iso` rausgeht: Unix-Zeitstempel als UTC gelesen == Serverzeit.
            pad = timedelta(days=1)
            deals = mt5.history_deals_get(frm - pad, to + pad)
            if deals is None:
                rec["deals_error"] = str(mt5.last_error())
                rec["deals"] = []
            else:
                rec["deals"] = []
                for dd in deals:
                    server_time = datetime.fromtimestamp(dd.time, timezone.utc).replace(tzinfo=None)
                    if not (frm <= server_time < to):   # obere Grenze exklusiv, wie bisher
                        continue
                    row = {k: v for k, v in dd._asdict().items() if k in _DEAL_FIELDS}
                    row["time_iso"] = server_time.isoformat()
                    rec["deals"].append(row)

            pos = mt5.positions_get()
            rec["positions"] = [] if pos is None else [
                {k: v for k, v in p._asdict().items() if k in _POS_FIELDS} for p in pos
            ]
            for p in rec["positions"]:
                p["time_iso"] = datetime.fromtimestamp(p["time"], timezone.utc).replace(tzinfo=None).isoformat()
        finally:
            mt5.shutdown()

        out["accounts"][acc.label] = rec
    return out


def week_bounds(iso_week: str) -> tuple[datetime, datetime]:
    """'2026-W37' -> (Montag 00:00, folgender Montag 00:00).

    Fenster bewusst bis Montag 00:00 statt Sonntag 24:00: history_deals_get()
    ist am oberen Rand exklusiv, und Broker-Zeitstempel liegen in Server-TZ
    (UTC+3) -- ein auf Sonntag 23:59 gekapptes Fenster verliert sonst die
    letzten Freitag-Deals mancher Server.

    Seit dem Fenster-Fix in pull() (2026-09-23) ist das kein Schutzmechanismus
    mehr, sondern nur noch die korrekte Wochengrenze: dort wird beidseitig um
    einen Tag geweitet und anschliessend gegen die Serverzeit gefiltert.
    Gegengeprueft an 2026-W38 -- identische Deal-Zahlen und Summen wie im
    archivierten Report (EK 40/-227,31, TTP 89/-898,07, IQ 98/+1.411,14).
    """
    year, week = iso_week.split("-W")
    monday = datetime.fromisocalendar(int(year), int(week), 1)
    return monday, monday + timedelta(days=7)


def main() -> int:
    ap = argparse.ArgumentParser(description="Read-only MT5-Abzug aller Live-Konten.")
    ap.add_argument("--week", help="ISO-Woche, z.B. 2026-W37")
    ap.add_argument("--from", dest="frm", help="Startdatum YYYY-MM-DD")
    ap.add_argument("--to", dest="to", help="Enddatum YYYY-MM-DD (exklusiv)")
    ap.add_argument("--out", help="Zieldatei (Default: scripts/reports/mt5_<fenster>.json)")
    args = ap.parse_args()

    if args.week:
        frm, to = week_bounds(args.week)
        tag = args.week
    elif args.frm and args.to:
        frm = datetime.fromisoformat(args.frm)
        to = datetime.fromisoformat(args.to)
        tag = f"{args.frm}_{args.to}"
    else:
        ap.error("entweder --week oder --from/--to angeben")

    data = pull(frm, to)
    out_path = Path(args.out) if args.out else OUT_DIR / f"mt5_{tag}.json"
    out_path.write_text(json.dumps(data, indent=1, default=str), encoding="utf-8")

    for label, rec in data["accounts"].items():
        if "error" in rec:
            print(f"  FEHLER  {label}: {rec['error']}")
        else:
            acc = rec.get("account") or {}
            print(f"  ok      {label}: Equity {acc.get('equity')} {acc.get('currency')}, "
                  f"{len(rec['deals'])} Deals, {len(rec['positions'])} offene Positionen")
    print(f"\nGespeichert: {out_path}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
