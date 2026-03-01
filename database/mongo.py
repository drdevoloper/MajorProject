from pymongo import MongoClient
from config import MONGO_URI

client = MongoClient(MONGO_URI)

db = client["insider_db"]

stocks_collection = db["stocks"]
news_list = db["news"]
logs = db["risk_logs"]
features_collection = db["features"]