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

from scrapers import FishPrices 


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


###### Running the scraping of the website

fp = FishPrices(url= 'http://www.puertodevigo.com/informacion-diaria-lonja/', conn= conn)

fp.extract_rows()

fp.create_df()

fp.rows_to_df()

fp.convert_strings_to_float()

fp.add_todays_date()

fp.load_historic_data(sql = 'select * from market_price_vigo_hist_daily')

fp.check_if_new_data_available()

fp.update_db()