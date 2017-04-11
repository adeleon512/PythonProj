import bcrypt

def get_user(dbc, uid):
    """
    Get a user's information.
    :param dbc: A database connection. This function will make and commit a transaction.
    :param uid: The user ID.
    :return: The user information map, or None if the user is invalid.
    """
    with dbc, dbc.cursor() as cur:
        cur.execute('''
            SELECT username
            FROM bm_user WHERE user_id = %s
        ''', (uid,))
        row = cur.fetchone()
        if row is None:
            return None
        else:
            name, = row
            return {'name': name, 'id': uid }


def lookup_user(dbc, name):
    """
    Look up a user by name.
    :param dbc: A database connection. This function will take a transaction.
    :param uid: The user ID.
    :return: The user information map, or None if the user is invalid.
    """
    with dbc, dbc.cursor() as cur:
        cur.execute('''
            SELECT user_id, username, pw_hash
            FROM bm_user WHERE username = %s
        ''', (name,))
        row = cur.fetchone()
        if row is None:
            return None
        else:
            uid, name, pw_hash = row
            return {'name': name, 'id': uid, 'pw_hash': pw_hash }


def check_auth(dbc, username, password):
    """
    Check if a user is authorized.
    :param dbc: The database connection.
    :param username: The user name.
    :param password: The password (unhashed).
    :return: The user ID, or None if authentication failed.
    """
    user = lookup_user(dbc, username)
    if user is None:
        return None
    hash = bcrypt.hashpw(password.encode('UTF-8'),
                         user['pw_hash'].encode('UTF-8'))
    if hash == user['pw_hash'].encode('UTF-8'):
        return user['id']
    else:
        return None


def create_user(dbc, username, password):
    """
    Creates a user.
    :param dbc: The DB connection.  This function will make and commit a transaction.
    :param username: The user name.
    :param password: The password.
    :return: The user ID.
    """
    hash = bcrypt.hashpw(password.encode('UTF-8'), bcrypt.gensalt())
    with dbc, dbc.cursor() as cur:
        cur.execute('''
            INSERT INTO bm_user (username, pw_hash)
            VALUES (%s, %s)
            RETURNING user_id
        ''', (username, hash.decode('UTF-8')))
        row = cur.fetchone()
        return row[0]
