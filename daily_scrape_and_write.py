# -*- coding: utf-8 -*-
"""
Created on Thu Apr 29 17:24:58 2021

@author: valen
"""

# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import re
import os
from tqdm import tqdm

os.chdir(os.path.dirname(os.path.abspath(__file__)))
#os.chdir(r'C:\Users\valen\fish_ax')


# scraping Website HTML
print("Starting scraping fish prices from Vigo...")
page = requests.get('http://www.puertodevigo.com/informacion-diaria-lonja/')
soup = BeautifulSoup(page.text, "lxml")
print("Done scraping")

# Find table call "listado" which contains fish auction prices
table = soup.findChildren(name="table", attrs={"class":"listado"})[0]

# Extract each row of the table but nothing else
rows = table.findChildren(['td', 'tr'])


#creating table to write content into
columns = ["species","max_price_kg", "min_price_kg", "kg_auctioned"]
df_today = pd.DataFrame(columns = columns)

#write each row to table
for row in tqdm(rows):
    i=0
    cells = row.findChildren('td')
    if len(cells) >0:
        #print(cells)
        i=0
        row_entries = list()
        for cell in cells:
            i+=1
            value = cell.string
            # if it´s the first cell in the row, then we´re looking at the string and do not need to do any number extraction
            if i ==1:
                row_entries.append(value)
                
            # all other cells need to be cleaned of currency format and other text
            else:
                row_entries.append(re.findall(r'(^(?!0+\,00)(?=.{1,9}(\,|$))(?!0(?!\,))\d{1,3}(.\d{3})*(\,\d+)?|$)', value)[0][0])
                
        # We add the extracted data at the bottom of the data frame
        df_length = len(df_today)
        df_today.loc[df_length] = row_entries
        
# convert all strings that have been scraped and represent numeric values into floats
df_today_clean = df_today.apply(lambda x: x.str.replace('[A-Za-z]', '').str.replace('.', '').str.replace(',', '.').astype(float) if x.name in ['max_price_kg','min_price_kg', 'kg_auctioned'] else x)

# Add a date column with today´s date. 
df_today_clean.insert(1, 'date', datetime.date.today())
print('Data for today looks like this:')
print(df_today_clean.head())

# Load all existing data to see whether we already have some entries for today
df_hist = pd.read_csv("data\market_price_vigo_hist_daily.csv", dtype= {'species': str
                                                             , 'date': str
                                                             , 'max_price_kg': float
                                                             , 'min_price_kg': float
                                                             , 'kg_auctioned': float}, parse_dates=['date'])
# Converting pandas date formate to datetime.date()
df_hist.date = df_hist.date.apply(lambda x: x.to_pydatetime().date())

if len(df_hist[datetime.date.today() == df_hist.date]) > 0:
    print('Caution: '+str(len(df_hist[datetime.date.today() == df_hist.date]))+' Records already present for today. Removing records to overwrite...')

    # Dropping rows where date is not today
    df_hist = df_hist[datetime.date.today() != df_hist.date]
    print('Successfully dropped previously pulled record for today')

# Appending rows from today´s data pull
df_updated = pd.concat([df_hist, df_today_clean])
print(str(len(df_today_clean))+' new rows successfully apended')


# Updating the main database
df_updated.to_csv('data\market_price_vigo_hist_daily.csv',index=False, header =True)
print('Data successfully written to .csv')

# Writing a backup with a timestamp, just in case
df_updated.to_csv('data\backup\market_price_vigo_hist_daily_backup'+datetime.datetime.now().strftime("%d-%b-%Y-%H-%M-%S")+'.csv',index=False, header =True)
print('Data Backup successfully written')