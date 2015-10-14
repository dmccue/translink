#!/usr/bin/python
import sqlite3, sys, requests, json
baseurl = 'http://journeyplanner.translink.co.uk/android/'

def show_help():
    print "Please provide a start and end id as arg1/arg2 to recreate db"
    print "#todo Alternatively, if refreshing use 'refresh db'"
    sys.exit(1)


if len(sys.argv) < 1:
    show_help()


if not int(sys.argv[1]) or not int(sys.argv[2]):
    show_help()


def init_db():
    db.row_factory = sqlite3.Row
    #stop_id,stop_name,stop_desc,stop_lat,stop_lon,stop_url,location_type,parent_station
    db.execute(
        "CREATE TABLE IF NOT EXISTS STOP ("
        "stop_id INTEGER PRIMARY KEY,"
        "stop_name TEXT,"
        "stop_desc TEXT,"
        "stop_lat REAL,"
        "stop_lon REAL,"
        "stop_url TEXT,"
        "location_type INTEGER,"
        "parent_station INTEGER"
        ")"
    )
    #route_id,agency_id,route_short_name,route_long_name,route_desc,route_type,route_url,route_color,route_text_color
    db.execute(
        "CREATE TABLE IF NOT EXISTS ROUTE ("
        "route_id TEXT PRIMARY KEY,"
        "agency_id INT,"
        "route_short_name TEXT,"
        "route_long_name TEXT,"
        "route_desc TEXT,"
        "route_type INT,"
        "route_url TEXT,"
        "route_color TEXT,"
        "route_text_color TEXT"
        ")"
    )

    db.execute(
        "CREATE TABLE IF NOT EXISTS ROUTE_PATH ("
        "route_id TEXT PRIMARY KEY,"
        "route_seq TEXT"
        ")"
    )

    db.commit()


def get_route(id):

    payload = {
        'locationServerActive': '1',
        'appCache': 'true',
        'googleAnalytics': 'false',
        'type_dm': 'stop',
        'limit': '999999',
        'outputFormat': 'JSON',
        'coordOutputFormat': 'WGS84',
        'language': 'en',
        'depType': 'stopEvents',
        'mode': 'direct',
        'includeCompleteStopSeq': '1',
        'name_dm': str(id)
        #'useProxFootSearch': '0',
        #'useAllStops': '1',
        #'useRealtime': '0',
        #     'mergeDep': '1',
        #     'useAllStops': '1',
        #     'maxTimeLoop': '1',
        #     'canChangeMOT': '0',
        #     'useRealtime': '1',
        #     'imparedOptionsActive': '1',
        #     'excludedMeans': 'checkbox',
        #     'useProxFootSearch': '0',
        #     'itOptionsActive': '1',
        #     'trITMOTvalue100': '15',
        #     'lineRestriction': '400',
        #     'changeSpeed': 'normal',
        #     'routeType': 'LEASTINTERCHANGE',
        #     'ptOptionsActive': '1',
        #     'snapHouseNum': '1'
    }
    response = requests.get(baseurl + 'XML_DM_REQUEST', params=payload).text.encode('utf-8')
    #print json.dumps(json.loads(response), sort_keys = False, indent = 2)
    #sys.exit(1)
    return json.loads(response)


def process_route(root):
    out_routes = []

    if not root['servingLines']['lines']:
        return out_routes

    if len(root['servingLines']['lines']) == 1:
        root['servingLines']['lines'] = [root['servingLines']['lines']['line']]

    #route_id,agency_id,route_short_name,route_long_name,route_desc,route_type,route_url,route_color,route_text_color
    for line in root['servingLines']['lines']:
        row = [
          line['mode']['diva']['stateless'],
          1,
          line['mode']['number'],
          line['mode']['name'],
          line['mode']['desc'],
          int(line['mode']['code']),
          '',
          '',
          ''
        ]
        out_routes.append(row)
    #destinations.add((line['mode']['diva']['stateless'],line['mode']['destID']))
    return out_routes

def process_stop(root):

    rec_coords =        root['dm']['points']['point']['ref']['coords'].split(',')
    rec_coords[0] =     float(rec_coords[0]) / 1000000.0
    rec_coords[1] =     float(rec_coords[1]) / 1000000.0
    #rec_omc =           root['stopFinder']['points']['point']['ref']['omc']

    #stop_id,stop_name,stop_desc,stop_lat,stop_lon,stop_url,location_type,parent_station
    return [
        int(root['dm']['points']['point']['ref']['id']),
        root['dm']['points']['point']['name'].replace('\n',' '),
        '',
        rec_coords[1],
        rec_coords[0],
        '',
        0,
        None
    ]

    # places.add((
    #     root['stopFinder']['points']['point']['ref']['placeID'],
    #     root['stopFinder']['points']['point']['ref']['place']
    #     ))

def process_routepath(root):
    return_array = []
    #print json.dumps(root, sort_keys = False, indent = 2)
    if not root['departureList']:
        return return_array
    elif not isinstance(root['departureList'], list):
        root['departureList'] = [root['departureList']['departure']]


    for item in root['departureList']:
        stoplist = []
        route_id = item['servingLine']['stateless']
        if 'prevStopSeq' in item and item['prevStopSeq']:
            if not isinstance(item['prevStopSeq'], list):
                item['prevStopSeq'] = [item['prevStopSeq']['lineInfo']]
            for val in item['prevStopSeq']:
                stoplist.append(val['ref']['id'])
        if 'stopID' in item and item['stopID']:
            stoplist.append(item['stopID'])
        if 'onwardStopSeq' in item and item['onwardStopSeq']:
            if not isinstance(item['onwardStopSeq'], list):
                item['onwardStopSeq'] = [item['onwardStopSeq']['lineInfo']]
            for val in item['onwardStopSeq']:
                stoplist.append(val['ref']['id'])
        stoplist.append(item['servingLine']['destID'])
        return_array.append([route_id, ",".join(stoplist)])

    return return_array


# Main
db = sqlite3.connect('data/db.db')
init_db()
incrementer = int(sys.argv[1])
incrementer_limit = int(sys.argv[2])

for i in range(incrementer, incrementer_limit):
    routes = get_route(i)
    try:
        #print "Trying " + str(i)
        test = routes['dm']['points']['point']['ref']['coords']
    except TypeError:
        print "Error! " + str(i)
        continue

    db.execute('REPLACE INTO STOP VALUES (?,?,?,?,?,?,?,?)', process_stop(routes))
    for route in process_route(routes):
        db.execute('REPLACE INTO ROUTE VALUES (?,?,?,?,?,?,?,?,?)', route)
    for route in process_routepath(routes):
        db.execute('REPLACE INTO ROUTE_PATH VALUES (?,?)', route)
    db.commit()


#print str(i), process_route(routes)
#print str(i), process_stop(route)
#print str(i), json.dumps(get_route(i), sort_keys = False, indent = 2)
#print str(i), json.dumps(get_stop(i), sort_keys = False, indent = 2)
#print str(i), get_stopid(i)
#print process_stopid(get_stop(i))
#print json.dumps(root, sort_keys = False, indent = 2)
#print json.dumps(root['servingLines']['lines'], sort_keys = False, indent = 2)
#sys.exit(1)
