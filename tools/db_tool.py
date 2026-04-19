import os

import mysql.connector
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

_DB_CONFIG = {
    "local": {
        "host":     os.getenv("LOCAL_DB_HOST"),
        "port":     int(os.getenv("LOCAL_DB_PORT", 3306)),
        "user":     os.getenv("LOCAL_DB_USER"),
        "password": os.getenv("LOCAL_DB_PASSWORD"),
        "database": os.getenv("LOCAL_DB_NAME"),
    },
    "staging": {
        "host":     os.getenv("STAGING_DB_HOST"),
        "port":     int(os.getenv("STAGING_DB_PORT", 3306)),
        "user":     os.getenv("STAGING_DB_USER"),
        "password": os.getenv("STAGING_DB_PASSWORD"),
        "database": os.getenv("STAGING_DB_NAME"),
    },
    "production": {
        "host":     os.getenv("PRODUCTION_DB_HOST"),
        "port":     int(os.getenv("PRODUCTION_DB_PORT", 3306)),
        "user":     os.getenv("PRODUCTION_DB_USER"),
        "password": os.getenv("PRODUCTION_DB_PASSWORD"),
        "database": os.getenv("PRODUCTION_DB_NAME"),
    },
}


def get_connection(env):
    """Return an open MySQL connection for the given env (local/staging/production)."""
    env = env.lower()
    cfg = _DB_CONFIG.get(env)
    if not cfg:
        raise ValueError(f"Unknown env '{env}'. Choose: local, staging, production.")
    if not cfg["host"] or not cfg["user"]:
        raise ValueError(f"DB credentials for '{env}' are not set in .env.")
    conn = mysql.connector.connect(**cfg)
    return conn


def run_query(env, sql, params=None):
    """Execute a SELECT query and return results as a list of dicts."""
    conn = get_connection(env)
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params or ())
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()


def run_write(env, sql, params=None):
    """
    Execute an INSERT/UPDATE/DELETE statement.
    Raises an error if env is 'production' to prevent accidental writes.
    Returns the number of affected rows.
    """
    if env.lower() == "production":
        raise PermissionError("Write operations are not allowed on the production database.")
    conn = get_connection(env)
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params or ())
        conn.commit()
        affected = cursor.rowcount
        print(f"Write succeeded. Rows affected: {affected}")
        return affected
    finally:
        conn.close()


def table_exists(env, table_name):
    """Return True if table_name exists in the database for the given env."""
    cfg = _DB_CONFIG[env.lower()]
    rows = run_query(
        env,
        "SELECT COUNT(*) AS cnt FROM information_schema.tables "
        "WHERE table_schema = %s AND table_name = %s",
        (cfg["database"], table_name),
    )
    exists = rows[0]["cnt"] > 0
    print(f"Table '{table_name}' exists in {env}: {exists}")
    return exists


def get_tables(env):
    """Return a list of all table names in the database."""
    rows = run_query(env, "SHOW TABLES")
    # SHOW TABLES returns single-key dicts; extract the value regardless of key name
    tables = [list(row.values())[0] for row in rows]
    print(f"\nTables in {env} DB ({len(tables)} total):\n")
    for t in tables:
        print(f"  {t}")
    return tables


def get_row_count(env, table_name):
    """Return the number of rows in a table."""
    rows = run_query(env, f"SELECT COUNT(*) AS cnt FROM `{table_name}`")
    count = rows[0]["cnt"]
    print(f"Row count for '{table_name}' ({env}): {count}")
    return count


def verify_record_exists(env, table_name, conditions):
    """
    Return True if at least one row matches all column:value conditions.
    conditions is a dict, e.g. {"email": "test@example.com", "status": "active"}.
    """
    where_clause = " AND ".join(f"`{col}` = %s" for col in conditions)
    values       = tuple(conditions.values())
    rows = run_query(
        env,
        f"SELECT COUNT(*) AS cnt FROM `{table_name}` WHERE {where_clause}",
        values,
    )
    exists = rows[0]["cnt"] > 0
    print(f"Record exists in '{table_name}' ({env}) with {conditions}: {exists}")
    return exists
