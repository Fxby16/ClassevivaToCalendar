import requests
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from dateutil.parser import isoparse
import os
import json
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

url = "https://web.spaggiari.eu/rest/v1/auth/login"
SCOPES = ['https://www.googleapis.com/auth/calendar']

with open("classeviva_credentials.json", "r") as file:
    classeviva_credentials = json.load(file)

ident = classeviva_credentials["ident"]
password = classeviva_credentials["pass"]
uid = classeviva_credentials["uid"]

def authenticate_google_account():
    creds = None
    # Se il token di accesso esiste già, caricalo
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # Se non ci sono credenziali o sono scadute, procedi con il flusso OAuth 2.0
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Utilizza il file 'credentials.json' per il flusso OAuth 2.0
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Salva le credenziali per il prossimo accesso
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # Costruisci il servizio
    service = build('calendar', 'v3', credentials=creds)
    return service

def event_exists(service, summary, start_time):
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone(timedelta(hours=1)))

    # Define the time range to search for events
    time_min = start_time.isoformat()
    time_max = (start_time + timedelta(hours=1))
    if time_max.tzinfo is None:
        time_max = time_max.replace(tzinfo=timezone(timedelta(hours=1)))
    time_max = time_max.isoformat() 

    try:
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        print(f"Checking for existing events between {time_min} and {time_max}...")

        for event in events:
            print(f"Found event: {event['summary']} at {event['start']}")
            # Compare summary and start time
            event_start = event['start'].get('dateTime', event['start'].get('date'))
            if event['summary'] == summary and event_start == start_time.isoformat():
                print(f"Event '{summary}' already exists.")
                return True
    except Exception as e:
        print(f"Errore durante la verifica dell'evento: {e}")

    return False

def create_event(service, event):
    event_exists_flag = event_exists(service, google_calendar_event['summary'], datetime.fromisoformat(google_calendar_event['start']['dateTime']))
    
    if event_exists_flag:
        print(f"Evento '{google_calendar_event['summary']}' già esistente!")
        return
    
    try:
        event_result = service.events().insert(
            calendarId='primary', body=event).execute()
        print(f"Evento creato: {event_result.get('htmlLink')}")
    except Exception as error:
        print(f"Si è verificato un errore: {error}")

def get_token():
    headers = {
        "User-Agent": "CVVS/std/4.1.7 Android/10",
        "Z-Dev-Apikey": "Tg1NWEwNGIgIC0K",
        "ContentsDiary-Type": "application/json"
    }

    payload = {
        "ident": ident,
        "pass": password,
        "uid": uid
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        #print("Response Status Code:", response.status_code)
        #print("Response Body:", response.json()) 
    except requests.exceptions.RequestException as e:
        print("An error occurred:", e)

    token = response.json()["token"]

    return token

token = get_token()
service = authenticate_google_account()

uid_no_s = uid[1:]
url = f"https://web.spaggiari.eu/rest/v1/students/{uid_no_s}/agenda/all/20250324/20250330"

headers = {
    "User-Agent": "CVVS/std/4.1.7 Android/10",
    "Z-Dev-Apikey": "Tg1NWEwNGIgIC0K",
    "Z-Auth-Token": token,
    "ContentsDiary-Type": "application/json"
}

try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    #print("Response Status Code:", response.status_code)
    #print("Response Body:", response.json())
except requests.exceptions.HTTPError as e:
    print("[HTTP error] Response Body:", response.json())
except requests.exceptions.RequestException as e:
    print("An error occurred:", e)

words_blacklist = ["colloqui", "colloquio", "webex"]
verifiche = ["verifica", "compito", "prova", "test", "orale", "scritto", "presentazione", "presentazioni", "interrogazione", "interrogazioni", "verifiche", "prove", "test", "orali", "scritti", "presentazioni", "interrogazioni"]

for event in response.json().get("agenda", []):
    parsed_begin_date = datetime.fromisoformat(event["evtDatetimeBegin"])
    parsed_end_date = datetime.fromisoformat(event["evtDatetimeEnd"])
    # print(event["authorName"], ":", event["notes"], "\n", event["isFullDay"], parsed_begin_date, parsed_end_date, "\n")

    google_calendar_event = {}

    should_skip = False
    for word in words_blacklist:
        if word in event["notes"].lower():
            should_skip = True
            break

    if should_skip:
        continue

    color = 1
    for word in verifiche:
        if word in event["notes"].lower():
            color = 11
            break

    if(event["isFullDay"]):
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
    else:
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

    create_event(service, google_calendar_event)