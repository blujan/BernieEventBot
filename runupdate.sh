#!/bin/bash

curl -O https://d2bq2yf31lju3q.cloudfront.net/js/event-data.gz
gunzip event-data.gz
mv event-data event-data.data
if [ $# -eq 0 ]; then
  python event_process_5.py > latestlog.log 2>&1
else
  echo $1
  python event_process_5.py $1 > latestlog.log 2>&1
fi
