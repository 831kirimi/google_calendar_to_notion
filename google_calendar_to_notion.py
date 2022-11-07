#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime, re
import googleapiclient.discovery
import google.auth
import requests
import os
from dotenv import load_dotenv
import dataclasses

@dataclasses.dataclass
class Event:
    calendar_id: str
    title: str
    start: str
    end: str
    location: str
    description: str
    page_id:str = ''

def convert_datetime_google_to_notion(ggl_datetime:str):
  split = ggl_datetime.split('+')
  convert = split[0] + '.000+' + split[1]
  return convert
  
# googleカレンダーから情報を取得
def get_google_calendar(api_key_path:str,calendar_id:str,sync_token:str) -> list: 
  SCOPES = ['https://www.googleapis.com/auth/calendar']
  gapi_creds = google.auth.load_credentials_from_file(api_key_path, SCOPES)[0]
  service = googleapiclient.discovery.build('calendar', 'v3', credentials=gapi_creds)

  print('get google calendar events...')

  if sync_token != '' or sync_token != None: # sync tokenあり
    event_list = service.events().list(
        calendarId=calendar_id,
        singleEvents=True,
        syncToken=sync_token).execute()
  else: # sync tokenなし
    event_list = service.events().list(
        calendarId=calendar_id,
        singleEvents=True).execute()

  events = event_list.get('items', [])

  next_sync_token = event_list.get('nextSyncToken')
  next_page_token = event_list.get('nextPageToken')

  while next_page_token != None:
    event_list = service.events().list(
      pageToken=next_page_token,
      calendarId=calendar_id,
      singleEvents=True).execute()
    events.append(event_list.get('items', []))
    next_sync_token = event_list.get('nextSyncToken')
    next_page_token = event_list.get('nextPageToken')

  f = open('nextSyncToken', 'w')
  f.write(next_sync_token)
  f.close()

  formatted_events = []
  for event in events:
      if 'summary' not in event:
            continue
      if 'location' in event:
            location = event['location']
      else:
            location = ''
      if 'description' in event:
            description = event['description']
      else:
            description = ''
      start = event['start'].get('dateTime', event['start'].get('date'))
      end = event['end'].get('dateTime', event['end'].get('date'))
      if re.match(r'^\d{4}-\d{2}-\d{2}$', start): # all day event
        end = None
      else:
        start = convert_datetime_google_to_notion(start)
        end = convert_datetime_google_to_notion(end)

      formatted_events.append(Event(calendar_id=event['id'],
                                        title=event['summary'],
                                        start=start, # start time or day
                                        end=end, # end time or day
                                        location=location,
                                        description=description))

  return formatted_events
          
# Notionの指定したデータベースにページを作成する
def create_notion_page(notion_key:str,database_id:str,calender:Event) -> None:
  url = "https://api.notion.com/v1/pages"

  payload = {
    "parent": {
        "type": "database_id",
        "database_id": database_id
    },
    "properties": {
      "CalendarID": {
        "type": "rich_text",
        "rich_text": [
          {
            "type": "text",
            "text": {
              "content": calender.calendar_id
            }
          }
        ]
      },
      "Title": {
        "title": [
          {
            "type": "text",
            "text": {
              "content": calender.title
            }
          }
        ]
      },
      "Date": {
        "type": "date",
        "date": {
          "start": calender.start,
          "end": calender.end
        }
      },
      "Location": {
        "type": "rich_text",
        "rich_text": [
          {
            "type": "text",
            "text": {
              "content": calender.location
            }
          }
        ]
      },
      "Description": {
        "type": "rich_text",
        "rich_text": [
          {
            "type": "text",
            "text": {
              "content": calender.description
            }
          }
        ]
      },
    }
  }

  headers = {
    "accept": "application/json",
    "Notion-Version": "2022-06-28",
    "content-type": "application/json",
    "authorization": "Bearer {}".format(notion_key)
  }

  print('create notion page...')

  response = requests.post(url, json=payload, headers=headers)
  
  if response.status_code == requests.codes.ok:
    print('success!')
  else:
    print('### error ###')
    print('status_code: {0}, calendar_id: {1}, title: {2}'.format(response.status_code, calender.calendar_id, calender.title))

def query_notion_database(notion_key:str,database_id:str,calender_id:str):
  url = "https://api.notion.com/v1/databases/{}/query".format(database_id)

  payload = {
      "page_size": 100,
      "filter": {
        "property": "CalendarID",
        "rich_text": {
        "equals": calender_id
        }
      }
  }
  headers = {
      "accept": "application/json",
      "Notion-Version": "2022-06-28",
      "content-type": "application/json",
      "authorization": "Bearer {}".format(notion_key)
  }

  response = requests.post(url, json=payload, headers=headers)

  json_data = response.json()
  results = json_data["results"]
  if len(results) == 0:
    return 0
  elif len(results) == 1:
    result = results[0]
    event = Event(calendar_id=calender_id,
    title=result['properties']['Title']['title'][0]['text']['content'],
    start=result['properties']['Date']['date']['start'],
    end=result['properties']['Date']['date']['end'],
    location=result['properties']['Location']['rich_text'][0]['text']['content'],
    description=result['properties']['Description']['rich_text'][0]['text']['content'],
    page_id=result['id'])
    return event
  else:
    print('error!')
    return 1

def update_page(notion_key:str,page_id:str,event:Event):
  url = "https://api.notion.com/v1/pages/{}".format(page_id)

  payload = {"properties": {
      # "CalendarID": {
      #   "type": "rich_text",
      #   "rich_text": [
      #     {
      #       "type": "text",
      #       "text": {
      #         "content": event.calendar_id
      #       }
      #     }
      #   ]
      # },
      "Title": {
        "title": [
          {
            "type": "text",
            "text": {
              "content": event.title
            }
          }
        ]
      },
      "Date": {
        "type": "date",
        "date": {
          "start": event.start,
          "end": event.end
        }
      },
      "Location": {
        "type": "rich_text",
        "rich_text": [
          {
            "type": "text",
            "text": {
              "content": event.location
            }
          }
        ]
      },
      "Description": {
        "type": "rich_text",
        "rich_text": [
          {
            "type": "text",
            "text": {
              "content": event.description
            }
          }
        ]
      },
    }
  }

  headers = {
      "accept": "application/json",
      "Notion-Version": "2022-06-28",
      "content-type": "application/json",
      "authorization": "Bearer {}".format(notion_key)
  }

  response = requests.patch(url, json=payload, headers=headers)

  if response.status_code == requests.codes.ok:
    print('success!')
  else:
    print('### error ###')
    print('status_code: {0}, calendar_id: {1}, title: {2}'.format(response.status_code, event.calendar_id, event.title))

def main():
  load_dotenv()

  # sync token
  if os.path.exists('nextSyncToken'):
    sync_token = open('nextSyncToknen', 'r')
  else:
    sync_token = ''
  
  events = get_google_calendar(os.environ['GOOGLE_API_KEY_PATH'],os.environ['CALENDAR_ID'],sync_token)

  for event in events:
    notion_event = query_notion_database(os.environ['NOTION_ACCESS_KEY'],os.environ['DATABASE_ID'],event.calendar_id)
    if notion_event == 0: # create
      create_notion_page(os.environ['NOTION_ACCESS_KEY'],os.environ['DATABASE_ID'],event)
    elif notion_event == 1:
      continue
    else: # update
      event.page_id = notion_event.page_id
      if event != notion_event:
        update_page(os.environ['NOTION_ACCESS_KEY'],event.page_id,event)
      else:
        print('no update')

if(__name__ == '__main__'):
  main()