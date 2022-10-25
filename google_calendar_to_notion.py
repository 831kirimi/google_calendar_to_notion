#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import googleapiclient.discovery
import google.auth
import requests
import os
from dotenv import load_dotenv

# googleカレンダーから情報を取得
def get_google_calendar(api_key_path,calendar_id,start,max_result):
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
      formatted_events.append([event['id'],
            event['summary'],
            event['start'].get('dateTime', event['start'].get('date')), # start time or day
            event['end'].get('dateTime', event['end'].get('date')), # end time or day
            location,
            description])

  return formatted_events
          
# Notionの指定したデータベースにページを作成する
def create_notion_page(notion_key,database_id,calendar_id,title,start,end,location,description):
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
              "content": calendar_id
            }
          }
        ]
      },
      "Title": {
        "title": [
          {
            "type": "text",
            "text": {
              "content": title
            }
          }
        ]
      },
      "Date": {
        "type": "date",
        "date": {
          "start": start,
          "end": end
        }
      },
      "Location": {
        "type": "rich_text",
        "rich_text": [
          {
            "type": "text",
            "text": {
              "content": location
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
              "content": description
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
    print('status_code: {0}, calendar_id: {1}, title: {2}'.format(response.status_code, calendar_id, title))
  

def main():
  load_dotenv()

  # start = datetime.datetime.utcnow().isoformat() + 'Z' # now
  start = datetime.datetime(2010, 1, 1, 0, 0, 0, 0).isoformat() + 'Z'

  events = get_google_calendar(os.environ['GOOGLE_API_KEY_PATH'],os.environ['CALENDAR_ID'],start,100000)

  for event in events:
    create_notion_page(os.environ['NOTION_ACCESS_KEY'],os.environ['DATABASE_ID'],event[0],event[1],event[2],event[3],event[4],event[5])
  
if(__name__ == '__main__'):
  main()