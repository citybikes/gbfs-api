from citybikes.types import Station, Network


class CBD:
    def __init__(self, db):
        self.db = db

    # attr dispatcher to db obj
    def __getattr__(self, attr):
        return getattr(self.db, attr)

    async def get_network(self, uid):
        cur = await self.db.execute(
            """
            SELECT * FROM networks
            WHERE tag = ?
            LIMIT 1
        """,
            (uid,),
        )

        row = await cur.fetchone()

        if not row:
            return None

        return Network(**row)

    async def get_stations(self, uid):
        cur = await self.db.execute(
            """
            SELECT s.*
            FROM stations s
            JOIN networks n ON s.hash = json_each.value
            JOIN json_each(n.stations)
            WHERE n.tag = ?
            ORDER BY hash
        """,
            (uid,),
        )

        stations = map(lambda r: Station(**r), await cur.fetchall())
        return list(stations)

    async def network_exists(self, uid):
        cur = await self.db.execute(
            """
            SELECT 1 from networks
            WHERE tag = ?
            LIMIT 1
        """,
            (uid,),
        )
        row = await cur.fetchone()

        return bool(row)

    async def get_last_updated(self, uid=None):
        if uid:
            cur = await self.db.execute(
                """
                SELECT MAX(stat->>'timestamp') as timestamp FROM stations
                WHERE network_tag = ?
            """,
                (uid,),
            )
        else:
            cur = await self.db.execute(
                """
                SELECT MAX(stat->>'timestamp') as timestamp FROM stations
            """
            )

        last_updated = (await cur.fetchone())["timestamp"]
        return last_updated

    async def vehicle_types(self, uid):
        # match vehicle types according to station information heuristics
        # XXX ideally, we should set these on the network level in pybikes
        # so this info would be in meta

        cur = await self.db.execute(
            """
            SELECT
                   max(s.stat->>'extra'->>'normal_bikes' IS NOT NULL) as normal_bikes,
                   max(s.stat->>'extra'->>'ebikes' IS NOT NULL) as ebikes,
                   max(s.stat->>'extra'->>'cargo' IS NOT NULL) as cargo,
                   max(s.stat->>'extra'->>'ecargo' IS NOT NULL) as ecargo,
                   max(s.stat->>'extra'->>'kid_bikes' IS NOT NULL) as kid_bikes
            FROM stations s
            JOIN networks n ON s.hash = json_each.value
            JOIN json_each(n.stations)
            WHERE n.tag = ?
              AND s.network_tag = ?
            GROUP BY s.network_tag
        """,
            (uid, uid),
        )

        vehicle_types_q = await cur.fetchone()
        return vehicle_types_q

    async def get_tags(self):
        cur = await self.db.execute("""
            SELECT tag FROM networks
        """)
        rows = await cur.fetchall()
        return list(map(lambda r: r["tag"], rows))
