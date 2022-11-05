#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import googleapiclient.discovery
import google.auth
import requests
import os
from dotenv import load_dotenv
import dataclasses
# import json

@dataclasses.dataclass
class Event:
    calendar_id: str
    title: str
    start: str
    end: str
    location: str
    description: str
    page_id:str = ''

# googleカレンダーから情報を取得
def get_google_calendar(api_key_path:str,calendar_id:str,start:str,max_result:int) -> list: 
  SCOPES = ['https://www.googleapis.com/auth/calendar']
  gapi_creds = google.auth.load_credentials_from_file(api_key_path, SCOPES)[0]
  service = googleapiclient.discovery.build('calendar', 'v3', credentials=gapi_creds)

  print('get google calendar events...')

  event_list = service.events().list(
      calendarId=calendar_id, timeMin=start,
      maxResults=max_result, singleEvents=True,
      orderBy='startTime').execute()

  events = event_list.get('items', [])
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
      formatted_events.append(Event(calendar_id=event['id'],
                                        title=event['summary'],
                                        start=event['start'].get('dateTime', event['start'].get('date')), # start time or day
                                        end=event['end'].get('dateTime', event['end'].get('date')), # end time or day
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
    # p2j_data = json.dumps(r, indent=4)
    # print(p2j_data)
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

  print(response.text) 

def main():
  load_dotenv()

  # start = datetime.datetime.utcnow().isoformat() + 'Z' # now
  start = datetime.datetime(2010, 1, 1, 0, 0, 0, 0).isoformat() + 'Z'

  max_result = 100000

  events = get_google_calendar(os.environ['GOOGLE_API_KEY_PATH'],os.environ['CALENDAR_ID'],start,max_result)

  for event in events:
    update_event = query_notion_database(os.environ['NOTION_ACCESS_KEY'],os.environ['DATABASE_ID'],event.calendar_id)
    if update_event == 0: # create
      create_notion_page(os.environ['NOTION_ACCESS_KEY'],os.environ['DATABASE_ID'],event)
    elif update_event == 1:
      continue
    else: # update
      event.page_id = update_event.page_id
      if event != update_event:
        update_page(os.environ['NOTION_ACCESS_KEY'],update_event.page_id,update_event)      

if(__name__ == '__main__'):
  main()