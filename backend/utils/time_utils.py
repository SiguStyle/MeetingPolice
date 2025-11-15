from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))


def now_iso() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
