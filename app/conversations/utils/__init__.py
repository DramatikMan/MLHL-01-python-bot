import sqlite3

from ...db import DB_URI


def get_columns_meta() -> dict[str, str]:
    with sqlite3.connect(DB_URI) as conn:
        return {
            row[0]: row[1]
            for row in conn.cursor().execute('SELECT * FROM meta')
        }
