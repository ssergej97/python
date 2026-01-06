import psycopg
from dataclasses import dataclass

DB_NAME = 'catering'
USER = 'sergey'
PASSWORD = ''
HOST = 'localhost'
PORT = 5432

# with psycopg.connect(
#     dbname=DB_NAME,
#     user=USER,
#     password=PASSWORD,
#     host=HOST,
#     port=PORT
# ) as connection:
#     with connection.cursor() as cur:
#         cur.execute(
#             "INSERT INTO users (name, phone, role) VALUES (%s, %s, %s) RETURNING id;",
#             ("Marry", "+30672244945", "USER"),
#         )
#
#         results = cur.fetchone()
#         print(results)

payload = {
    'dbname': 'catering',
    'user': 'sergey',
    'password': '',
    'host': 'localhost',
    'port': 5432
}

class DataBseConnection:
    def __enter__(self):
        self.conn = psycopg.connect(**payload)
        self.cur = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()

        self.cur.close()
        self.conn.close()

    def query(self, sql: str, params: tuple | None= None):
        self.cur.execute(sql, params or ())
        return self.cur.fetchall()

@dataclass
class User:
    name: str
    phone: str
    role: str
    id: int | None = None

    @classmethod
    def all(cls) -> list['User']:
        """return all users from the database"""

        with DataBseConnection() as db:
            rows = db.query('select name, phone, role, id from users')
            return [cls(*row) for row in rows]

    @classmethod
    def filter(cls, **filters) -> list['User']:
        """return filtered users from users table"""
        keys = filters.keys()
        conditions = ' AND '.join([f'{key} = %s' for key in keys])
        values = tuple(filters.values())

        with DataBseConnection() as db:
            rows = db.query(f'select name, phone, role, id from users where {conditions}', values)
            return [cls(*row) for row in rows]


#select all users from database
users = User.all()
print(users)

filtered_users: list[User] = User.filter(role='USER', id=1)
print(filtered_users)