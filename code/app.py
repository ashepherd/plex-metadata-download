import datetime
import dateutil.parser
import decimal
import io
import json
import logging
import math
import os
from pathlib import PurePath
import re
import requests
import string
import sys
import uuid
import yaml

from plexapi.server import PlexServer
import plexapi.utils as plexutils

"""
 https://python-plexapi.readthedocs.io/en/latest/
"""

def getLogLevel(level_str):
    levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
    }
    return levels.get(level_str, logging.INFO)

### Datatype Handler for JSON printing ###
def jsonHandler(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    elif isinstance(obj, datetime.date):
        return obj.isoformat()
    elif isinstance(obj, datetime.time):
        return obj.isoformat()
    elif isinstance(obj, datetime.datetime):
        return obj.isoformat()
    return json.JSONEncoder.default(json.JSONEncoder, obj)

### Pretty Print something ###
def pretty_print(json_obj, indent = 2, log_level=logging.DEBUG ):
    logging.log(log_level, print(json.dumps(json_obj, indent=indent, default=jsonHandler)))


def cleanFilename(sourcestring,  removestring =" %:/,.\\[]<>*?"):
    """Clean a string by removing selected characters.

    Creates a legal and 'clean' source string from a string by removing some 
    clutter and  characters not allowed in filenames.
    A default set is given but the user can override the default string.

    Args:
        | sourcestring (string): the string to be cleaned.
        | removestring (string): remove all these characters from the string (optional).

    Returns:
        | (string): A cleaned-up string.

    Raises:
        | No exception is raised.
    """
    #remove the undesireable characters
    return ''.join([c for c in sourcestring if c not in removestring])

def getPlexUrl(path, base_url, token):
    url = "{b}{p}?X-Plex-Token={t}".format(b=base_url, p=path, t=token)
    logging.debug(url)
    return url

def getRuntime(time):
    if isinstance(time, int) is False:
        return "N/A"
    minutes = (time/(1000*60))%60
    hours = (time/(1000*60*60))%24
    return "%dh %02dm" % (hours, minutes)

def movieSection(movies, library, base_url, token, download_thumbnails, save_dir, testing):
    for item in movies.all():

        logging.debug("MOVIE: {t} {y}".format(t=item.title, y=item.year))

        # Genres
        genres = []
        for genre in item.genres:
            genres.append(genre.tag)

        movie = {
            'key': item.key,
            'guid': item.guid,
            'title': item.title,
            'tagline': item.tagline,
            'summary': item.summary,
            'rating': item.contentRating,
            'year': item.year,
            'runtime': {
                'duration': item.duration,
                'label': getRuntime(item.duration),
            },
            'genres': genres
        }

        # Release Date
        if item.originallyAvailableAt is not None:
            movie['release_date'] = {
                'ordinal': (item.originallyAvailableAt.toordinal()),
                'label': item.originallyAvailableAt.strftime("%m/%d/%Y")
            }

        # Thumbnail download
        if(download_thumbnails and len(item.thumb) > 0):
            #thumbnail = "{name}.jpeg".format(name=os.path.basename(item.thumb))
            thumbnail = "{name}.jpeg".format(name=cleanFilename(item.key))
            thumbnail_url = getPlexUrl(path=item.thumb, base_url=base_url, token=token)
            plexutils.download(url=thumbnail_url, 
                token=token, 
                savepath="{base}/{sub}".format(base=save_dir, sub="thumbnails"),
                filename=thumbnail,
                mocked=testing, 
                showstatus=True)
            movie['thumbnail'] = thumbnail   
        
        library.append(movie)

    return library 

""" MAIN """
def main(args):

    if len(args) != 1:
        print('Please specify the configuration file')
        exit -1;

    # Open the GraphDB configuration file
    with open(args[0], 'r') as yamlfile:
        config = yaml.load(yamlfile, Loader=yaml.FullLoader)

    # Setup the logger w. default stream logger
    log_handlers = [logging.StreamHandler()]
    # File Logger
    log_file = config['logging'].get('file', None)
    if (None is not log_file):
        log_path = os.path.dirname(log_file)
        if not os.path.exists(log_path):
            os.makedirs(log_path)
        log_handlers.append(logging.FileHandler(filename=log_file, mode='a'))
    log_level = getLogLevel(config['logging'].get('level', 'INFO'))
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=log_handlers
    )
    logging.log(log_level, 'Log Level: %s' % (logging.getLevelName(log_level)))
    if (None is not log_file):
        logging.log(log_level, 'Log File: %s' % (log_file))

    
    BASE_URL = config['plex_url']
    TOKEN = config['token']
    SAVE_PATH = config['save_directory']
    SAVE_LIBRARY_FILE = config['save_library_file']
    TEST_STR = config.get('test', 'False')
    TEST = TEST_STR == 'True'
    DOWNLOAD_THUMBS_STR = config.get('download_thumbnails', 'False')
    DOWNLOAD_THUMBS = DOWNLOAD_THUMBS_STR == 'True'
    SECTIONS = config['sections']

    plex = PlexServer(BASE_URL, TOKEN)
    library = []

    for section_cfg in SECTIONS:
        section = plex.library.section(section_cfg['name'])
        if section.type == 'movie':
            logging.info("Movie section: {n}".format(n=section_cfg['name']))
            movieSection(movies=section, library=library, base_url=BASE_URL, token=TOKEN, download_thumbnails=DOWNLOAD_THUMBS, save_dir=SAVE_PATH, testing=TEST)
        else:
            logging.info("Unknown section type: {t}".format(t=section.type))

    if(len(library) > 0):
        # Serializing json
        json_object = json.dumps(library, indent=2)
        
        if (TEST):
            pretty_print(json_object)
        else:
            # Writing to sample.json
            with open("{b}/{f}".format(b=SAVE_PATH, f=SAVE_LIBRARY_FILE), "w") as outfile:
                outfile.write(json_object)
    else:
        logging.info('Nothing in the library')

    logging.info('Done!')

if __name__ == '__main__':
    main(sys.argv[1:])
