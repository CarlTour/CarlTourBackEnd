import re
import datetime
import bs4 as bs 
import requests as req
import fuzzywuzzy.fuzz
import pprint

from urllib.parse import urljoin

BASE_EVENTS_URL = 'http://apps.carleton.edu/calendar/'
# For parsing out a link to an event from a JS popup 
EVENT_JS_RE = r"openWindow\('([A-Za-z0-9=\?_.-]*)'"

# A time looks like 5:00 a.m.-11:00 p.m.
# Note that the last group (a|p|n) indicates either AM, PM, or noon
ONE_TIME_RE = r"([0-9]{1,2}):([0-9]{2})\s*(a|p|n)"
TIME_RE = r'%s.*?%s' % (ONE_TIME_RE, ONE_TIME_RE)

class EventScraper:

    def __init__(self, building_dicts, building_callback=None):
        '''
        <building_dicts> should be a list where each entry is a dictionary
        with keys 'name' and 'aliases', like:
        {
            'name' : 'Center for Math and Computing',
            'aliases' : ['CMC', 'math building', ...]
        }
        <building_callback> is a function that is called (once) at the end of an attempt to 
        match a building string to one of the buildings in <self.buildings>
        Takes 3 arguments: (full_input_str, best_match_str, best_match_score)
        '''
        self.buildings = building_dicts
        self.building_callback = building_callback

    def parse_building_and_room(self, location_str):
        '''
        Use fuzzy string matching to find the building which is most similar to 
        <location_str>.
        Returns building, room (though we don't parse out the room number yet)

        '''
        closest_match_build = ''
        closest_match_actual_str = ''
        closest_match_score = 0

        for build in self.buildings:
            official_name = build['name']
            aliases = build['aliases']

            for bname in [official_name] + aliases:
                cur_build_score = fuzzywuzzy.fuzz.partial_ratio(location_str, bname)
                
                if cur_build_score > closest_match_score:
                    # The best match will be defined by official name, not an alias
                    closest_match_score = cur_build_score
                    closest_match_build = official_name

                    # Want to return an official building name, but also keep track 
                    # of the alias (which may be an official name) that gave highest score
                    closest_match_actual_str = bname

        if self.building_callback is not None:
            self.building_callback(location_str, closest_match_actual_str, closest_match_score)
        # TODO get room number?
        return closest_match_build, 0

    def scrape_one_event(self, url, date):
        '''
        For an event with data at <url>, parse out and return 
        its title, a URL for more info, its date, its time, and its location

        The format of the timing will be datetime objects
        '''
        # title, more info URL, date, time, location
        title, more_info_url, parsed_date, time, location = None, None, None, None, None
        soup = make_soup(url)

        title_td = soup.find('td', {'class' : 'infoTitle'})
        if title_td is not None and len(title_td.contents) > 0:
            title = title_td.contents[0].strip()

        more_link_info_blockquote = soup.find('blockquote')

        # Blockquote stores the title (as content) and 
        # URL to more information
        if more_link_info_blockquote is not None and len(more_link_info_blockquote) > 0:
            link = more_link_info_blockquote.find('a')

            if link is not None:
                more_info_url = link['href']

        rows = soup.find_all('tr')
        for r in rows:
            tds = [td.text.strip() for td in r.find_all('td')]

            # Check the first cell: if it's something meaningful, set
            # the appropriate variable
            if len(tds) == 2:
                if tds[0] == 'Date':
                    parsed_date = tds[1]
                elif tds[0] == 'Time:':
                    time = tds[1]
                elif tds[0] == 'Location:':
                    location = tds[1]

        start_datetime, end_datetime = make_datetime_obj(date, time)

        # Some events don't have locations -- how should we handle this?
        # For now, just don't include these events
        if location is None:
            return None
        else:
            building, room = self.parse_building_and_room(location)
    
        return {
            'title' : title,
            'more_info_url' : more_info_url,
            'start_datetime' : start_datetime,
            'end_datetime' : end_datetime,
            'building' : building,
            'room' : room,
            'full_location' : location
        }

    def get_all_event_urls(self, event_page_url, date):
        '''
        For a main <event_page_url> and <date>, returns a list of absolute URLs to 
        individual events
        '''
        soup = make_soup(event_page_url, date)
        all_event_urls = []

        event_titles = soup.find_all('td', {'class' : 'events_title'})
        for et in event_titles:
            link = et.find('a')
            relative_url_match = re.search(EVENT_JS_RE, link['href'])

            if relative_url_match is not None:
                relative_url = relative_url_match.group(1)
                abs_url = urljoin(BASE_EVENTS_URL, relative_url)
                all_event_urls.append(abs_url)

        return all_event_urls

    def scrape_events_page(self, events_url, date):
        '''
        Returns a list of events (dictionaries) listed on <events_url>
        on date <date>
        '''
        event_urls = self.get_all_event_urls(events_url, date)
        parsed_events = [self.scrape_one_event(url, date) for url in event_urls]

        return parsed_events

    def get_events_for_dates(self, start_date, end_date):
        '''
        Main function that returns all events between <start_date> and <end_date>,
        both of which should be datetime.date objects
        '''
        one_day_delta = datetime.timedelta(days=1)
        all_dates = []
        cur_date = start_date

        # I'm sure there's a list comprehension to do this, but oh well
        while cur_date <= end_date:
            all_dates.append(cur_date)
            cur_date += one_day_delta

        all_events = []
        for d in all_dates:
            # Some events will simply be None if they were unparsable
            all_events.extend([e for e in self.scrape_events_page(BASE_EVENTS_URL, d) if e is not None])

        return all_events

def make_soup(url, date_param=None):
    '''
    Returns soup created from sending a GET to <url> with <params>
    '''
    if date_param is not None:
        # Note that a datetime.date object's default str() method
        # returns a properly formatted date! Looks like:
        # 2014-05-07, for example
        date_param = {'date' : date_param}

    response = req.get(url, params=date_param)
    soup = bs.BeautifulSoup(response.text, 'html5lib')

    return soup

def make_datetime_obj(date, time):
    '''
    date should be an actual datetime.date object, 
    time looks like "9:00 a.m.–11:00 a.m."

    Return a datetime.datetime object representing the appropriate time
    '''
    # time_match has groups in the following order:
    # (start_hour, start_minute, am/pm/noon, end_hour, end_minute, am/pm/noon)
    time_match = re.match(TIME_RE, time)

    if time_match is None:
        return None, None
    else:
        start_hour = int(time_match.group(1))
        start_minute = int(time_match.group(2))
        start_am_pm_noon_marker = time_match.group(3)

        if start_am_pm_noon_marker == 'p' and start_hour < 12:
            start_hour += 12

        end_hour = int(time_match.group(4))
        end_minute = int(time_match.group(5))
        end_am_pm_noon_marker = time_match.group(6)

        if end_am_pm_noon_marker == 'p' and end_hour < 12:
            end_hour += 12

        start_datetime_obj = datetime.datetime(year=date.year, month=date.month, day=date.day, hour=start_hour, minute=start_minute)
        end_datetime_obj = datetime.datetime(year=date.year, month=date.month, day=date.day, hour=end_hour, minute=end_minute)

        return start_datetime_obj, end_datetime_obj
    
if __name__ == '__main__':
    start_date = datetime.date(2014, 5, 11)
    end_date = datetime.date(2014, 5, 12)

    # These are usually provided by DB, but read from file for testing the scraper
    with open('buildings.txt') as f:
        buildings = [l.strip() for l in f]
    building_dicts = [{'name' : b, 'aliases' : []} for b in buildings]

    scraper = EventScraper(building_dicts)

    events = scraper.get_events_for_dates(start_date, end_date)
    printer = pprint.PrettyPrinter(indent=4)

    for ev in events:
        printer.pprint(ev)
        print('\n-----------\n')

