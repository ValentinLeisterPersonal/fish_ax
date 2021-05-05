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
import psycopg2
import psycopg2.extras as extras

def execute_values(conn, df, table):
    """
    Using psycopg2.extras.execute_values() to insert the dataframe
    """
    # Create a list of tupples from the dataframe values
    tuples = [tuple(x) for x in df.to_numpy()]
    # Comma-separated dataframe columns
    cols = ','.join(list(df.columns))
    # SQL quert to execute
    query  = "INSERT INTO %s(%s) VALUES %%s" % (table, cols)
    cursor = conn.cursor()
    try:
        extras.execute_values(cursor, query, tuples)
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print("Error: %s" % error)
        conn.rollback()
        cursor.close()
        return 1
    print("execute_values() done")
    cursor.close()


DATABASE_URL = os.environ['DATABASE_URL']
#DATABASE_URL = 'postgres://qpesqziuxmjadk:068a89d1a51c5c4c25b2e76e54d82005f68edc09d1ff5941ffa8de208fcf59bf@ec2-23-22-191-232.compute-1.amazonaws.com:5432/da51dv9akjq43s'
conn = psycopg2.connect(DATABASE_URL, sslmode='require')


os.chdir(os.path.dirname(os.path.abspath(__file__)))
#os.chdir(r'C:\Users\valen\desktop\fish_ax')


# scraping Website HTML
print("Starting scraping fish prices from Vigo...")
page = requests.get('http://www.puertodevigo.com/informacion-diaria-lonja/')
soup = BeautifulSoup(page.text, "html.parser")
print("Done scraping")

# Find table call "listado" which contains fish auction prices
table = soup.findChildren(name="table", attrs={"class":"listado"})[0]

# Extract each row of the table but nothing else
rows = table.findChildren(['td', 'tr'])


#creating table to write content into
columns = ["species","max_price", "min_price", "kg_auctioned"]
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
df_today_clean = df_today.apply(lambda x: x.str.replace('[A-Za-z]', '').str.replace('.', '').str.replace(',', '.').astype(float) if x.name in ['max_price','min_price', 'kg_auctioned'] else x)

# Add a date column with today´s date. 
df_today_clean.insert(1, 'date', datetime.date.today())
print('Data for today looks like this:')
print(df_today_clean.head())

# Load all existing data to see whether we already have some entries for today

sql = 'select * from market_price_vigo_hist_daily'
df_hist = pd.read_sql_query(sql,conn)


if len(df_today_clean)>len(df_hist[datetime.date.today() == df_hist.date]):
    print('We found new data from today. Removing any previous records previous to appending...')

    # Dropping rows where date is not today
    #df_hist = df_hist[datetime.date.today() != df_hist.date]
    cur = conn.cursor()
    cur.execute("""delete from market_price_vigo_hist_daily where date = %s""",(datetime.date.today(),))
    print('Step 1: Successfully dropped previously pulled record for today')

    print('Records stored before appending:'+str(len(pd.read_sql_query(sql,conn))))
    # Appending new rows to pg table
    execute_values(conn, df_today_clean, 'market_price_vigo_hist_daily')
    print(str(len(pd.read_sql_query(sql,conn))))

    print(str(len(df_today_clean))+' new rows successfully apended')
    print('Records stored after appending:'+str(len(pd.read_sql_query(sql,conn))))
else:
    print('No new records for today. Not making any updates to the database')

# Updating the main database
#df_updated.to_csv('data/market_price_vigo_hist_daily.csv',index=False, header =True)
#print('Data successfully written to .csv')

# Writing a backup with a timestamp, just in case
#df_updated.to_csv('data/backup/market_price_vigo_hist_daily_backup'+datetime.datetime.now().strftime("%d-%b-%Y-%H-%M-%S")+'.csv',index=False, header =True)
#print('Data Backup successfully written')