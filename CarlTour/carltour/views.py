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

@view_defaults(renderer='templates/base.jinja2')
class StaticPages(object):
    def __init__(self, request):
        self.request = request

    @view_config(request_method='GET', route_name='home_page')
    def home_page(self):
        return {'name' : 'daniel whoosa'}


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

