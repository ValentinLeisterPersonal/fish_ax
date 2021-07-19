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
# set page title
st.set_page_config(page_title='Guia del Pescado | Precios, Sugerencias, Sostenibilidad, Temporada y Valor Nutritivo', page_icon='🎣')


# Remove the little menu at the top
st.markdown(""" <style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style> """, unsafe_allow_html=True)

# Remove excess padding on the page
padding = 0
st.markdown(f""" <style>
    .reportview-container .main .block-container{{
        padding-top: {padding}rem;
        padding-right: {padding}rem;
        padding-left: {padding}rem;
        padding-bottom: {padding}rem;
    }} </style> """, unsafe_allow_html=True)


# Make sure the title and icon are displayed next to each other
titcol1, titcol2 = st.beta_columns((1,4))

titcol1.image('img/logo.jpg')
titcol2.markdown('# Tu guia para una compra economica, sostenible, saludable y variada.')
st.markdown("---")


st.markdown("## Encuentra chollos en la lonja hoy")


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



if len(df_deviation)>0:
    (min_price, max_price) = st.slider('Buscas algo lujoso o barato? Limita el precio en EUR/Kg que estas dispuesto a pagar'
                              , min(df_deviation.precio_hoy)
                              , max(df_deviation.precio_hoy)
                              , (min(df_deviation.precio_hoy), max(df_deviation.precio_hoy))
                              , step=1.0)
    source = df_deviation[(df_deviation['precio_hoy']<=max_price)&(df_deviation['precio_hoy']>=min_price)]

    base_top = alt.Chart(source).encode(
        x=alt.X('desviacion_del_precio_medio', title= 'Desviacion de precio medio', axis=alt.Axis(format='+%')),
        y=alt.Y('especie:N', sort='x', title= None)
    ).transform_window(
    rank='rank(desviacion_del_precio_medio)',
    sort=[alt.SortField('desviacion_del_precio_medio', order='descending')]
    ).transform_filter(
    (alt.datum.desviacion_del_precio_medio >= 0))
        
    base_bottom = alt.Chart(source).encode(
        x=alt.X('desviacion_del_precio_medio', title= 'Desviacion de precio medio', axis=alt.Axis(format='+%')),
        y=alt.Y('especie:N', sort='x', title= None)
    ).transform_window(
    rank='rank(desviacion_del_precio_medio)',
    sort=[alt.SortField('desviacion_del_precio_medio', order='ascending')]
    ).transform_filter(
    (alt.datum.desviacion_del_precio_medio <= 0))

else:
    st.text("Parece que hoy la lonja está cerrada o aun no se han publicado precios.")

col1, col2 = st.beta_columns(2)

base = base_bottom
bars = base.mark_bar().encode(
    color=alt.Color('desviacion_del_precio_medio'
                    , scale=alt.Scale(domain = [-1,+1],scheme='lightmulti')
                    , legend = None)
    )

text = base.mark_text(
    align='left',
    baseline='middle',
    dx=7  # Nudges text to right so it doesn't appear on top of the bar
, color ='slategrey').encode(
    text='data_label')



#st.text("Precio hoy en EUR /Kg vs. precio medio")
col1.markdown("### Hoy más barato que habitualmente")
col1.altair_chart(bars + text, use_container_width=True)

############


base = base_top
bars = base.mark_bar().encode(
    color=alt.Color('desviacion_del_precio_medio'
                    , scale=alt.Scale(domain = [-1,+1],scheme='lightmulti')
                    , legend = None)
    )

text = base.mark_text(
    align='left',
    baseline='middle',
    dx=7  # Nudges text to right so it doesn't appear on top of the bar
, color ='slategrey').encode(
    text='data_label')

col2.markdown("### Hoy mas caro que habitualmente")
col2.altair_chart(bars + text, use_container_width=True)


#############################
#############################

st.markdown("## Las 10 especies más caras y baratas segun precio medio:")
st.text("Precios en Eur /Kg")


col1, col2 = st.beta_columns(2)

source = df_avg_per_species.round(2).nlargest(10, 'precio_medio').reset_index()[['especie','precio_medio']]
bars=alt.Chart(source).mark_bar().encode(
    x=alt.X('precio_medio:Q', title = 'Precio medio (EUR/Kg)'),y=alt.Y('especie:N', sort='-x', title= None), color=alt.Color('precio_medio', scale=alt.Scale(scheme='reds'), legend = None))


labels = alt.Chart(source).mark_text( align='left',
        baseline='middle',
        dx=7  # Nudges text to right so it doesn't appear on top of the bar
    , color ='slategrey'
).encode(x=alt.X('precio_medio:Q', title = 'Precio medio (EUR/Kg)'),y=alt.Y('especie:N', sort='-x', title= None),
    text='precio_medio:Q'
)
         
col1.altair_chart(bars+labels, use_container_width=True)





#col1.write(df_avg_per_species.round(2).nlargest(5, 'precio_medio')[['precio_medio', 'precio_min','precio_max']].style.format("{:2}"))
#st.bar_chart(df_avg_per_species.round(2).nlargest(5, 'precio_medio')[['precio_medio']])

source = df_avg_per_species.round(2).nsmallest(10, 'precio_medio').reset_index()[['especie','precio_medio']]
bars=alt.Chart(source).mark_bar().encode(
    x=alt.X('precio_medio:Q', title = 'Precio medio (EUR/Kg)'), y=alt.Y('especie:N', sort='x', title= None), color=alt.Color('precio_medio', scale=alt.Scale(scheme='greenblue'), legend = None))

labels = alt.Chart(source).mark_text( align='left',
        baseline='middle',
        dx=7  # Nudges text to right so it doesn't appear on top of the bar
    , color ='slategrey'
).encode(x=alt.X('precio_medio:Q', title = 'Precio medio (EUR/Kg)'),y=alt.Y('especie:N', sort='x', title= None),
    text='precio_medio:Q'
)

col2.altair_chart(bars + labels, use_container_width =  True)



st.markdown("---")
st.header("Ver detalles para una especie especifica")
option = st.selectbox(
    'Escoge la especie a visualizar',
     np.insert(df['especie'].sort_values().unique(),0,"TODAS (media ponderada)"))

if not option == "TODAS (media ponderada)":
        df_agg_per_date = df[df['especie']== option].set_index('fecha')[['precio_medio', 'precio_min','precio_max', 'kg_vendidos']]  


st.markdown("### Observa si está subiendo o bajando el precio de tu pescado/marisco")
st.text("Precio medio, maximo y minimo en EUR/Kg")


# line chart with price evolution
source=df_agg_per_date[['precio_min','precio_max']].reset_index()

source2=df_agg_per_date[['precio_medio']].reset_index().melt('fecha')

line= alt.Chart(source2).mark_line(size=5, color = '#0C266A').encode(
    x=alt.X('fecha', title='Fecha'),
    y=alt.Y('value', title='Precio (EUR/Kg)')
    )


band = alt.Chart(source).mark_area(opacity=0.7, color='#cfebfd'
).encode(
    x='fecha',
    y='precio_min',
    y2='precio_max'
)

st.altair_chart(band+line, use_container_width=True)


######################
# Chart which plots data per weekday
######################
st.markdown("### Encuentra el mejor día de la semana para comprar tu pescado/marisco")

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

weekday_dict_es = {1:'1. LUN', 2:'2. MAR', 3:'3. MIE', 4: '4. JUE', 5: '5. VIE', 6: '6. SAB', 7: '7. DOM'}

df_per_weekday['weekday_char']=[weekday_dict_es[wd] for wd in df_per_weekday.weekday_numeric]

############################
#line weekday chart
############################

source = df_per_weekday


df_per_weekday['option_chosen']='other species'

df_per_weekday.loc[df_per_weekday['species']==option, 'option_chosen'] = option

line=alt.Chart(source).mark_line(point=True).encode(
            x='weekday_char',
            y=alt.Y('dev_pct_from_avg_price', axis=alt.Axis(format='+%')),
            detail=alt.Detail('species'),
            tooltip='species',
            color=alt.Color('option_chosen', scale=alt.Scale(domain=['other species', option]
                                                        , range = ['#cfebfd','#0C266A']), legend =None)
            ).interactive().properties(
    height=450
)

# layer that accomplishes the highlighting
source_highlight = df_per_weekday[df_per_weekday["species"] == option]
line_highlight = alt.Chart(source_highlight).mark_line(point=True, size =3).encode(
                    x=alt.X('weekday_char', title = 'Dia de la Semana'),
                    y=alt.Y('dev_pct_from_avg_price', title = 'Desviacion del precio medio'),
                    detail=alt.Detail('species'),
                    tooltip='species',
                    color=alt.Color('option_chosen', scale=alt.Scale(domain=['other species', option]
                                                                , range = ['#cfebfd','#0C266A']))
                    ).interactive()


annotation = alt.Chart(source).mark_text(
    align='left',
    baseline='middle',
    fontSize = 15,
    dx = 20
).encode(
        x='weekday_char',
        y=alt.Y('dev_pct_from_avg_price', axis=alt.Axis(format='+%')),
    text='species'
).transform_filter((alt.datum.species == option)&(alt.datum.weekday_char == '3.MIE')
)


st.altair_chart(line + annotation + line_highlight, use_container_width=True)


######################
# Chart with the volume of sales
######################


# column chart with volume
st.markdown("### Oberva si hay oferta suficiente para tu compra")

df_kg_sold_per_day = df_agg_per_date.reset_index()[['fecha', 'kg_vendidos']]

columns = alt.Chart(df_kg_sold_per_day).mark_bar(size=7).encode(
    x=alt.X('fecha', title = 'Fecha'),
    y=alt.Y('kg_vendidos', title = 'Kg en venta'),
    ).configure_bar(color='#cfebfd')

st.altair_chart(columns, use_container_width=True)
                                    
                                    
if not option == "TODAS (media ponderada)":
    if st.checkbox('Mostrar datos detallados'):
        'Informacion detallada sobre la especie : ', option 
        st.write(df[df['especie']==option].drop(columns='especie').sort_values(by='fecha'))

#######################
# Price Index        
#######################

st.header("Indice general de precios")
st.text("Abr-22 21 = 100")



source = pd.DataFrame({'date':price_index.index, 'index':price_index.values}) 
line = alt.Chart(source).mark_line().encode(x=alt.X('date', title= 'Fecha'), y=alt.Y('index', title= 'Nivel del Index (comparado con Abril-22 2021)'))
st.altair_chart(line, use_container_width=True)




st.header("Indice por subcategoria")

df_index = pd.read_sql_query("""with price_base as (select date
, category
, subcategory
, round(percentile_cont(0.5) within group (order by((max_price+min_price)/2))::numeric, 2) median_price

from market_price_vigo_hist_daily mp 

join species s on s.species = mp.species 
group by 1,2,3 order by 4 desc)

select date
, subcategory index_name
, round(median_price*100/first_value(median_price) OVER (partition by subcategory order by date), 2) index_value
from price_base
--union all 

--select date
--, category index_name
--, round(median_price*100/first_value(median_price) OVER (partition by category order by date), 2) index_value
--from price_base
--union all
--select date, 'TODAS (media ponderada)' index_name, round(median_price*100/first_value(median_price) OVER (order by date), 2) index_value
--from price_base""", conn)



subsector = st.selectbox(
    'Escoge la especie a visualizar',
     df_index['index_name'].sort_values().unique())

df_index= df_index[df_index.index_name == subsector]

line = alt.Chart(df_index).mark_line().encode(
    x=alt.X('date', title= 'Fecha'), y=alt.Y('index_value', title= 'Nivel del Index (comparado con Abril-22 2021)'), color= 'index_name')
st.altair_chart(line, use_container_width=True)



st.header("Las 5 especies más vendidas")
st.text("Según Cantidad vendida por media cada día")
st.dataframe(df_avg_per_species.round(2).nlargest(5, 'kg_vendidos')[['kg_vendidos', 'precio_medio']].style.format("{:,.2f}"))




