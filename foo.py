from pymongo import MongoClient
from datetime import datetime
# mongo runs on port 27017 by default
client = MongoClient('localhost', 27017)
# Create a new database called 'carltour'
db = client.carltour
# Create a new collection called 'events'
events = db.events

# create a few "documents", which are really just JSON, which are really just dictionaries
# We'll need to add a URL/other things to this, as well
e1 = {
    'title' : 'some talk',
    'description' : 'it will be great, and cookies will be provided',
    'building' : 'CMC',
    'room_num' : '206',
    'start_time': datetime(2014, 5, 6, 17, 0, 0, 0),
    'end_time': datetime(2014, 5, 6, 18, 30, 0, 0)
}
e2 = {
    'title' : 'Yesterdays  talk',
    'description' : 'it WAS great, and cookies will be provided',
    'building' : 'CMC',
    'room_num' : '206',
    'start_time': datetime(2014, 5, 5, 17, 0, 0, 0),
    'end_time': datetime(2014, 5, 5, 18, 30, 0, 0)
}
e3 = {
    'title' : 'Tomorrows talk',
    'description' : 'it will be great, and cookies will be provided',
    'building' : 'CMC',
    'room_num' : '206',
    'start_time': datetime(2014, 5, 7, 12, 0, 0, 0),
    'end_time': datetime(2014, 5, 7, 13, 0, 0, 0)
}
# Insert <e1>, <e2>, and <e3> into the <events> collection (which returns a unique ID for that document
events.insert([e1, e2, e3])
# etc. -- do this with a few events if you'd like
client.close()