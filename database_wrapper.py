import pymongo

from pymongo import MongoClient

cluster = MongoClient("<your database URL>")
db = cluster["<name of your cluster in the database>"]

class DatabaseWrapper:
	def post(db_name,obj):
		collection = db[db_name]
		collection.insert_one(obj)

	def find(db_name,obj):
		collection = db[db_name]
		return list(collection.find({},obj))

	def find_one(db_name,obj):
		collection = db[db_name]
		return collection.find_one(obj)

	def update(db_name, old, new):
		collection = db[db_name]
		return collection.update_one(old, {"$set" : new})



#peform some test with the database


