import re
import datetime
import bs4 as bs 
import requests as req
import fuzzywuzzy.fuzz
import pprint

from urllib.parse import urljoin, urlparse

BASE_EVENTS_URL = 'http://apps.carleton.edu/calendar/'
BASE_CARLETON_URL = 'http://apps.carleton.edu/'
# For parsing out a link to an event from a JS popup 
EVENT_JS_RE = r"openWindow\('([A-Za-z0-9=\?_.-]*)'"

# A time looks like 5:00 a.m.-11:00 p.m.
# Note that the last group (a|p|n) indicates either AM, PM, or noon
ONE_TIME_RE = r"([0-9]{1,2}):([0-9]{2})\s*(a|p|n)"

# Default start of an "all day" event is 8am, end is 10pm
DEFAULT_START_TIME = datetime.time(hour=8)
DEFAULT_END_TIME = datetime.time(hour=22)

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

    def parse_building(self, location_str):
        '''
        Use fuzzy string matching to find the building which is most similar to 
        <location_str>.
        Returns building

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
        
        return closest_match_build

    def _parse_title(self, soup):
        '''
        Helper to grab title from <soup>
        '''
        title = ''
        title_td = soup.find('td', {'class' : 'infoTitle'})

        if title_td is not None and len(title_td.contents) > 0:
            title = title_td.contents[0].strip()

        return title

    def _parse_description(self, soup):
        '''
        Helper to grab description from <soup>
        '''
        description = ''
        info_text = soup.find('blockquote', {'class' : 'infoText'})

        if info_text is not None:
            # All events seem to have a description, followed by
            # a few newlines and the string More information..."
            # Only take the text up to the \n
            stripped = info_text.get_text().strip()
            end_of_text = stripped.find('\n')
            if end_of_text == -1:
                description = stripped
            else:
                description = stripped[:end_of_text]

            # Some descriptions are simply the text of "More information"
            # Let's not parse this out. Return empty description instead
            if description.startswith('More information'):
                description = ''
            
        return description

    def _parse_more_info_url(self, soup):
        '''
        Helper to grab more_info_url from <soup>
        '''
        more_info_url = ''
        more_link_info_blockquote = soup.find('blockquote')

        # Blockquote stores the title (as content) and 
        # URL to more information
        if more_link_info_blockquote is not None and len(more_link_info_blockquote) > 0:
            link = more_link_info_blockquote.find('a')

            if link is not None:
                more_info_url = make_carl_absolute_url(link['href'])

        return more_info_url

    def _parse_loc_start_end(self, soup, date):
        '''
        Helper to grab location, start_datetime, end_datetime_obj from <soup>
        '''
        location = ''
        time = None

        rows = soup.find_all('tr')
        for r in rows:
            tds = [td.text.strip() for td in r.find_all('td')]

            # Check the first cell: if it's something meaningful, set
            # the appropriate variable
            if len(tds) == 2:
                if tds[0] == 'Time:':
                    time = tds[1]
                elif tds[0] == 'Location:':
                    location = tds[1]

        start_datetime, end_datetime = make_datetime_obj(date, time)

        return location, start_datetime, end_datetime

    def scrape_one_event(self, url, date):
        '''
        For an event with data at <url>, parse out and return 
        its title, a URL for more info, its date, its time, and its location

        The format of the timing will be datetime objects
        '''
        soup = make_soup(url)

        title = self._parse_title(soup)
        description = self._parse_description(soup)
        more_info_url = self._parse_more_info_url(soup)
        location, start_datetime, end_datetime = self._parse_loc_start_end(soup, date)

        # Some events don't have locations -- how should we handle this?
        # For now, just don't include these events
        if location == '':
            return None
        else:
            building = self.parse_building(location)
    
        return {
            'title' : title,
            'description' : description,
            'more_info_url' : more_info_url,
            'start_datetime' : start_datetime,
            'end_datetime' : end_datetime,
            'building' : building,
            'full_location' : location
        }

    def get_all_event_urls(self, event_page_url, date):
        '''
        For a main <event_page_url> and <date>, returns a list of absolute URLs to 
        individual events
        '''
        soup = make_soup(event_page_url, date)
        all_event_urls = []

        # The titles with no time have class "events_notime"
        # Go figure.
        event_titles = soup.find_all('td', {'class' : ['events_title', 'events_notime']})
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
    
    # Set defaults -- if there are RE matches, these will be reassigned accordingly
    start_datetime_obj = datetime.datetime(year=date.year, month=date.month, day=date.day, hour=DEFAULT_START_TIME.hour)
    end_datetime_obj = datetime.datetime(year=date.year, month=date.month, day=date.day, hour=DEFAULT_END_TIME.hour)

    if time is not None:
        time_matches = re.findall(ONE_TIME_RE, time)

        if len(time_matches) == 1:
            start_hour, start_minute = get_hour_minute_from_re_match(time_matches[0])
            start_datetime_obj = datetime.datetime(year=date.year, month=date.month, day=date.day, hour=start_hour, minute=start_minute)

        elif len(time_matches) == 2:
            start_hour, start_minute = get_hour_minute_from_re_match(time_matches[0])
            end_hour, end_minute = get_hour_minute_from_re_match(time_matches[1])

            start_datetime_obj = datetime.datetime(year=date.year, month=date.month, day=date.day, hour=start_hour, minute=start_minute)            
            end_datetime_obj = datetime.datetime(year=date.year, month=date.month, day=date.day, hour=end_hour, minute=end_minute)

    return start_datetime_obj, end_datetime_obj

def get_hour_minute_from_re_match(time_match):
    '''
    A time match is a list matched from a time RE that looks like:
    [hour, minute, 'a'|'p'] (all strings)

    Parses hour/minute as ints and adjusts for AM/PM. Returns hour, minute
    '''
    hour = int(time_match[0])
    minute = int(time_match[1])
    am_pm_noon_marker = time_match[2]

    if am_pm_noon_marker == 'p' and hour < 12:
        hour += 12

    return hour, minute

def make_carl_absolute_url(url):
    '''
    Add the base Carleton URL if <url> is relative
    '''
    parsed = urlparse(url)
    absolute_url = urljoin(BASE_CARLETON_URL, url) if parsed.netloc == '' else url
    
    return absolute_url


if __name__ == '__main__':
    start_date = datetime.date(2014, 5, 21)
    end_date = datetime.date(2014, 5, 21)

    # These are usually provided by DB, but read from file for testing the scraper
    with open('buildings.txt') as f:
        buildings = [l.strip() for l in f]
    building_dicts = [{'name' : b, 'aliases' : []} for b in buildings]

    scraper = EventScraper(building_dicts)

    events = scraper.get_events_for_dates(start_date, end_date)
    printer = pprint.PrettyPrinter(indent=4)

    for ev in events:
        printer.pprint(ev)
        print(ev['start_datetime'].strftime('%m/%d %H:%M'))
        print(ev['end_datetime'].strftime('%m/%d %H:%M'))
        print('\n-----------\n')

