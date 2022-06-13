#!/usr/bin/env python3
"""
Create a database on the RDS
"""
import psycopg2
import sys


def main():
    host = os.getenv("MOPED_TEST_HOSTNAME")
    user = os.getenv("MOPED_TEST_USER")
    password = os.getenv("MOPED_TEST_PASSWORD")

    pg = psycopg2.connect(host, user, password)
    cursor = pg.cursor()

    database_name = sys.argv[1]

    create_database_sql = f"CREATE DATABASE {database_name}".format(database_name)

    cursor.execute(create_database_sql)


if __name__ == "__main__":
    main()
