# -*- coding: utf-8 -*-
"""
Created on Thu Apr 29 17:48:22 2021

@author: valen
"""


import streamlit as st
import numpy as np
import pandas as pd
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
#os.chdir(r'C:\Users\valen\fish_ax')


# Importing data
df = pd.read_csv("data\\market_price_vigo_hist_daily.csv", dtype= {'species': str
                                                             , 'date': str
                                                             , 'max_price_kg': float
                                                             , 'min_price_kg': float
                                                             , 'kg_auctioned': float}, parse_dates=['date'])
# Converting pandas date formate to datetime.date()
df.date = df.date.apply(lambda x: x.to_pydatetime().date())

# Data enrichment
df["mid_price_eur"] = (df.max_price_kg+df.min_price_kg)/2
df["turnover_at_mid_price_eur"] = df.mid_price_eur*df.kg_auctioned

#
df.groupby('species')


# top 5 most expensive fish

st.title('Fish Price Analytics (Puerto de Vigo)')
st.write("Top 5 Most expensive all time:")
st.write(df.nlargest(5, 'mid_price_eur'))

st.write("Top 5 least expensive all time:")
st.write(df.nsmallest(5, 'mid_price_eur'))

st.write("Top 5 most kg auctioned:")
st.write(df.nlargest(5, 'kg_auctioned'))

st.write("top 5 highest turnover")
st.write(df.nlargest(5, 'turnover_at_mid_price_eur'))

chart_data = pd.DataFrame(
     np.random.randn(20, 3),
     columns=['a', 'b', 'c'])

chart_data = df.groupby('date').mean().sort_values(by='date', ascending=True)[['max_price_kg', 'mid_price_eur','min_price_kg']]

st.write("Price range development over time")

st.line_chart(chart_data)

if st.checkbox('Get detailed data'):
    option = st.selectbox(
        'Which fish would you like to look at',
         df['species'])
    
    'You selected: ', option, 'price' 
    st.write(df[df['species']==option].drop(columns='species').sort_values(by='date'))

