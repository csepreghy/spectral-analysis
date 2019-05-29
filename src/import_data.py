from astroquery.gama import GAMA
from astroquery.sdss import SDSS
import astropy.units as u
from astropy import coordinates as coords

from astropy import coordinates as coords

import pandas as pd
import numpy as np

pos = coords.SkyCoord('0h8m05.63s +14d50m23.3s', frame='icrs')
xid = SDSS.query_region(pos, spectro=True)

template = SDSS.get_spectral_template('qso')
print('template', template)

def get_gama_dataset_from_query():
  gama_all_data = GAMA.query_sql('SELECT * FROM AATSpecAll AS s WHERE s.z BETWEEN 0.000000001 AND 10')
  gama_all_data_df = pd.DataFrame(np.array(gama_all_data)) # convert table to CSV
  gama_all_data_df.to_csv('data/GAMA.csv') # write csv into data folder

  return gama_all_data_df


def get_gama_dataset_from_csv():
  gama_df = pd.read_csv('data/GAMA.csv')
  
  return gama_df

def get_SDSS_dataset_from_query():
  pos = coords.SkyCoord('120.01976d +45.916684d', frame='icrs')
  xid = SDSS.query_region(pos, spectro=True, radius=2000*u.arcsec)
  sp = SDSS.get_spectra(matches=xid)
  #im = SDSS.get_images(matches=xid, band='g')

  return sp