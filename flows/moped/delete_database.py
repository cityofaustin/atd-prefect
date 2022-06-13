#!/usr/bin/env python3
"""
Delete a database on the RDS
"""
import sys, os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def main():
    host = os.getenv("MOPED_TEST_HOSTNAME")
    user = os.getenv("MOPED_TEST_USER")
    password = os.getenv("MOPED_TEST_PASSWORD")

    pg = psycopg2.connect(host=host, user=user, password=password)
    pg.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = pg.cursor()

    database_name = sys.argv[1]

    create_database_sql = f"DROP DATABASE IF EXISTS {database_name}".format(
        database_name
    )
    print(create_database_sql)
    cursor.execute(create_database_sql)


if __name__ == "__main__":
    main()
