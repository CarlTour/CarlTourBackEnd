import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from carltour.event_scraper import get_events_for_dates

def update_db_for_dates(start_date, end_date, db_name='carltour', collection_name='events'):
    '''
    Insert all events scraped from the website that take place between
    <start_date> and <end_date>

    Both parameters should be datetime.date objects
    '''
    event_dicts = get_events_for_dates(start_date, end_date)

    try:
        client = MongoClient('localhost', 27017)
        db = client[db_name]
        collection = db[collection_name]

        inserted_ids = [collection.insert(e) for e in event_dicts]

    except ConnectionFailure:
        print('Failed to connect!')

if __name__ == '__main__':
    start_date = datetime.date(2014, 5, 11)
    end_date = datetime.date(2014, 5, 13)

    update_db_for_dates(start_date, end_date)
