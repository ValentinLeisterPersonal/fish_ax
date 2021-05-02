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
                                                                  ,'kg_auctioned': float}
                                                                 , parse_dates=['date'])

# Converting pandas date formate to datetime.date()
df.date = df.date.apply(lambda x: x.to_pydatetime().date())

# Renaming columns
df.columns =['especie','fecha', 'precio_max', 'precio_min', 'kg_vendidos']

# Aggregating duplicate entries under the same name
df = df.groupby(['fecha','especie']).agg({'precio_max':max
                                          , 'precio_min':min
                                          , 'kg_vendidos': sum}).reset_index()

# Data enrichment
df.insert(2, "precio_medio", (df.precio_max+df.precio_min)/2)
df.insert(6, "rotacion_eur", df.precio_medio*df.kg_vendidos)

##############
## Data preprocessing

df_agg_per_date=df.groupby(['fecha']).agg({'precio_medio':np.mean
                                     ,'precio_max':np.mean
                                     ,'precio_min':np.mean})

price_index = df_agg_per_date['precio_medio']/df_agg_per_date['precio_medio'][0]*100


df_avg_per_species = df.groupby('especie').agg({'precio_medio':np.mean
                                     ,'precio_max':np.max
                                     ,'precio_min':np.min
                                     ,'kg_vendidos':sum})


##########
##########

st.title('Precios de pescado en lonja')
st.header("Evolucion del precio por especie")

option = st.selectbox(
    'Escoge la especie a visualizar',
     np.insert(df['especie'].sort_values().unique(),0,"TODAS (media ponderada)"))
if not option == "TODAS (media ponderada)":
    df_agg_per_date = df[df['especie']== option].set_index('fecha')[['precio_medio', 'precio_min','precio_max']]
st.text("Precio medio, maximo y minimo en Eur /Kg")



source=df_agg_per_date.reset_index().melt('fecha')
st.write(
    alt.Chart(source).mark_line(interpolate='step-after').encode(
    x='fecha',
    y='value',
    color=alt.Color('variable', scale=alt.Scale(domain=['precio_medio', 'precio_min','precio_max']
                                                , range = ['black','palegreen','coral']))
    ).configure_line(size=3)
    )


if not option == "TODAS (media ponderada)":
    if st.checkbox('Mostrar datos detallados'):
        'Informacion detallada sobre la especie : ', option 
        st.write(df[df['especie']==option].drop(columns='especie').sort_values(by='fecha'))


st.header("Las 5 especies más caras segun precio medio:")
st.text("Precios en Eur /Kg")

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


st.header("Indice general de precios")
st.text("Abr-22 21 = 100")
st.line_chart(price_index)


st.header("Las 5 especies más vendidas")
st.text("Segun Kg vendidos por media cada día")
st.write(df_avg_per_species.round(2).nlargest(5, 'kg_vendidos')[['kg_vendidos', 'precio_medio']].style.format("{:,.2f}"))




