# -*- coding: utf-8 -*-
"""
Created on Thu Apr 29 17:48:22 2021

@author: valen
"""


import streamlit as st
import numpy as np
import pandas as pd
import os
import altair as alt

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

st.title('Precios de pescado en lonja')
st.header("Indice de precios")
st.text("Abr-22 21 = 100")

st.line_chart(price_index)


st.header("Evolucion del precio por especie")

option = st.selectbox(
    'Escoge la especie a visualizar',
     np.insert(df['especie'].sort_values().unique(),0,"TODAS (media ponderada)"))
if not option == "TODAS (media ponderada)":
    price_range_chart_data = df[df['especie']== option].set_index('fecha')[['precio_medio', 'precio_min','precio_max']]
st.text("Precio medio, maximo y minimo en Eur /Kg")

st.line_chart(price_range_chart_data)
if not option == "TODAS (media ponderada)":
    if st.checkbox('Mostrar datos detallados'):
        'Informacion detallada sobre la especie : ', option 
        st.write(df[df['especie']==option].drop(columns='especie').sort_values(by='fecha'))


st.header("Las 5 especies más caras segun precio medio:")
st.text("Precios en Eur /Kg")
df_avg_per_species = df.groupby('especie').mean()
source = df_avg_per_species.round(2).nlargest(5, 'precio_medio').reset_index()[['especie','precio_medio']]
st.write(alt.Chart(source).mark_bar().encode(
    x='precio_medio:Q',y=alt.Y('especie:N', sort='-x'), color=alt.Color('precio_medio', scale=alt.Scale(scheme='reds'))))

st.write(df_avg_per_species.round(2).nlargest(5, 'precio_medio')[['precio_medio', 'precio_min','precio_max']].style.format("{:2}"))
#st.bar_chart(df_avg_per_species.round(2).nlargest(5, 'precio_medio')[['precio_medio']])





st.header("Las 5 especies más baratas segun precio medio:")
st.text("Precios en Eur /Kg")
source = df_avg_per_species.round(2).nsmallest(5, 'precio_medio').reset_index()[['especie','precio_medio']]
st.write(alt.Chart(source).mark_bar().encode(
    x='precio_medio:Q',y=alt.Y('especie:N', sort='x'), color=alt.Color('precio_medio', scale=alt.Scale(scheme='greenblue'))))

st.write(df_avg_per_species.round(2).nsmallest(5, 'precio_medio')[['precio_medio', 'precio_min','precio_max']].style.format("{:2}"))

st.header("Las 5 especies más vendidas")
st.text("Segun Kg vendidos por media cada día")
st.write(df_avg_per_species.round(2).nlargest(5, 'kg_vendidos')[['kg_vendidos', 'precio_medio']].style.format("{:,.2f}"))




