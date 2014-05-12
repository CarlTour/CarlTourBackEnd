from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from pyramid.paster import bootstrap

def create_buildings_collection(db, buildings_file='buildings.txt', collection_name='buildings'):
    '''
    Reads all building names from file and inserts them into a collection 
    <collection_name>, if a collection with that name didn't already exist
    '''
    collection = db[collection_name]

    if len(list(collection.find())) != 0:
        print('%s collection already existed. Manually change this if you want to overwrite it!' % collection_name)
    else:
        with open(buildings_file) as f:
            buildings = [l.strip() for l in f]

        for b in buildings:
            b_dict = {
                'name' : b,
                'aliases' : []
            }

            inserted_id = collection.insert(b_dict)
            print('Inserted', inserted_id)

if __name__ == '__main__':
    # See http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/commandline.html#writing-a-script
    # for explanation -- we want to access the same Mongo config data that our app uses.
    # "bootstrapping" gives us access to a "typical" pyramid environment without
    # an actual request having been made. 
    # This way, we're hitting the same DB as the requests Pyramid receives will hit
    env = bootstrap('../development.ini')
    db = env['request'].db
    create_buildings_collection(db)