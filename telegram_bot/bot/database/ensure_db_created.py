import logging

import psycopg2
from psycopg2 import sql

logger = logging.getLogger(__name__)


def create_database(dbname, user, password, host="localhost", port="5432"):
    try:
        connection = psycopg2.connect(
            dbname='postgres',
            user=user,
            password=password,
            host=host,
            port=port
        )
        connection.autocommit = True

        cursor = connection.cursor()

        create_db_query = sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname))
        cursor.execute(create_db_query)
    except psycopg2.Error as e:
        logger.error(f"Error creating database: {e}")
    finally:
        if connection:
            cursor.close()
            connection.close()
