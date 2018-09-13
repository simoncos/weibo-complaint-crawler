from pymongo import MongoClient

from conf import MONGO_HOST, MONGO_PORT, MONGO_DATABASE, MONGO_USERNAME, MONGO_PASSWORD, MONGO_COLLECTION

class MongoHelper:
    client = MongoClient(MONGO_HOST, MONGO_PORT)
    db = client[MONGO_DATABASE]
    db.authenticate(MONGO_USERNAME, MONGO_PASSWORD)
    collection = db[MONGO_COLLECTION]

    def update(self, data):
        if type(data) is list:
            for i in data:
                self.collection.replace_one({'url': i['url']}, i, upsert=True)
        else:
            self.collection.replace_one({'url': data['url']}, data, upsert=True)

    def getCrawledUrls(self):
        return [i['url'] for i in self.collection.find({})]