from app.users import init_db
from app.users.standard import create_standard_items
from app.users.crud import open_db_conn

def on_starting(_):
    init_db()
    open_db_conn()
    create_standard_items()

def post_fork(_, __):
    open_db_conn()

if __name__ == "__main__":
    on_starting(None)
