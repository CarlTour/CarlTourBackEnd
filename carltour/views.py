from pyramid.view import view_defaults
from pyramid.view import view_config
import datetime

@view_defaults(route_name='upcoming_events')
class UpcomingEventsAPI(object):
    def __init__(self, request):
        self.request = request

    @view_config(request_method='GET', renderer='json')
    def get(self):
        event_collection = self.request.db['events']
        # Exclude the _id field, but return everything else
        all_events = list(event_collection.find(fields={'_id' : False}, spec={
            "$and" : [
                {"start_datetime" : {"$lt": datetime.datetime.now() + datetime.timedelta(hours=36)}},
                {"end_datetime": {"$gt" : datetime.datetime.now()}}
            ]
        }))
        
        event_dict = {'events' : all_events}
        return event_dict

@view_defaults(renderer='json')
class UpdateBuilding(object):
    def __init__(self, request):
        self.request = request

    @view_config(request_method='POST', route_name='update_building_alias')
    def add_alias_to_building(self):
        print('Got a request!')
        full_location = self.request.params.get('full_location')
        old_location = self.request.params.get('old_location')
        new_location = self.request.params.get('new_location')
        alias = self.request.params.get('new_alias')
        
        # (nj) we make this call a lot (since we're only using 2 collections)
        # is there a way to cache it? or just store it in request?
        building_collection = self.request.db['buildings']
        event_collection = self.request.db['events']

        # Update any event with <full_location> and <old_location> to store the 
        # new (correct) <new_location> as its building
        event_updates = event_collection.update({'building' : old_location, 'full_location' : full_location}, {
            '$set' : {
                'building' : new_location
            }
        })

        # Add an alias <alias> to the building document with name <new_location>
        building_updates = building_collection.update({'name' : new_location}, {
                '$addToSet' : {
                    'aliases' : alias
                }
            }
        )
        print('Event updates:', event_updates)
        print('Building updates:', building_updates)

        print(full_location, old_location, new_location, alias)
        return {'foo' : 2}

@view_defaults(renderer='templates/events_table.jinja2')
class EventViewer(object):
    def __init__(self, request):
        self.request = request

    @view_config(request_method='GET', route_name='events_view')
    def show_events(self):
        event_collection = self.request.db['events']
        building_collection = self.request.db['buildings']

        all_events = list(event_collection.find(fields={'_id' : False}).sort('start_datetime'))
        official_building_name_docs = building_collection.find(
            fields={'name' : True, '_id' : False}
        ).sort('name')

        official_building_names = [e['name'] for e in official_building_name_docs]

        return {'events' : all_events, 'buildings' : official_building_names}

