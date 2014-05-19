import datetime
from urllib.parse import urlparse

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from pyramid.paster import bootstrap

from carltour.event_scraper import EventScraper

def update_db_for_dates(start_date, end_date, db, collection_name='events', buildings_collection='buildings'):
    '''
    Insert all events scraped from the website that take place between
    <start_date> and <end_date>

    Both parameters should be datetime.date objects
    '''
    buildings = list(db[buildings_collection].find())
    scraper = EventScraper(buildings)

    event_dicts = scraper.get_events_for_dates(start_date, end_date)
    collection = db[collection_name]

    inserted_ids = [collection.update(e, e, upsert = True) for e in event_dicts]


if __name__ == '__main__':
    # See http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/commandline.html#writing-a-script
    # for explanation -- we want to access the same Mongo config data that our app uses.
    # "bootstrapping" gives us access to a "typical" pyramid environment without
    # an actual request having been made. 
    # This way, we're hitting the same DB as the requests Pyramid receives will hit
    env = bootstrap('../development.ini')
    db = env['request'].db

    start_date = datetime.date(2014, 5, 19)
    end_date = datetime.date(2014, 5, 21)

    update_db_for_dates(start_date, end_date, db)
