import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

"""
Graph MTA data
"""


"""
TODO
-------
Examine LINENAME field
Some stations have multiple linenames
    - cumulative entries/exits differ
    - could be because that station has 2 levels, with a set of turnstiles
      on each level and each set of turnstiles recorded separately
    - Issue: the tests for each set of turnstiles conducted at different times
             so when it's groupby'd datetime the result doesn't capture what's
             needed
    - Maybe just aggregate to daily?
        - But then I could see the case where we'd want to differentiate
          ridership behavior between rush-hour (impact on work) and non-rush-hour
          (impact on leisure)
        - By aggregating to daily we'd lose this granularity
"""

mta_data = pd.read_csv('.\\data\\mta_data.csv')
mta_data.loc[:,'DATETIME'] = [pd.Timestamp(date, freq='d') for date in mta_data.DATETIME]

mta_data = mta_data.drop_duplicates(subset=['C/A','UNIT','SCP','STATION','LINENAME','DIVISION','DATETIME'],keep='last')

# Collect station names
station_names = np.unique(mta_data['STATION'])
station_names.sort()
# Clean station names
station_names_formatted = [name.lower().replace(' ','_').replace('/','_').replace('-','_').replace('.','_')for name in station_names]
station_name_map = {station_name: station_name_formatted for station_name,station_name_formatted in zip(station_names,station_names_formatted)}


# Omit stations that have (potentially) faulty turnstile reporting tools
# These were chosen based on whether their time series on cumulative entries
# reported wild swings or outliers
omit_stations = ['TIMES SQ-42 ST','ST LAWRENCE AV', 'PROSPECT AV',
                 'PAVONIA/NEWPORT', 'NEWARK HW BMEBE', 'NEWARK C',
                 'NEWARK HM HE','NEWARK BM BW','LEXINGTON AV/63',
                 'LACKAWANNA','JOURNAL SQUARE','HOWARD BCH JFK',
                 'HOYT ST','HARRISON','GRD CNTRL-42 ST',
                 'FULTON ST','FRANKLIN ST','EAST BROADWAY',
                 'CHRISTOPHER ST','CARROLL ST','CANAL ST',
                 'BOWLING GREEN','8 AV','79 ST',
                 '75 ST-ELDERTS','59 ST','50 ST',
                 '46 ST BLISS ST','42 ST-PORT AUTH','34 ST-PENN STA',
                 '34 ST-HERALD SQ','238 ST','23 ST']


# Omit stations with inconsistencies -- will look at these later
station_names_redux = np.array(station_names)[[station not in omit_stations for station in station_names]]
with open(".\\data\\station_names_redux.txt",'w') as f:
    f.write('\n'.join([station_name_map[name] for name in station_names_redux]))

# Smooth series with rolling window
# over 1-week period
smooth = True

# Plot growth rates as opposed to levels
# Growth rates will be relative to January's average ridership
# for a given hour block
growth = True
growth_addendum = ''
# Plot total 4-hourly entries per station over time for each station
for name in station_names_redux:
    mta_sample = mta_data.loc[mta_data['STATION'] == name]
    mta_sample = mta_sample.sort_values(['SCP','DATETIME'])
    mta_sample = mta_sample.reset_index(drop=True)

    # Observe level change relative to previous hour block
    level_change = mta_sample.drop('DATETIME',axis=1).groupby(['SCP','LINENAME']).transform(lambda x: x-x.shift(1))
    mta_sample.loc[:,['ENTRIES','EXITS']] = level_change

    mta_sample = mta_sample.groupby('DATETIME').sum()
    mta_sample = mta_sample.sort_values(by='DATETIME')

    # Filter out observations with values < 0 (because it doesn't make sense
    # otherwise--these are based on cumulative entries, meaning over time
    # the number of entries should be non-decreasing
    mta_sample = mta_sample.loc[mta_sample.ENTRIES > 0,:]
    mta_sample = mta_sample.reset_index(drop=False)

    # Add weekend dummy for future groupbys
    mta_sample.loc[:,'WEEKEND'] = [1 if date.weekday() >= 4 else 0 for date in mta_sample.DATETIME]

    # Separate datetime into separate string columns
    mta_sample.loc[:,'YEAR']  = [date.year for date in mta_sample.DATETIME]
    mta_sample.loc[:,'MONTH'] = [date.month for date in mta_sample.DATETIME]
    mta_sample.loc[:,'DAY']   = [date.day for date in mta_sample.DATETIME]

    if growth:
        mta_sample = mta_sample.drop('DATETIME',axis=1)
        # Add time column for future groupbys
        mta_sample_jan = mta_sample.loc[mta_sample.apply(lambda x: (x.MONTH == 1) and (x.YEAR==2020),axis=1),:]

        mta_sample_jan = mta_sample_jan.groupby(['YEAR','MONTH','DAY']).mean().reset_index()

        mta_sample_jan = mta_sample_jan.groupby(['WEEKEND']).mean().reset_index()

        mta_sample_jan.loc[mta_sample_jan.WEEKEND == 1,'ENTRIES'] = mta_sample_jan.loc[mta_sample_jan.WEEKEND == 1,'ENTRIES'].mean()

        mta_sample_jan = mta_sample_jan.reset_index(drop=True)
        mta_sample_jan = mta_sample_jan.drop('EXITS',axis=1)
        mta_sample_jan = mta_sample_jan.drop(['YEAR','MONTH','DAY'],axis=1)

        mta_sample_daily = mta_sample.groupby(['YEAR','MONTH','DAY']).mean().reset_index()

        # Merge the January averages to the original dataframe
        mta_sample_merged = mta_sample_daily.merge(mta_sample_jan,how='inner',left_on=['WEEKEND'],right_on=['WEEKEND'],suffixes=('','_JAN'))
        mta_sample_merged.loc[:,'DATETIME'] = mta_sample_merged.apply(lambda x: pd.Timestamp(str(int(x.YEAR)) + '-' + str(int(x.MONTH)) + '-' + str(int(x.DAY)),freq='d'), axis=1)

        mta_sample_merged = mta_sample_merged[['DATETIME','ENTRIES','ENTRIES_JAN']]
        mta_sample_merged = mta_sample_merged.set_index('DATETIME')

        pct_chng = ((mta_sample_merged.ENTRIES-mta_sample_merged.ENTRIES_JAN)/mta_sample_merged.ENTRIES_JAN)*100
        mta_sample = pd.DataFrame(pct_chng)
        mta_sample.columns = ['ENTRIES']
        mta_sample = mta_sample.sort_index()
        # Label to add to plot
        y_label = '% change in ridership\n(relative to Jan. averages)'
    else:
        y_label = 'Average ridership by station entries'

    if smooth:
        if growth:
            # Split weekends and weekdays
            mta_sample_wkd_smooth = mta_sample.loc[np.logical_and(mta_sample.index.weekday >= 0,
                                                                  mta_sample.index.weekday < 4),:]

            mta_sample_wkn_smooth = mta_sample.loc[np.logical_and(mta_sample.index.weekday >= 4,
                                                                  mta_sample.index.weekday <= 6),:]
        else:
            # Split weekends and weekdays
            mta_sample_wkd_smooth = mta_sample.loc[np.logical_and([date.weekday() >= 0 for date in mta_sample.DATETIME],
                                                                  [date.weekday() < 4 for date in mta_sample.DATETIME]),:]
            mta_sample_wkn_smooth = mta_sample.loc[np.logical_and([date.weekday() >= 4 for date in mta_sample.DATETIME],
                                                                  [date.weekday() <=6 for date in mta_sample.DATETIME]),:]


        mta_sample_wkd_smooth = mta_sample_wkd_smooth.rolling(window=7).mean().interpolate('linear')
        mta_sample_wkn_smooth = mta_sample_wkn_smooth.rolling(window=7).mean().interpolate('linear')


    fig, ax = plt.subplots(figsize=(14,8))
    dir_name = '.\\output\\plot_entries_per_station_grow={0}_smooth={1}'.format(int(growth),int(smooth))
    if smooth:
        ax.plot(mta_sample.loc['2020-02':,'ENTRIES'],alpha=0.3)
        ax.plot(mta_sample_wkd_smooth.loc['2020-02':,'ENTRIES'])
        ax.plot(mta_sample_wkn_smooth.loc['2020-02':,'ENTRIES'])
        ax.legend(['Total, unsmoothed','Weekdays, smoothed','Weekends, smoothed'])
        ax.set_title(name)
        ax.set_xlabel('Date')
        ax.set_ylabel(y_label)
        plt.tight_layout()
        try:
            fig.savefig(dir_name + '\\raw_entries_per_station={0}'.format(station_name_map[name]))
        except FileNotFoundError:
            os.makedirs(dir_name)
            fig.savefig(dir_name + '\\raw_entries_per_station={0}'.format(station_name_map[name]))
    else:
        ax.plot(mta_sample.loc['2020-02':,'ENTRIES'])
        ax.set_title(name)
        ax.set_xlabel('Date')
        ax.set_ylabel(y_label)
        plt.tight_layout()
        try:
            fig.savefig(dir_name + '\\raw_entries_per_station={0}'.format(station_name_map[name]))
        except FileNotFoundError:
            os.makedirs(dir_name)
            fig.savefig(dir_name + '\\raw_entries_per_station={0}'.format(station_name_map[name]))
