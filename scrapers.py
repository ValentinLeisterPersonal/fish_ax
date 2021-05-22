# -*- coding: utf-8 -*-
"""
Created on Thu Apr 29 17:24:58 2021

@author: valen
"""
import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import re
import os
from tqdm import tqdm
import psycopg2
import psycopg2.extras as extras

class FishPrices():
    def __init__(self, url, conn):
        self.conn = conn
        # scraping Website HTML
        print("Starting scraping fish prices from Vigo...")
        page = requests.get(url)
        self.soup = BeautifulSoup(page.text, "html.parser")
        print("Done scraping")
        
    @staticmethod
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
    
    def extract_rows(self):
        # Find table call "listado" which contains fish auction prices
        table = self.soup.findChildren(name="table", attrs={"class":"listado"})[0]
        
        # Extract each row of the table but nothing else
        self.rows = table.findChildren(['td', 'tr'])
        
    def create_df(self):
        #creating table to write content into
        columns = ["species","max_price", "min_price", "kg_auctioned"]
        self.df = pd.DataFrame(columns = columns)
        
    
    def rows_to_df(self):
        
        #write each row to table
        for row in tqdm(self.rows):
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
                df_length = len(self.df)
                self.df.loc[df_length] = row_entries
        
    def convert_strings_to_float(self):
        # convert all strings that have been scraped and represent numeric values into floats
        self.df_clean = self.df.apply(lambda x: x.str.replace('[A-Za-z]', '').str.replace('.', '').str.replace(',', '.').astype(float) if x.name in ['max_price','min_price', 'kg_auctioned'] else x)


    def add_todays_date(self):
        # Add a date column with today´s date. 
        self.df_clean.insert(1, 'date', datetime.date.today())
        print('Data for today looks like this:')
        print(self.df_clean.head())
    
    
    def load_historic_data(self, sql):
        # Load all existing data to see whether we already have some entries for today
        self.sql = sql
        self.df_hist = pd.read_sql_query(sql, self.conn)
        
        
    def check_if_new_data_available(self):
        if len(self.df_clean)>len(self.df_hist[datetime.date.today() == self.df_hist.date]):
            self.isfreshdata = True
        else:
            self.isfreshdata = False

    
    def update_db(self):
        if self.isfreshdata == True:
            print('We found new data from today.')
            self.drop_stale_data()
            self.append_fresh_data()
        else:
            print('No new records for today. Not making any updates to the database')
            
          
    def drop_stale_data(self):
        # Dropping rows where date is not today
        print('Removing any previous records previous to appending...')
        cur = self.conn.cursor()
        cur.execute("""delete from market_price_vigo_hist_daily where date = %s""",(datetime.date.today(),))
        print('Step 1: Successfully dropped previously pulled record for today')
        
    
    def append_fresh_data(self):
        print('Records stored before appending:'+str(len(pd.read_sql_query(self.sql,self.conn))))
        
        # Appending new rows to pg table
        self.execute_values(self.conn, self.df_clean, 'market_price_vigo_hist_daily')
        print(str(len(pd.read_sql_query(self.sql,self.conn))))
    
        print(str(len(self.df_clean))+' new rows successfully apended')
        print('Records stored after appending:'+str(len(pd.read_sql_query(self.sql,self.conn))))

