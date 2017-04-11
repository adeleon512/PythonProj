from contextlib import contextmanager
import psycopg2


def db_connect(app):
    """
    Create a database connection.
    :param app: The Flask application.
    :return: The database connection
    """
    # Get the database connection from the configuration
    cxn = psycopg2.connect(**app.config['PG_ARGS'])
    return cxn


@contextmanager
def db_cursor(app):
    """
    Create a database connection and cursor.  Does *not* manage transactions.
    :param app: The application.
    :return: A database cursor that, when closed, also closes its connection.
    """
    dbc = db_connect(app)
    try:
        cur = dbc.cursor()
        try:
            yield cur
        finally:
            cur.close()
    finally:
        dbc.close()
