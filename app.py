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
import psycopg2


DATABASE_URL = os.environ['DATABASE_URL']
#DATABASE_URL = 'postgres://qpesqziuxmjadk:068a89d1a51c5c4c25b2e76e54d82005f68edc09d1ff5941ffa8de208fcf59bf@ec2-23-22-191-232.compute-1.amazonaws.com:5432/da51dv9akjq43s'
conn = psycopg2.connect(DATABASE_URL, sslmode='require')

os.chdir(os.path.dirname(os.path.abspath(__file__)))
#os.chdir(r'C:\Users\valen\desktop\fish_ax')

sql = 'select * from market_price_vigo_hist_daily'
df = pd.read_sql_query(sql,conn)

# Converting pandas date formate to datetime.date()
#df.date = df.date.apply(lambda x: x.to_pydatetime().date())

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
                                     ,'precio_min':np.mean
                                     ,'kg_vendidos':sum})

price_index = df_agg_per_date['precio_medio']/df_agg_per_date['precio_medio'][0]*100


df_avg_per_species = df.groupby('especie').agg({'precio_medio':np.mean
                                     ,'precio_max':np.max
                                     ,'precio_min':np.min
                                     ,'kg_vendidos':sum})


##########
##########

st.title('Precios de pescado en lonja')

st.header("El Chollometro de la lonja hoy")


df_deviation = pd.read_sql_query('''SELECT species as especie,
avg_price_today as precio_hoy,
deviation_from_avg_price as desviacion_del_precio_medio,
avg_price_all_time as precio_medio
from (select 
				date, 
				species, 
				round(((max(max_price)+min(min_price))/2)::numeric, 2) as avg_price_today,
				round((avg((max(max_price)+min(min_price))/2) over (partition by species))::numeric, 2) as avg_price_all_time,
				round((((max(max_price)+min(min_price))/2)/ (avg((max(max_price)+min(min_price))/2) over (partition by species))-1)::numeric, 2) as deviation_from_avg_price
				from market_price_vigo_hist_daily
	 			group by 1,2) deviations
where date = CURRENT_DATE
ORDER BY deviation_from_avg_price''', conn)


df_deviation['data_label']= pd.Series(["{0:+.0f}%".format(val * 100) for val in df_deviation.desviacion_del_precio_medio])+' ('+df_deviation.precio_hoy.astype(str)+'€)' 



option = st.selectbox(
    'Escoge la especie a visualizar',
     np.insert(df['especie'].sort_values().unique(),0,"TODAS (media ponderada)"))

if not option == "TODAS (media ponderada)":
        df_agg_per_date = df[df['especie']== option].set_index('fecha')[['precio_medio', 'precio_min','precio_max', 'kg_vendidos']]  

if len(df_deviation)>0:
    
    if not option == "TODAS (media ponderada)":    
        source = df_deviation[df_deviation["especie"] == option]
    else:
        (min_price, max_price) = st.slider('O indica el precio en EUR/Kg que estas dispuesto a pagar'
                              , min(df_deviation.precio_hoy)
                              , max(df_deviation.precio_hoy)
                              , (min(df_deviation.precio_hoy), max(df_deviation.precio_hoy))
                              , step=1.0)
        source = df_deviation[(df_deviation['precio_hoy']<=max_price)&(df_deviation['precio_hoy']>=min_price)]

    base = alt.Chart(source).encode(
        x='desviacion_del_precio_medio:Q',
        y=alt.Y('especie:N', sort='x')
    )
    
    bars = base.mark_bar().encode(color=alt.Color('desviacion_del_precio_medio', scale=alt.Scale(domain = [-1,+1],scheme='lightmulti'), legend = None))
    
    
    text = base.mark_text(
        align='left',
        baseline='middle',
        dx=7  # Nudges text to right so it doesn't appear on top of the bar
    , color ='slategrey').encode(
        text='data_label')
    
    
    
    st.text("Precio hoy en EUR /Kg vs. precio medio")
    st.write(bars + text)
else:
    st.text("Parece que hoy la lonja está cerrada o aun no se han publicado precios.")

    

st.header("Evolucion del precio por especie")


st.text("Precio medio, maximo y minimo en Eur /Kg")

# line chart with price evolution
source=df_agg_per_date[['precio_medio', 'precio_min','precio_max']].reset_index().melt('fecha')
st.write(
    alt.Chart(source).mark_line(point=True
                                #, interpolate='step-after'
                                ).encode(
    x='fecha',
    y='value',
    color=alt.Color('variable', scale=alt.Scale(domain=['precio_medio', 'precio_min','precio_max']
                                                , range = ['#797979','#B2FDBF','#FDBFB2']),legend=None)
    ).configure_line(size=3)
    )

                                    
                                    
                                    
                                   
                                    
# column chart with volume

df_kg_sold_per_day = df_agg_per_date.reset_index()[['fecha', 'kg_vendidos']]

st.write(
    alt.Chart(df_kg_sold_per_day).mark_bar(size=15).encode(
    x='fecha',
    y='kg_vendidos'
    ).configure_bar(color='#797979')
    )
                                    
                                    
if not option == "TODAS (media ponderada)":
    if st.checkbox('Mostrar datos detallados'):
        'Informacion detallada sobre la especie : ', option 
        st.write(df[df['especie']==option].drop(columns='especie').sort_values(by='fecha'))


df_per_weekday = pd.read_sql_query('''select species, weekday_numeric, avg_price, round(avg_price/ avg(avg_price) over (partition by species)-1, 3) dev_pct_from_avg_price from 

((select 'TODAS (media ponderada)' as species
, extract(isodow from date) as weekday_numeric
, round(percentile_cont(0.5) within group (order by((max_price+min_price)/2))::numeric, 2) avg_price

 from market_price_vigo_hist_daily 
group by 1,2
order by 1,2)

union all

(select species
, extract(isodow from date) as weekday_numeric
, round(percentile_cont(0.5) within group (order by((max_price+min_price)/2))::numeric, 2) avg_price 

 from market_price_vigo_hist_daily 
group by 1,2
order by 1, 2)) as base''', conn)

weekday_dict_es = {1:'1.LUN', 2:'2.MAR', 3:'3.MIE', 4: '4.JUE', 5: '5.VIE', 6: '6.SAB', 7: '7.DOM'}

df_per_weekday['weekday_char']=[weekday_dict_es[wd] for wd in df_per_weekday.weekday_numeric]

#line weekday chart

source = df_per_weekday


df_per_weekday['option_chosen']='other species'

df_per_weekday.loc[df_per_weekday['species']==option, 'option_chosen'] = option

line=alt.Chart(source).mark_line(point=True).encode(
            x='weekday_char',
            y=alt.Y('dev_pct_from_avg_price', axis=alt.Axis(format='+%')),
            detail=alt.Detail('species'),
            tooltip='species',
            color=alt.Color('option_chosen', scale=alt.Scale(domain=['other species', option]
                                                        , range = ['#cfebfd','#00008b']))
            ).properties(width=550,height=800).interactive()

# layer that accomplishes the highlighting
source_highlight = df_per_weekday[df_per_weekday["species"] == option]
line_highlight = alt.Chart(source_highlight).mark_line(point=True).encode(
                    x='weekday_char',
                    y=alt.Y('dev_pct_from_avg_price'),
                    detail=alt.Detail('species'),
                    tooltip='species',
                    color=alt.Color('option_chosen', scale=alt.Scale(domain=['other species', option]
                                                                , range = ['#cfebfd','#00008b']))
                    ).properties(width=800, height=800).interactive()

st.write(line + line_highlight)


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




