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
        print (all_events)
        event_dict = {'events' : all_events}
        return event_dict