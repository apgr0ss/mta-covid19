from urllib import request
import re
import glob
from io import StringIO
import os
import numpy as np
import pandas as pd
import datetime

"""
Scrape turnstile entry/exit data from MTA website
and clean for analysis
"""

# Set global parameters
start_date = '200104'
end_date = '200411' # leave blank if you want data up to the most recent date

# Get file names from website
page = request.urlopen('http://web.mta.info/developers/turnstile.html')
raw_page = page.read().decode('utf-8')
file_names = np.array(re.findall(r'turnstile_[0-9]+.txt',raw_page))
file_names = file_names[::-1] # reverse the order


start_date_idx = np.where([start_date in file_name for file_name in file_names])
start_date_idx = start_date_idx[0][0]

if end_date == '':
    end_date_idx = len(file_names)-1
else:
    end_date_idx = np.where([end_date in file_name for file_name in file_names])
    end_date_idx = end_date_idx[0][0]

mta_data = pd.DataFrame()
# Grab names of files that have already been downloaded -- to save time
downloaded = glob.glob('.\\data\\*.csv')
downloaded = [file[5:-4] for file in downloaded]
if os.path.exists('.\\data\\mta_data.csv'):
    mta_data = pd.read_csv('.\\data\\mta_data.csv')
    mta_data.loc[:,'DATETIME'] = [pd.Timestamp(dtime) for dtime in mta_data.DATETIME]

for i in range(start_date_idx,end_date_idx+1):
    year = '20'+file_names[i][-10:-4][:2]
    month = file_names[i][-10:-4][2:4]
    day = file_names[i][-10:-4][4:]
    pretty_date = '-'.join([year,month,day])
    if file_names[i][:-4] not in downloaded:
        html_file = request.Request('http://web.mta.info/developers/data/nyct/turnstile/' + file_names[i], headers={'User-Agent': 'Mozilla/5.0'})
        htmltext = request.urlopen(html_file).read().decode('utf-8')
        new_data = pd.read_csv(StringIO(htmltext),sep=',',header=0)
        # Combines 'date' and 'time' columns into a 'datetime' field for easier indexing
        datetime_str = [date + ' ' + time for date,time in zip(new_data['DATE'],new_data['TIME'])]
        new_data['DATETIME'] = pd.DatetimeIndex(datetime_str)
        new_data.columns = [col.replace(' ','') for col in new_data.columns]

        # Filter by regular audits
        new_data = new_data.loc[new_data.DESC=='REGULAR']
        new_data.to_csv('.\\data\\{0}.csv'.format(file_names[i][:-4]))
        mta_data = pd.concat([mta_data, new_data],axis=0)
        print('Added data for ' + pretty_date)

# Save result to CSV
mta_data.to_csv('.\\data\\mta_data.csv',index=False)
