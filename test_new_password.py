# test_new_password.py
from pymongo import MongoClient

new_password = "0701805Aliyu"
connection_string = f"mongodb+srv://Vercel-Admin-atlas-teal-queen:{new_password}@atlas-teal-queen.runwsmr.mongodb.net/cyberguard?retryWrites=true&w=majority"

try:
    client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("✅ MongoDB Connection SUCCESS!")
    
    # Test database operations
    db = client.cyberguard
    
    # Create collections if they don't exist
    collections = ['users', 'payments', 'sessions', 'otp_storage']
    for collection in collections:
        if collection not in db.list_collection_names():
            db.create_collection(collection)
            print(f"Created collection: {collection}")
    
    print(f"Database: {db.name}")
    print(f"Collections: {db.list_collection_names()}")
    
    # Test write operation
    test_user = {"test": "data", "timestamp": "now"}
    db.users.insert_one(test_user)
    print("✅ Write test successful!")
    
except Exception as e:
    print(f"❌ MongoDB Connection FAILED: {e}")
