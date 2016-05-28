# BernieEventBot
Script to pull information from the Bernie Map. Updates Slack and a google spreadsheet.

Implementation is a bit "quick and dirty" as it's not a permanent application.

Requires:
- Slack webhook API URL
- Google API key
- Sunlightfoundation.com API Key

Outline:
- Pulls national data set of events
- First round of filtering is based on state zipcode
- Second round is based on lat/long
- Uses Sunlightfoundation API to filter and categorize based on congressional district
- Determines city based on zip code
- Updates Slack channel
- Will provide list of events for that day if --daily is passed into the script
- Updates Google spreadsheet
- Caches data in JSON format for next run

Built for Python 2.7

License is GNU General Public License Version 3
