import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import censusdata

nyc_county_fips = {'ny_county':'061',
                   'kings_county':'047',
                   'queens_county':'081',
                   'bronx_county':'005',
                   'richmond_county':'085'}

geo_list = [censusdata.censusgeo([('state', '36'), ('county', county),('tract','*')]) for county in list(nyc_county_fips.values())]

manhattan = censusdata.geographies(geo_list[0],'sf1',2010)
manhattan_censusgeo = list(manhattan.values())[:]

pop_per_tract = pd.concat([censusdata.download('sf1',2010,geocode,['P008006','P001001']) for geocode in manhattan_censusgeo])

pop_per_tract = pop_per_tract.iloc[:,[0,2]]
pop_per_tract.columns = ['tot_asian','tot']
pop_per_tract = pop_per_tract.loc[pop_per_tract.tot > 100,:]
pop_per_tract.apply(lambda x: x[0]/x[1], axis=1).sort_values(ascending=False)
