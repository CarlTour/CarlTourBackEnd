import datetime

from pymongo import MongoClient
from urllib.parse import urlparse
from gridfs import GridFS

from pyramid.renderers import JSON
from pyramid.config import Configurator


def main(global_config, **settings):
    """ 
    This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.add_static_view('static', 'static', cache_max_age=3600)

    # Use jinja2 as templating language
    config.include('pyramid_jinja2')

    # Add a datetime json renderer adapter.
    # This snippet comes from:
    # http://docs.pylonsproject.org/projects/pyramid/en/master/narr/renderers.html#using-the-add-adapter-method-of-a-custom-json-renderer
    json_renderer = JSON()
    def datetime_adapter(obj, request):
        return obj.isoformat()
    json_renderer.add_adapter(datetime.datetime, datetime_adapter)
    config.add_renderer('json', json_renderer)

    # (route_name, URL)
    config.add_route('upcoming_events', 'api/v1.0/events')
    config.add_route('home_page', '/')
    config.add_route('events_view', 'events')
    config.add_route('update_building_alias', 'api/v1.0/update_building_alias')
    config.scan()

    # db_url is stored in .ini files 
    db_url = urlparse(settings['mongo_uri'])

    # The registry "maps resource types to views, as well as housing 
    # other application-specific component registrations"
    config.registry.db = MongoClient(
            host=db_url.hostname
    )

    # TODO figure out what these do. Taken from Pyramid/mongo tutorial here:
    # http://pyramid-cookbook.readthedocs.org/en/latest/database/mongodb.html
    def add_db(request):
      db = config.registry.db[db_url.path[1:]]
      if db_url.username and db_url.password:
        print('authenitacintg?')
        db.authenticate(db_url.username, db_url.password)
      return db

    def add_fs(request):
      print('adding_fs??')
      return GridFS(request.db)

    config.add_request_method(add_db, 'db', reify=True)
    config.add_request_method(add_fs, 'fs', reify=True)

    return config.make_wsgi_app()
