# test_url_encoding.py
from pymongo import MongoClient

# Test with URL encoding
password = "0701805Aliyu%40"  # @ encoded as %40
connection_string = f"mongodb+srv://Vercel-Admin-atlas-teal-queen:{password}@atlas-teal-queen.runwsmr.mongodb.net/cyberguard?retryWrites=true&w=majority"

try:
    client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("✅ MongoDB Connection SUCCESS with URL encoding!")
except Exception as e:
    print(f"❌ Connection failed: {e}")
