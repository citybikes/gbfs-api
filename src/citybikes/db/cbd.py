from citybikes.db.types import Station, Network, Vehicle


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
            WHERE network_tag = ?
              AND hash IN (
                SELECT value FROM networks
                  JOIN json_each(networks.stations) ON networks.tag = ?
            )
            ORDER BY hash
        """,
            (uid, uid, ),
        )

        stations = map(lambda r: Station(**r), await cur.fetchall())
        return list(stations)

    async def get_vehicles(self, uid):
        cur = await self.db.execute(
            """
            SELECT v.*
            FROM vehicles v
            WHERE network_tag = ?
              AND hash IN (
                SELECT value FROM networks
                  JOIN json_each(networks.vehicles) ON networks.tag = ?
            )
            ORDER BY hash

        """,
            (uid, uid, ),
        )

        vehicles = map(lambda r: Vehicle(**r), await cur.fetchall())
        return list(vehicles)

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
                SELECT updated as timestamp FROM networks
                WHERE tag = ?
            """,
                (uid,),
            )
        else:
            cur = await self.db.execute(
                """
                SELECT MAX(updated) as timestamp FROM networks
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
            WITH bike_type_flags AS (
                SELECT
                    MAX(s.stat->>'extra'->>'normal_bikes' IS NOT NULL)  AS normal_bikes,
                    MAX(s.stat->>'extra'->>'ebikes' IS NOT NULL)        AS ebikes,
                    MAX(s.stat->>'extra'->>'cargo' IS NOT NULL)         AS cargo,
                    MAX(s.stat->>'extra'->>'ecargo' IS NOT NULL)        AS ecargo,
                    MAX(s.stat->>'extra'->>'kid_bikes' IS NOT NULL)     AS kid_bikes,
                    MAX(0)                                              AS scooter
                FROM stations s
                WHERE s.network_tag = ?

                UNION ALL

                -- handle missing normal_bikes in extra
                SELECT
                    MAX(s.stat->>'bikes' - s.stat->>'extra'->>'ebikes' IS NOT NULL) AS normal_bikes,
                    MAX(0) AS ebikes,
                    MAX(0) AS cargo,
                    MAX(0) AS ecargo,
                    MAX(0) AS kid_bikes,
                    MAX(0) AS scooter
                FROM stations s
                WHERE s.network_tag = ?
                  AND s.stat->>'extra'->>'normal_bikes' IS NULL
                  -- only if sum(types) < total_bikes
                  AND s.stat->>'bikes' > (
                    coalesce(s.stat->>'extra'->>'normal_bikes', 0) +
                    coalesce(s.stat->>'extra'->>'ebikes', 0) +
                    coalesce(s.stat->>'extra'->>'cargo', 0) +
                    coalesce(s.stat->>'extra'->>'ecargo', 0) +
                    coalesce(s.stat->>'extra'->>'kid_bikes', 0)
                  )

                UNION ALL

                SELECT
                    MAX(v.kind = 'bike')      AS normal_bikes,
                    MAX(v.kind = 'ebike')     AS ebikes,
                    MAX(0)                    AS cargo,
                    MAX(0)                    AS ecargo,
                    MAX(0)                    AS kid_bikes,
                    MAX(v.kind = 'scooter')   AS scooter
                FROM vehicles v
                WHERE v.network_tag = ?
            )

            SELECT
                MAX(normal_bikes) AS normal_bikes,
                MAX(ebikes) AS ebikes,
                MAX(cargo) AS cargo,
                MAX(ecargo) AS ecargo,
                MAX(kid_bikes) AS kid_bikes,
                MAX(scooter) AS scooter
            FROM bike_type_flags
        """,
            (uid, uid, uid),
        )

        vehicle_types_q = await cur.fetchone()

        if not vehicle_types_q:
            return []

        vehicle_types = filter(lambda kv: bool(kv[1]), vehicle_types_q.items())

        return [k for k, _ in vehicle_types]

    async def get_tags(self):
        cur = await self.db.execute("""
            SELECT tag FROM networks
            ORDER BY tag
        """)
        rows = await cur.fetchall()
        return list(map(lambda r: r["tag"], rows))
