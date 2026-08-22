import logging
import sqlite3
from contextlib import contextmanager
from importlib import resources

log = logging.getLogger("db")


@contextmanager
def get_session(*args, **kwargs):
    with sqlite3.connect(*args, **kwargs) as db:
        # XXX Check perf penalty on this
        db.row_factory = lambda *a: dict(sqlite3.Row(*a))
        yield db


def migrate(conn):
    migrations_path = resources.files("citybikes.db") / "migrations"
    migrations = sorted(migrations_path.glob("*.sql"))
    version = conn.execute("PRAGMA user_version").fetchone()
    version = version["user_version"]
    for migration in migrations[version:]:
        cur = conn.cursor()
        try:
            log.info("Applying %s", migration.name)
            cur.executescript("begin;" + migration.read_text())
        except Exception as e:  # noqa: BLE001
            log.error("Failed migration %s: %s. Bye", migration.name, e)
            cur.execute("rollback")
            return False
        else:
            cur.execute("commit")

    return True


# class shortcuts
from citybikes.db.cbd import CBD as CBD
