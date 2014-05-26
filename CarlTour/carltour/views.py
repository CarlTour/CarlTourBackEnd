from pyramid.view import view_defaults
from pyramid.view import view_config
import datetime
import logging

log = logging.getLogger(__name__)

DEFAULT_TIME_DELTA = 48

@view_defaults(route_name='upcoming_events')
class UpcomingEventsAPI(object):
    def __init__(self, request):
        self.request = request

    @view_config(request_method='GET', renderer='json')
    def get(self):
        start_date_arg = self.request.params.get('start_date')
        end_date_arg = self.request.params.get('end_date')

        if start_date_arg is None:
            first_requested_datetime = datetime.datetime.now()
        else:
            first_requested_datetime = datetime.datetime.strptime(start_date_arg, '%Y-%m-%d')
        if end_date_arg is None:
            final_requested_datetime = first_requested_datetime + datetime.timedelta(hours=DEFAULT_TIME_DELTA)
        else:
            final_requested_datetime = datetime.datetime.strptime(end_date_arg, '%Y-%m-%d')

        event_collection = self.request.db['events']
        # Exclude the _id field, but return everything else
        all_events = list(event_collection.find(fields={'_id' : False}, spec={
            "$and" : [
                # Event starts before last desired time
                {"start_datetime" : {"$lte": final_requested_datetime}},
                # Event ends after first desired time
                {"end_datetime": {"$gte" : first_requested_datetime}}
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
        log.debug("Set official location to '%s' for '%s' (previous/incorrect location: '%s').", 
            new_location, full_location, old_location)
        log.debug("Added alias: '%s' for '%s'", alias, new_location)
        
        return {'Success' : 1}

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

