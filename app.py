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
df = pd.read_csv("data/market_price_vigo_hist_daily.csv", dtype= {'species': str
                                                             , 'date': str
                                                             , 'max_price_kg': float
                                                             , 'min_price_kg': float
                                                             , 'kg_auctioned': float}, parse_dates=['date'])


# Converting pandas date formate to datetime.date()
df.date = df.date.apply(lambda x: x.to_pydatetime().date())

#renaming columns
df.columns =['especie','fecha', 'precio_max', 'precio_min', 'kg_vendidos']

# Data enrichment
df.insert(2, "precio_medio", (df.precio_max+df.precio_min)/2)
df.insert(6, "rotacion_eur", df.precio_medio*df.kg_vendidos)

#
price_range_chart_data= df.groupby('fecha').mean().sort_values(by='fecha', ascending=True)[['precio_medio', 'precio_min','precio_max']]

price_index = price_range_chart_data['precio_medio']/price_range_chart_data['precio_medio'][0]*100

st.title('Precios de Pescado en lonja')
st.write("Indice de precios (Abr-22 21 = 100)")
st.line_chart(price_index)


st.write("Evolucion del precio medio, maximo y minimo")
option = st.selectbox(
    'Escoge la especie a visualizar',
     np.insert(df['especie'].unique(),0,"TODOS (Media ponderada)"))
if not option == "TODOS (Media ponderada)":
    price_range_chart_data = df[df['especie']== option].set_index('fecha')[['precio_medio', 'precio_min','precio_max']]

st.line_chart(price_range_chart_data)
if not option == "TODOS (Media ponderada)":
    if st.checkbox('Datos detallados'):
        'Informacion detallada sobre la especie : ', option 
        st.write(df[df['especie']==option].drop(columns='especie').sort_values(by='fecha'))


st.write("5 especies más caros:")
st.write(df.nlargest(5, 'precio_medio'))

st.write("5 especies más baratos:")
st.write(df.nsmallest(5, 'precio_medio'))

st.write("5 especies más vendidos")
st.write(df.nlargest(5, 'kg_vendidos'))




