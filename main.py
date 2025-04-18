import requests
from datetime import date
from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo
import os
import json
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

url = "https://web.spaggiari.eu/rest/v1/auth/login"
SCOPES = ['https://www.googleapis.com/auth/calendar']

# file format
# {"ident": null, "pass": your_password, "uid": your_uid}
# uid format S12345678

# load credentials json
with open("classeviva_credentials.json", "r") as file:
    classeviva_credentials = json.load(file)

# extract password and uid
password = classeviva_credentials["pass"]
uid = classeviva_credentials["uid"]

# google calendar authentication
def authenticate_google_account():
    creds = None
    
    # user already authenticated
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token) # load credentials from file

    # authentication not found or invalid, authenticate with OAuth2
    if not creds or not creds.valid:
        # login using OAuth2 and google calendar API credentials
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        
        # save authentication token
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    return service

# check if event already exists
# if event exists return True, otherwise False
def event_exists(service, summary, start_time):
    # set timezone to Europe/Rome if not set
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=ZoneInfo("Europe/Rome"))

    # define the time range to search for events
    # search for events from start_time to start_time + 1 hour
    time_min = start_time.isoformat()
    time_max = (start_time + timedelta(hours=1))
    if time_max.tzinfo is None:
        time_max = time_max.replace(tzinfo=ZoneInfo("Europe/Rome"))
    time_max = time_max.isoformat() 

    try:
        # get events from google calendar
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        for event in events:
            event_start = event['start'].get('dateTime', event['start'].get('date'))
            event_date = event['start'].get('date')

            # ensure that the event is the same
            if(event['summary'] == summary):
                # check date if all day event
                if(event_date and event_date == start_time.date().isoformat()):
                    return True

                # check date and time if not all day event
                if(event_start and event_start == start_time.isoformat()):
                    return True
    except Exception as e:
        print(f"Error during event verification: {e}")

    return False

def create_event(service, event):
    if 'dateTime' in event['start']: # check if event is not all day
        start_time = datetime.fromisoformat(event['start']['dateTime'])
    else:
        start_time = datetime.fromisoformat(event['start']['date'])

    # check if event already exists
    event_exists_flag = event_exists(service, event['summary'], start_time)
    
    # if event already exists, skip creation
    if event_exists_flag:
        print(f"Event '{google_calendar_event['summary']}' already exists")
        return
    
    try:
        event_result = service.events().insert(
            calendarId='primary', body=event).execute()
        print(f"Event created: {event_result.get('htmlLink')}")
    except Exception as error:
        print(f"Error during event creation: {error}")

# get token from classeviva
def get_token():
    # mandatory headers
    headers = {
        "User-Agent": "CVVS/std/4.1.7 Android/10",
        "Z-Dev-Apikey": "Tg1NWEwNGIgIC0K",
        "ContentsDiary-Type": "application/json"
    }

    # payload for authentication
    payload = {
        "ident": None,
        "pass": password,
        "uid": uid
    }

    try:
        response = requests.post(url, headers=headers, json=payload) # send POST request
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("An error occurred:", e)

    token = response.json()["token"] # extract token from response

    return token

token = get_token()
service = authenticate_google_account()

uid_no_s = uid[1:] # remove the first character 'S' from uid
start_date = date.today()
end_date = date.today()

# set the start date to the next school year if the current date is after June 30
if(start_date > date(date.today().year, 6, 30)):
    end_date = date(date.today().year + 1, 6, 30)
else:
    end_date = date(date.today().year, 6, 30)

# format the dates to the required format
formatted_start_date = start_date.strftime("%Y%m%d")
formatted_end_date = end_date.strftime("%Y%m%d")

url = f"https://web.spaggiari.eu/rest/v1/students/{uid_no_s}/agenda/all/{formatted_start_date}/{formatted_end_date}"

# headers for the request
headers = {
    "User-Agent": "CVVS/std/4.1.7 Android/10",
    "Z-Dev-Apikey": "Tg1NWEwNGIgIC0K",
    "Z-Auth-Token": token,
    "ContentsDiary-Type": "application/json"
}

try:
    response = requests.get(url, headers=headers) # send GET request
    response.raise_for_status()
except requests.exceptions.HTTPError as e:
    print("[HTTP error] Response Body:", response.json())
except requests.exceptions.RequestException as e:
    print("Error during agenda retrieval:", e)

words_blacklist = ["colloqui", "colloquio", "webex"] 
tests = ["verifica", "compito", "prova", "test", "orale", "scritto", "presentazione", "presentazioni", "interrogazione", "interrogazioni", "verifiche", "prove", "test", "orali", "scritti", "presentazioni", "interrogazioni"]

for event in response.json().get("agenda", []):
    parsed_begin_date = datetime.fromisoformat(event["evtDatetimeBegin"])
    parsed_end_date = datetime.fromisoformat(event["evtDatetimeEnd"])
    
    google_calendar_event = {}

    should_skip = False
    for word in words_blacklist: # skip events that contain blacklisted words
        if word in event["notes"].lower():
            should_skip = True
            break

    if should_skip:
        continue

    color = 1
    for word in tests: # set color to red if event contains test-related words
        if word in event["notes"].lower():
            color = 11
            break

    if(event["isFullDay"]): # build google calendar event if it is an all day event
        google_calendar_event = {
            'summary': event["notes"],
            'description': event["authorName"],
            'start': {
                'date': parsed_begin_date.strftime("%Y-%m-%d")
            },
            'end': {
                'date': (parsed_end_date + timedelta(1)).strftime("%Y-%m-%d")
            },
            'colorId': color,
            'reminders': {
                'useDefault': False,
            }
        }
    else: # build google calendar event if it is not an all day event
        google_calendar_event = {
            'summary': event["notes"],
            'description': event["authorName"],
            'start': {
                'dateTime': parsed_begin_date.strftime("%Y-%m-%dT%H:%M:%S"),
                'timeZone': 'Europe/Rome'
            },
            'end': {
                'dateTime': parsed_end_date.strftime("%Y-%m-%dT%H:%M:%S"),
                'timeZone': 'Europe/Rome'
            },
            'colorId': color,
            'reminders': {
                'useDefault': False,
            }
        }

    create_event(service, google_calendar_event) # create the event in google calendar