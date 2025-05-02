import os
import sys
import json
import sqlite3
import signal
import logging
import argparse

from citybikes.db import migrate
from citybikes.hyper.subscriber import ZMQSubscriber

DB_URI = os.getenv("DB_URI", "citybikes.db")
ZMQ_ADDR = os.getenv("ZMQ_ADDR", "tcp://127.0.0.1:5555")
ZMQ_TOPIC = os.getenv("ZMQ_TOPIC", "")

log = logging.getLogger("subscriber")

# XXX: mainly copy-pasta from citybikes/hyper
# think about moving this to the codebase if enough parts use it


class Sqlitesubscriber(ZMQSubscriber):
    def __init__(self, con, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.con = con

    def handle_message(self, topic, message):
        network = json.loads(message)
        meta = network["meta"]

        station_ids = [s["id"] for s in network.get("stations", [])]
        vehicle_ids = [v["id"] for v in network.get("vehicles", [])]

        cursor = self.con.cursor()

        # XXX check JSONB types
        log.info("Processing %s", meta)

        cursor.execute(
            """
            INSERT INTO networks (tag, name, latitude, longitude, meta, stations, vehicles)
            VALUES (?, ?, ?, ?, json(?), json(?), json(?))
            ON CONFLICT(tag) DO UPDATE SET
                name=excluded.name,
                latitude=excluded.latitude,
                longitude=excluded.longitude,
                meta=json(excluded.meta),
                stations=json(excluded.stations),
                vehicles=json(excluded.vehicles)
            WHERE
                -- ignore info if no stations (prob an error)
                excluded.stations != '[]' OR excluded.vehicles != '[]'
        """,
            (
                network["tag"],
                meta["name"],
                meta["latitude"],
                meta["longitude"],
                json.dumps(meta),
                json.dumps(station_ids),
                json.dumps(vehicle_ids),
            ),
        )

        self.con.commit()

        log.info("[%s] Got %d stations" % (network["tag"], len(network["stations"])))

        data_iter = (
            (
                s["id"],
                s["name"],
                s["latitude"],
                s["longitude"],
                json.dumps(
                    {
                        "bikes": s["bikes"],
                        "free": s["free"],
                        "timestamp": s["timestamp"],
                        "extra": s["extra"],
                    }
                ),
                network["tag"],
            )
            for s in network["stations"]
        )

        cursor.executemany(
            """
            INSERT INTO stations (hash, name, latitude, longitude, stat, network_tag)
            VALUES (?, ?, ?, ?, json(?), ?)
            ON CONFLICT(hash) DO UPDATE SET
                -- some networks may stop providing a name randomly
                name=coalesce(excluded.name, name),
                --
                latitude=excluded.latitude,
                longitude=excluded.longitude,
                stat=json(excluded.stat),
                network_tag=excluded.network_tag
        """,
            data_iter,
        )
        self.con.commit()
        log.info(
            "[%s] Finished processing %d stations"
            % (network["tag"], len(network["stations"]))
        )

        log.info("[%s] Got %d vehicles" % (network["tag"], len(network["vehicles"])))

        data_iter = (
            (
                v["id"],
                v["latitude"],
                v["longitude"],
                v["kind"],
                json.dumps(
                    {
                        "timestamp": v["timestamp"],
                        "extra": v["extra"],
                    }
                ),
                network["tag"],
            )
            for v in network["vehicles"]
        )

        cursor.executemany(
            """
            INSERT INTO vehicles (hash, latitude, longitude, kind, stat, network_tag)
            VALUES (?, ?, ?, ?, json(?), ?)
            ON CONFLICT(hash) DO UPDATE SET
                latitude=excluded.latitude,
                longitude=excluded.longitude,
                kind=excluded.kind,
                stat=json(excluded.stat),
                network_tag=excluded.network_tag
        """,
            data_iter,
        )
        self.con.commit()
        log.info(
            "[%s] Finished processing %d vehicles"
            % (network["tag"], len(network["vehicles"]))
        )

        # Now its probably a good time to clean up orphaned vehicles and
        # stations ...
        # XXX: this could be an update trigger on networks
        cursor.execute(
            """
            DELETE FROM stations
            WHERE network_tag = ?
              AND hash NOT IN (
                SELECT value FROM networks, json_each(networks.stations)
                WHERE networks.tag = ?
            );
         """,(network['tag'], network['tag'], ))

        log.info(
            "[%s] GC %d stations"
            % (network["tag"], cursor.rowcount)
        )

        cursor.execute(
            """
            DELETE FROM vehicles
            WHERE network_tag = ?
              AND hash NOT IN (
                SELECT value FROM networks, json_each(networks.vehicles)
                WHERE networks.tag = ?
            );
         """,(network['tag'], network['tag'], ))

        log.info(
            "[%s] GC %d vehicles"
            % (network["tag"], cursor.rowcount)
        )

        self.con.commit()


def main(args):
    db = sqlite3.connect(DB_URI)
    db.row_factory = lambda *a: dict(sqlite3.Row(*a))
    assert migrate(db)

    cur = db.cursor()
    cur.executescript("""
        PRAGMA journal_mode = WAL;
    """)
    db.commit()

    def shutdown(*args, **kwargs):
        log.info("Closing DB conn")
        db.close()
        sys.exit(0)

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, shutdown)

    subscriber = Sqlitesubscriber(db, args.addr, args.topic)
    subscriber.reader()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s",
        handlers=[logging.StreamHandler(stream=sys.stderr)],
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--addr", default=ZMQ_ADDR)
    parser.add_argument("-t", "--topic", default=ZMQ_TOPIC)
    args, _ = parser.parse_known_args()
    main(args)
