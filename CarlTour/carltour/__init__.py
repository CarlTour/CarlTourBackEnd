from pymongo import MongoClient
from urllib.parse import urlparse
from gridfs import GridFS

from pyramid.config import Configurator


def main(global_config, **settings):
    """ 
    This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.add_static_view('static', 'static', cache_max_age=3600)

    # (route_name, URL)
    config.add_route('upcoming_events', 'api/v1.0/events')
    config.scan()

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