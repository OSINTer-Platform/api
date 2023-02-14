def on_starting(_):
    from app.users import init_db
    init_db()

    from app.users.standard import create_standard_items
    create_standard_items()
