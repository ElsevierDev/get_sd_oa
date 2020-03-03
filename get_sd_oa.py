# -*- coding: utf-8 -*-
"""
Script to identify all OpenAccess articles in ScienceDirect, and store their
    URIs in a text file.
Created on Wed Feb 26 18:16:11 2020
@author: VriesA
"""

####
# Prerequisites:
# - Get an API key from dev.elsevier.com, and store as a single string, without 
#   line break, in apikey.txt in same folder as this script
# - Go to https://www.sciencedirect.com/science/ehr, download holdings
#   report in Excel format, and save as 'sd_holdings.xlsx' in same folder
#   as this script

import requests, pandas as pd, json
from datetime import date

# Get APIkey
with open('apikey.txt') as f:
    apikey = f.read()

# Set request headers
headers = {
        'X-ELS-APIkey' :  apikey,
        'Accept' : 'application/json'
        }

# Define elements of request URL
base_url = 'https://api.elsevier.com/content/metadata/article?query='
query_template = '''\
openaccess(1)+AND+issn({})+AND+pub-date+IS+{}&count=100&field=prism:url'''

# Import holdings report and limit to journals only
holdings = pd.read_excel('sd_holdings.xlsx')
holdings = holdings[holdings.publication_type == 'Journal']

# Keep only ISSN, date of first and last issue online, and set open end date to

holdings = holdings[[
        'title_id',
        'date_first_issue_online',
        'date_last_issue_online']]
holdings.date_last_issue_online.fillna(
        str(date.today().year + 1),
        inplace = True)


# Reduce date fields to just year (not year-month)
def left_4(string):
    return string[:4]

holdings.date_first_issue_online = holdings.date_first_issue_online.apply(
        lambda x: left_4(x))
holdings.date_last_issue_online = holdings.date_last_issue_online.apply(
        lambda x: left_4(x))

# Create file to track which ISSNs and years have been completed
try:
    with open('history.json') as f:
        history = json.load(f)
    print('History file found and loaded')
    print(history)
except FileNotFoundError:
    history = {}

# Loop through ISSNs
for i in range (0, len (holdings)):
    issn = holdings.iloc[i].title_id
    start_year = holdings.iloc[i].date_first_issue_online
    end_year = holdings.iloc[i].date_last_issue_online
    if issn not in history.keys():
        history[issn] = []
    # Loop through years for this ISSN, in reverse order
    for year in range(int(end_year), int(start_year), -1):
        if year in history[issn]:
            print("Year {} already completed for ISSN {}".format(
                year, issn))
            break
        print("Starting search for ISSN {} and year {}".format(
                issn, year))
        next_url = base_url + query_template.format(issn, str(year))
        # Start requests
        while next_url:
            print("- Next url: {}".format(next_url))
            r = requests.get(next_url, headers = headers)
            resp = json.loads(r.content)
            if int(resp['search-results']['opensearch:itemsPerPage']) > 0:
                # There are results in this response
                print("- Appending {} OA article URIs".format(
                    int(len(resp['search-results']['entry']))))
                with open('oa_article_urls.txt', mode = 'a') as f:
                    f.writelines([result['prism:url']+'\n' for result in 
                             resp['search-results']['entry']])
                for link in resp['search-results']['link']:
                    if link['@ref'] == 'next':
                        # Paginated response
                        next_url = link['@href']
                        break
                    else:
                        # No pagination
                        next_url = None
                if not next_url:
                    print("- No 'next' url, moving on")
            else:
                next_url = None
                print("- No results in this response, moving on")
        history[issn].append(year)
        with open('history.json', 'w') as f:
            json.dump(history, f)
        