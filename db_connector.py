from pymongo.mongo_client import MongoClient

DB_URL = "mongodb+srv://rowdyslav:228doxy228@cluster0.736skbi.mongodb.net/?retryWrites=true&w=majority"
DB_CLIENT = MongoClient(DB_URL)
CUBEFOOD_DB = DB_CLIENT["CubeFood"]

OFFICES = CUBEFOOD_DB["offices"]
USERS = CUBEFOOD_DB["users"]
