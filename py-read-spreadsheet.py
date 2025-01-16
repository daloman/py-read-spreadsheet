#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys
import pandas as pd
import requests as rs
import filecmp
from difflib import *
import datetime
import re
import shutil
import logging

pd.options.mode.copy_on_write = True

etalon = os.environ.get('ETALON_PATH', "etalon.csv")
original="original.xlsx"
temporary="temporary.csv"

log_level=os.environ.get('LOG_LEVEL','INFO')
webpage=os.environ.get('SCHEDULE_HTML',"/usr/share/nginx/html/index.html")
spreadsheet_columns = os.environ.get('SPREADSHEET_COLUMNS', "A:C,HF,HH,HL:HN")

tg_notifications_enable = os.environ.get('TG_NOTIFICATIONS_ENABLE', "False")
api_url = os.environ.get('NOTIFICATIONS_API_URL')
bot_token = os.environ.get('NOTIFICATIONS_BOT_TOKEN')
chat_id = os.environ.get('NOTIFICATIONS_CHAT_ID')

spreadsheet_id = os.environ.get('SPREADSHEET_ID')
spreadsheet_url="https://docs.google.com/spreadsheets/d/" + spreadsheet_id + "/export?format=xlsx"

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(encoding='utf-8', level=log_level)

logger.debug("Etalon file: %s", etalon)
logger.debug("Web page file: %s", webpage)
logger.debug("Web page file: %s", webpage)

res=rs.get(url=spreadsheet_url)

with open(original, 'wb') as f:
    f.write(res.content)

data=pd.ExcelFile(original)

# Produce spreadsheet list name (current week): "dd.MM-dd.MM.*"
today = datetime.datetime.today()
monday = today - datetime.timedelta(datetime.datetime.weekday(today))
saturday = today + datetime.timedelta(5 - datetime.datetime.weekday(today))
list_name_search_template = f"{monday.strftime('%d.%m')}.*{saturday.strftime('%d.%m')}"
logger.info(list_name_search_template)

list_name=''
# Get sheet names list
sheets=data.sheet_names
list_index=0
if len(data.sheet_names)>1:
    # Find list index
    count=0
    for list in data.sheet_names:
        # print("Count is: %d, list name is: %s" % (count, list))
        if re.search(list_name_search_template, list):
            list_index=count
            break
        count += 1

    logger.info("List found: %s, list index is: %d" % (list, list_index))
    schedule = data.parse(list_index, usecols=spreadsheet_columns)
    mygroup = schedule.tail(-2)
    mygroup.to_csv(temporary, index=False, header=False)
   

    mygroup.replace("\n", "<br>", inplace=True, regex=True)
    html=mygroup.to_html(header=False, na_rep='', justify='center', escape=False)
    
    # Create html to paste dataframe in it
    with open(webpage, "w", encoding="utf-8") as file:
      file.writelines('<meta charset="UTF-8">\n')
      file.writelines(f'<h1 align="center">{list}</h1>\n')
      
      file.write(html)

    # Save data from spreadsheet as etalon if it is absent.
    if not os.path.isfile(etalon):
        shutil.copyfile(temporary, etalon)
    comparision_result = filecmp.cmp(etalon, temporary, shallow=False)
    if not comparision_result:
        # If current data drom spreadsheet diffs from etalon,
        # backup etalon and replace with current data.
        timestamp=datetime.datetime.now()
        oldetalon=f"{etalon}-{timestamp.strftime('%d-%m-%Y-%H%M%S')}"
        logger.debug("Move old etalon file to: %s", oldetalon)
        shutil.copyfile(etalon, oldetalon)
        shutil.copyfile(temporary, etalon)
        msg = f"Current schedule: {list}\nSchedule has been changed"
        '''
        Example:
        
        curl -X POST \
             -H 'Content-Type: application/json' \
             -d '{"chat_id": "123456789", "text": "This is a test from curl", "disable_notification": true}' \
             https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage
        
        '''
        if tg_notifications_enable.lower() not in ('false', '0', 'f'):
            r = rs.post(api_url + '/bot' + bot_token + '/sendMessage', data={"chat_id": chat_id, "text": msg})
            logger.info("Message sent result: %s" % r)
    else:
        msg = f"Get sheets: {sheets}\nSchedule is untouched"
    

    logger.info(msg)
