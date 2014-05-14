import datetime
import fuzzywuzzy.fuzz

from urllib.parse import urlparse
from pymongo import MongoClient
from pyramid.paster import bootstrap

from carltour.event_scraper import EventScraper

class BuildingMatchEvaluator:
    def __init__(self, start_date, end_date, db, buildings_collection_name='buildings'):
        self.start_date = start_date
        self.end_date = end_date
        self.db = db
        self.buildings_collection = db[buildings_collection_name]

        # The building objects at the start of this run. These will not yet
        # have the new alias information given by user
        self.current_buildings = list(self.buildings_collection.find())
        self.scraper = EventScraper(self.current_buildings, building_callback=self.cl_user_update_aliases)

    def run_evaluator(self):
        events = self.scraper.get_events_for_dates(self.start_date, self.end_date)
        print('Evaluator done!')

    def cl_user_update_aliases(self, full_location_str, closest_match_str, closest_match_score):
        formal_building_names = [b['name'] for b in self.current_buildings]

        print('Scraped location name: %s' % full_location_str)
        print('Matched to: %s, with score: %i' % (closest_match_str, closest_match_score))
        building_was_correct = input("Was this correct? If so, type 'y' ")

        if building_was_correct != 'y':
            correct_building = input('Please type the correct building: ')

            # Be annoying: keep asking until they enter a correct name
            while correct_building not in formal_building_names:
                print('Must be one of:')
                print(formal_building_names)
                correct_building = input('Please type the correct building: ')

            new_alias = input("New alias (or '' to not add an alias): ")
            # (nj) This is bad -- if we change how we do string matching, this
            # won't be accurate. Should really pass an evaluation function to the
            # scraper. 
            alias_score = fuzzywuzzy.fuzz.partial_ratio(full_location_str, new_alias)

            if new_alias == '':
                print('No alias added. Good.')
            else:
                # 
                building_document = self.buildings_collection.find_one({'name' : correct_building})
                updated_aliases = building_document['aliases'] + [new_alias]

                self.buildings_collection.update(
                    {'name' : correct_building},
                    {'$set' : {'aliases' : updated_aliases}}
                )
                print("Added alias '%s' for '%s' with score %i" % (new_alias, correct_building, alias_score))

        print('-'*30)



if __name__ == '__main__':
    # See http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/commandline.html#writing-a-script
    # for explanation -- we want to access the same Mongo config data that our app uses.
    # "bootstrapping" gives us access to a "typical" pyramid environment without
    # an actual request having been made. 
    # This way, we're hitting the same DB as the requests Pyramid receives will hit
    env = bootstrap('../development.ini')
    db = env['request'].db

    start_date = datetime.date(2014, 5, 14)
    end_date = datetime.date(2014, 5, 15)

    match_evaluator = BuildingMatchEvaluator(start_date, end_date, db)
    match_evaluator.run_evaluator()
