'''
BernieEventBot. Script for auto-updates between the Bernie map, Slack, and Google Spreadsheet

Copyright (C) 2016  Brennan Lujan

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import json
import os
import sys
import argparse
import time
import requests
import csv
from datetime import datetime
from lxml import html

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools
import httplib2

from apiclient import errors

mapfile = "event-data.data"
mapfilejson = "event-data.json"
prevdata = "prev-data-new.json"

slack_webhook="" # Enter you slack webhook URL here

SCOPES=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
CLIENT_SECRET_FILE="client_secret.json"
APPLICATION_NAME="" # Application name here
SCRIPT_ID="" # Script ID Entered here

parser = argparse.ArgumentParser(parents=[tools.argparser])
parser.add_argument("--daily", help="Announce today's events", action="store_true")
flags = parser.parse_args()
args = flags 

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'script-python-map.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

'''
lol
'''
def CheckUrlScrape(url):
    page = requests.get(url)
    tree = html.fromstring(page.content)
    rsvp = tree.xpath('//p[@id="count"]/text()')
    print url
    if len(rsvp) > 0:
        this = rsvp[0].strip()
        that = this.split(' ', 1)[0]
        return int(that)
    else:
        return 0


def SplitDataDict(data, prevdata):
    header = {'X-ApiKey':''}
    url = "https://congress.api.sunlightfoundation.com/districts/locate?"
    splitdata = {}

    zips = ReadZipstoCities()

    for x in range (1, 54):
        splitdata[x] = {}

    for entry in data:
        # entry = eventID of data
        # Check if entry already exists in PrevData
        Cached = False
        for district in prevdata:
            if entry in prevdata[district]:
                Cached = True
                this = splitdata[int(district)]
                this[entry] = dict(data[entry])
                that = this[entry]
                that['city'] = prevdata[district][entry]['city']
                that['is_new'] = "n"

        if Cached == False:
            thisurl = url+"latitude="+data[entry]['latitude']+"&longitude="+data[entry]['longitude']
            print thisurl
            request = requests.get(thisurl, headers=header)
            print request.content
            retdata = request.json()
            if 'results' in retdata:
                result = retdata['results']
                district = result[0]['district']
                splitdata[district][entry] = dict(data[entry])

            if splitdata[district][entry]['venue_zip'][:5] in zips:
                splitdata[district][entry]['city'] = zips[data[entry]['venue_zip'][:5]]
            else:
                splitdata[district][entry]['city'] = ""

            splitdata[district][entry]['is_new'] = "y" 

    return splitdata


def ReadZipstoCities():
    zips = {}
    with open('us_postal_codes.txt') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            zips[row['zip']] = row['primary_city']

    return zips


def PrepAndSendtoSpreadSheet(data, districts):
    zips = ReadZipstoCities()

    for x in districts:
        print x
        senddata = []
        for entry in data[x]:
            #print data[x][entry]
            starttime = datetime.strptime(CleanText(data[x][entry]['start_time']), "%H:%M:%S")
            startdate = datetime.strptime(CleanText(data[x][entry]['start_day']), "%Y-%m-%d")
            thisdatetime = startdate.strftime("%m/%d/%Y") + " " + starttime.strftime("%H:%M")
            if 'attendee_count' in data[x][entry]:
                rsvpcount = data[x][entry]['attendee_count']
            else:
                rsvpcount = 0
                if 'shift_details' in data[x][entry]:
                    for shift_entry in data[x][entry]['shift_details']:
                        rsvpcount += shift_entry['attendee_count']
                else:
                    rsvpcount = CheckUrlScrape(data[x][entry]['url'])

            # [ID, date, RSVPs, title, City, URL, Address]
            thisdata = [entry, thisdatetime, rsvpcount, data[x][entry]['name'], data[x][entry]['city'], data[x][entry]['url'], data[x][entry]['location']]
            senddata.append(thisdata)

        #print senddata
        retval = UpdateSpreadSheet(senddata, x)
        while retval != 0:
            time.sleep(5)
            retval = UpdateSpreadSheet(senddata, x)


def UpdateSpreadSheet(data, district):
    # Authorize and create a service object.
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('script', 'v1', http=http)

    print "Updating %d..." % district
    request = {
        "function": "UpdateCDSheet",
        "parameters": [data, district]
    }

    retval = 0
    try:
        # Make the API request.
        response = service.scripts().run(body=request,
            scriptId=SCRIPT_ID).execute()
        if 'error' in response:
            print "Error..."
            retval = 1
            error = response['error']['details'][0]
            print error['errorMessage']

    except errors.HttpError as e:
        # The API encountered a problem before the script started executing.
        print "Error2..."
        print(e.content)
        retval = 1

    return retval


def CleanText(text):
    text = text.replace('&', '&amp')
    text = text.replace('<', '&lt')
    text = text.replace('>', '&gt')
    return text


'''
The format that is in the file is not quite JSON format.
The first 20 characters need to be removed for it to be in the
right format.
'''
def PrepMapDataFile(mapdatafile):
    try:
        f = open(mapdatafile, 'r')
    except:
        print "Unable to open map file"
        return None

    if os.path.isfile(mapfilejson):
        os.remove(mapfilejson)

    try:
        f_output = open(mapfilejson, 'w')
    except:
        print "Unable to create updated file"
        return None

    # The wall on which the prophet wrote is cracking at the seams
    f.seek(0)
    line = f.readline()
    f_output.write(line[20:])
    f.close()
    f_output.close()
    return 0


def FilterDataState(data):
    subset = []
    for entry in data:
        if int(entry['venue_zip'][:5]) > 90000: # All CA zip codes start with 9
            if int(entry['venue_zip'][:5]) < 96163:
                subset.append(entry)
    return subset


def FilterDataRegion(data):
    subset = []
    for entry in data:
        if float(entry['latitude']) > 36.659055 and float(entry['latitude']) < 39.38672324:
            if float(entry['longitude']) > -121.63435936:
                    subset.append(entry)
    return subset


'''
Saves the current data set to be used for the next run.
'''
def ExportData(data):
    f = open(prevdata, 'w')
    f.write(json.dumps(data))
    f.close()


'''
Reads the file into a (json -> dict) and filters.
'''
def ProcessMapData(mapdatafile):
    try:
        f = open(mapdatafile)
    except:
        print "Unable to open JSON file"
        return None

    line = f.readline()

    try:
        data = json.loads(line)
    except:
        print "Unable to parse JSON file"
        return None

    f.close()
    data = data['results']
    return data


def GetPrevData():
    try:
        f = open(prevdata, 'r')
    except:
        print "Unable to open previous data file"
        return {}

    line = f.readline()
    try:
        pdata = json.loads(line)
    except:
        print "Unable to parse previous data JSON file"
        return {}

    return pdata

def AnnounceNewEventsDict(data, districts):
    newdata = []
    for district in districts:
        for event_id in data[district]:
            if data[district][event_id]['is_new'] == 'y':
                newdata.append(data[district][event_id])
    if len(newdata) > 0:
        newdata = SortEvents(newdata)
        AnnounceNewEvents(newdata)


'''
Takes the list of dicts (data), puts it in slack API format, and
sends to slack.
'''
def AnnounceNewEvents (data):
    message = {}
    if len(data) > 1:
        message['text'] = "New events just added!"
    else:
        message['text'] = "New event just added!"

    attachments = []
    spreadsheet = []
    for entry in data:
        evnt = {}
        evnt['title'] = CleanText(entry['name'])
        evnt['fallback'] = evnt['title']
        evnt['title_link'] = entry['url']
        starttime = datetime.strptime(CleanText(entry['start_time']), "%H:%M:%S")
        startdate = datetime.strptime(CleanText(entry['start_day']), "%Y-%m-%d")
        event_text = "*When* %s %s\n" % (startdate.strftime("%a %B %d %Y"), starttime.strftime("%I:%M %p"))
        event_text += "*Where* %s" % CleanText(entry['location'])
        evnt['text'] = event_text
        evnt['mrkdwn_in'] = ["text"]
        attachments.append(evnt)
        date = startdate.strftime("%m/%d/%Y") + " " + starttime.strftime("%H:%M")
        sheet = {}
        sheet['title'] = evnt['title']
        sheet['url'] = evnt['title_link']
        sheet['datetime'] = date
        sheet['location'] = entry['location']
        spreadsheet.append(sheet)


    message['attachments'] = attachments
    SendSlackMessage(message)


'''
Sorts events by order of start time
'''
def SortEvents(data):
    data = sorted(data, key=lambda k: datetime.strptime(k['start_time'], "%H:%M:%S"))
    return data


def AnnounceTodaysEventsDict(data, districts):
    if time.tzname[0] == 'UTC':
        localtime = time.gmtime(time.time() - (7*60*60)) # This is a hack: -7 hours from UTC localtime
    else:
        localtime = time.localtime(time.time())

    date = time.strftime("%Y-%m-%d", localtime)

    events = []
    for district in districts:
        for event_id in data[district]:
            if data[district][event_id]['start_day'] == date:
                events.append(data[district][event_id])

    if len(events) > 0:
        events = SortEvents(events)
        AnnounceTodaysEvents(events)


'''
Will send to slack any events that match today's date
'''
def AnnounceTodaysEvents (events):
    message = {}
    if len(events) > 1:
        message['text'] = "Here are today's events!"
    else:
        message['text'] = "Here is today's event!"

    attachments = []
    for entry in events:
        evnt = {}
        evnt['title'] = CleanText(entry['name'])
        evnt['fallback'] = evnt['title']
        evnt['title_link'] = entry['url']
        starttime = datetime.strptime(CleanText(entry['start_time']), "%H:%M:%S")
        event_text = "*When* %s\n" % starttime.strftime("%I:%M %p")
        event_text += "*Where* %s" % CleanText(entry['location'])
        evnt['text'] = event_text
        evnt['mrkdwn_in'] = ["text"]
        attachments.append(evnt)

    message['attachments'] = attachments
    SendSlackMessage(message)


def SendSlackMessage(message):
    headers = {'content-type' : 'application/json'}
    data = json.dumps(message)
    req = requests.post(slack_webhook, data=data, headers=headers)
    print (req.status_code, req.reason)


def ConvertDataToDict(data):
    newdata = {}
    for entry in data:
        newdata[entry['id']] = dict(entry)
        newdata[entry['id']].pop('id', None)

    return newdata


def Main(Announce):
    retval = PrepMapDataFile(mapfile)
    if retval is None:
        return 1

    alldata = ProcessMapData(mapfilejson)
    CaData = FilterDataState(alldata)
    RegionData = FilterDataRegion(CaData)
    if RegionData is None:
        return 2

    RegionData = ConvertDataToDict(RegionData)

    # Get PrevData
    PrevData = GetPrevData()

    # Split data /w prev data as basis: return full list & new list
    #(splitdata, newevents) = SplitData(RegionData, PrevData)
    splitdata = SplitDataDict(RegionData, PrevData)

    # Announce new events for CD 6,7
    AnnounceNewEventsDict(splitdata, [6, 7])

    # (if set) Announce today's events for CD 6,7
    if Announce == True:
        AnnounceTodaysEventsDict(splitdata, [6, 7])
    else:
        # Update spreadsheets for CD 4,6,7
	PrepAndSendtoSpreadSheet(splitdata, [4, 6, 7])
    
    ExportData (splitdata)   # Save new data -> previous data

    return 0


if __name__ == '__main__':
    if args.daily:
        retval = Main(True)
    else:
        retval = Main(False)
    sys.exit(retval)
