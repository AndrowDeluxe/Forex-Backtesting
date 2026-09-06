"""Eigene Kopie von challenge_portfolio/paper_bot.py::_retry()/
_call_with_timeout() -- bewusst NICHT importiert (siehe Plan-Dokument,
Abschnitt "Retry/timeout"): dieser Pilot soll die 3 bestehenden Kopien
(challenge_portfolio/ek_portfolio/fk_instant_funding) nicht anfassen, das
ist ein spaeterer, eigener Konsolidierungsschritt, sobald der Lake sich
bewaehrt hat. Identische Logik/Werte wie das Original (6 Versuche/8s Pause,
90s Timeout pro Versuch per Daemon-Thread)."""

import queue
import threading
import time


def _call_with_timeout(fn, timeout_seconds: float = 90.0):
    result_q: queue.Queue = queue.Queue(maxsize=1)

    def _runner():
        try:
            result_q.put(("ok", fn()))
        except Exception as e:  # noqa: BLE001
            result_q.put(("error", e))

    threading.Thread(target=_runner, daemon=True).start()
    try:
        status, value = result_q.get(timeout=timeout_seconds)
    except queue.Empty:
        raise TimeoutError(f"Aufruf haengt noch nach {timeout_seconds:.0f}s (dukascopy_python-Hang, siehe DASHBOARD.md)")
    if status == "error":
        raise value
    return value


def retry(fn, attempts: int = 6, delay_seconds: float = 8.0, timeout_seconds: float = 90.0):
    last_exc = None
    for attempt in range(attempts):
        try:
            return _call_with_timeout(fn, timeout_seconds)
        except Exception as e:
            last_exc = e
            if attempt < attempts - 1:
                time.sleep(delay_seconds)
    raise last_exc
