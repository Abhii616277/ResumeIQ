"""
database.py — MongoDB connection and GridFS setup.
"""
import gridfs
from pymongo import MongoClient

from config import MONGO_URI, MONGO_DB_NAME, MONGO_COLLECTION_NAME

conn = MongoClient("mongodb+srv://rj616277_db_user:Rajkumar12@cluster0.qitfhku.mongodb.net/")
db = conn["Node"]
collection = db["node"]
fs = gridfs.GridFS(db)