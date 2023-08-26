from fastapi.testclient import TestClient

# Important order of imports, to inject custom couchdb index name, before DB connection is instatiated
from app import config_options

config_options.COUCHDB_NAME = "osinter_users_test"
from app.main import app


client = TestClient(app)
