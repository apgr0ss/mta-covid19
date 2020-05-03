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

        # Call methods
        self.find_point()

    def find_point(self):
        self.point = station_geo.loc[station_geo.name == self.long_name,'geometry'].values[0]

# Import station geography
station_geo = gpd.read_file('.\\data\\shape_files\\mta_stations\\geo_export_421f3107-0ff0-4c6c-9b11-15319fb58431.shp')

# Import Census tract geography
# Import each borough separately...
ct_shp_filenames = glob.glob('.\\data\\shape_files\\census_tracts\\*.shp')
ct_dfs = []
for filename in ct_shp_filenames:
    ct_dfs += [gpd.read_file(filename)]
# ...and vertically concatenate
ct_df = pd.concat(ct_dfs)


# Import abbreviated station names
with open('.\\data\\station_names_redux.txt','r') as f:
    station_names_redux = f.read().split('\n')


station_to_shp_name_dict = {}
for station in station_names_redux:
    ratio_list = [fuzz.ratio(station,station_2) for station_2 in np.unique(station_geo.name)]
    max_val = np.max(ratio_list)
    idx = np.where(ratio_list == max_val)[0]
    if max_val > 67:
        station_to_shp_name_dict[station] = np.unique(station_geo.name)[idx][0]
# Take broadway_jct out of dict because it's not a proper matching
station_to_shp_name_dict.pop('broadway_jct', None)
station_1 = Station(list(station_to_shp_name_dict.keys())[0])

bool_cond =  [station_1.point.within(ct) for ct in ct_df.geometry.values]
np.where(bool_cond)

point_df = gpd.GeoDataFrame({'name':'point','geometry':[station_1.point]},index=[0])
fig, ax = plt.subplots()
ct_df.plot(ax=ax)
point_df.plot(ax=ax,color='red',markersize=40)




nyc_county_fips = {'ny_county':'061',
                   'kings_county':'047',
                   'queens_county':'081',
                   'bronx_county':'005',
                   'richmond_county':'085'}

geo_list = [censusdata.censusgeo([('state', '36'), ('county', county),('tract','*')]) for county in list(nyc_county_fips.values())]

manhattan = censusdata.geographies(geo_list[0],'sf1',2010)
manhattan_censusgeo = list(manhattan.values())[:]

pop_per_tract = pd.concat([censusdata.download('sf1',2010,geocode,['P008006','P001001']) for geocode in manhattan_censusgeo])

pop_per_tract = pop_per_tract.iloc[:,[0,1]]
pop_per_tract.columns = ['tot_asian','tot']
pop_per_tract = pop_per_tract.loc[pop_per_tract.tot > 100,:]
pop_per_tract.apply(lambda x: x[0]/x[1], axis=1).sort_values(ascending=False)
