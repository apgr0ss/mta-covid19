import censusdata
from fuzzywuzzy import fuzz
import glob
import numpy as np
import pandas as pd
import geopandas as gpd
import descartes
import matplotlib.pyplot as plt

"""
Map stations to respective Census tract geographically and
pull in relevant demographic data

NOTE: Filtered out stations that did not achieve a 68 or higher Levenshtein ratio
"""

NYC_COUNTY_FIPS = {'Manhattan':'061',
                   'Brooklyn':'047',
                   'Queens':'081',
                   'Bronx':'005',
                   'Staten Island':'085'}

class Station:
    """
    Represent each station as a class
    Attributes:
        • short_name - abbreviated station name
        • long_name  - full station name
        • point - geographic point associated with station
        • tract - associated Census tract
        • ridership_df - ridership time series (from mta_data_graph.py)
        • demo_df - demographic data of the surrounding tract

    Methods:
        • find_point - find the geometric point associated w/ station
        • map_point  - find Census tract where the point resides
    """
    def __init__(self,short_name):
        self.short_name = short_name
        self.long_name  = station_to_shp_name_dict[short_name]
        self.tract = ''
        self.borough_name = ''
        # Call methods
        self.find_point()

    def find_point(self):
        self.point = station_geo.loc[station_geo.name == self.long_name,'geometry'].values[0]

    def set_tract(self,tract):
        self.tract = tract

    def set_borough(self, borough):
        self.borough_name = borough
        self.borough_fips = NYC_COUNTY_FIPS[borough]

    def plot_station(self):
        point_df = gpd.GeoDataFrame({'name':'point','geometry':[self.point]},index=[0])
        fig, ax = plt.subplots()
        ct_df.plot(ax=ax)
        point_df.plot(ax=ax,color='red',markersize=40)

# Import station geography
station_geo = gpd.read_file('.\\data\\shape_files\\mta_stations\\geo_export_421f3107-0ff0-4c6c-9b11-15319fb58431.shp')

######################################
# Import Census tract geography      #
# Import each borough separately...  #
######################################
ct_shp_filenames = glob.glob('.\\data\\shape_files\\census_tracts_nyc\\*.shp')
ct_dfs = []
for filename in ct_shp_filenames:
    ct_dfs += [gpd.read_file(filename)]
# ...and vertically concatenate
ct_df = pd.concat(ct_dfs)

# Import abbreviated station names
with open('.\\data\\station_names_redux.txt','r') as f:
    station_names_redux = f.read().split('\n')

################################################################################
# Create dictionary mapping station names I created to shapefile station names #
################################################################################
station_to_shp_name_dict = {}
for station in station_names_redux:
    ratio_list = [fuzz.ratio(station,station_2) for station_2 in np.unique(station_geo.name)]
    max_val = np.max(ratio_list)
    idx = np.where(ratio_list == max_val)[0]
    if max_val > 67:
        station_to_shp_name_dict[station] = np.unique(station_geo.name)[idx][0]
# Take broadway_jct out of dict because it's not a proper matching
station_to_shp_name_dict.pop('broadway_jct', None)

######################################
# Initialize list of station objects #
######################################
station_objs = []
for station_name in list(station_to_shp_name_dict.keys()):
    # Instantiate station object
    station = Station(station_name)
    # Find census tract which corresponds to station
    bool_cond =  [station.point.within(ct) for ct in ct_df.geometry.values]
    tract = ct_df.loc[bool_cond,'CT2010'].values[0]
    borough = ct_df.loc[bool_cond,'BoroName'].values[0]
    station.set_tract(tract)
    station.set_borough(borough)
    # Add station object to list
    station_objs += [station]


#####################################
# Plot which tracts are represented #
#####################################
station_points = [station.point for station in station_objs]
fig, ax = plt.subplots()
for station in station_objs:
    point_df = gpd.GeoDataFrame({'name':'point','geometry':[station.point]},index=[0])
    point_df.plot(ax=ax,color='red',markersize=40)

ct_df['include'] = ct_df.geometry.apply(lambda x: np.any([x.contains(point) for point in station_points]))
fig, ax = plt.subplots(figsize=(12,12))
ct_df.plot(ax=ax,column='include')
plt.axis('off')
plt.savefig('output\\nyc_tract_coverage.png')

#########################################
# Pull demographic info for each tract #
#########################################
geo_list = [censusdata.censusgeo([('state', '36'), ('county', station.borough_fips),('tract',station.tract)]) for station in station_objs]



pop_per_tract = pd.concat([censusdata.download('sf1',2010,geocode,['P008006','P001001']) for geocode in geo_list])

pop_per_tract = pop_per_tract.iloc[:,[0,1]]
pop_per_tract.columns = ['tot_asian','tot']
pop_per_tract = pop_per_tract.loc[pop_per_tract.tot > 100,:]
pop_per_tract.apply(lambda x: x[0]/x[1], axis=1).sort_values(ascending=False)
