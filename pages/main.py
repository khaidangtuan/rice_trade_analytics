import pandas as pd
import streamlit as st
import plotly.express as px
import sqlite3
from datetime import datetime
import streamlit_authenticator as stauth

# initiate connection
conn = sqlite3.connect('data.db')
st.set_page_config(
    page_title='Rice Global Trade Handbook',
    layout="wide"
    )

if 'password_correct' in st.session_state:
    st.write(f"Welcome *{st.session_state['name']}*")
else:
    st.error('Please log in first')
    st.stop()   

hide_streamlit_style = """
                <style>
                div[data-testid="stToolbar"] {
                visibility: hidden;
                height: 0%;
                position: fixed;
                }
                div[data-testid="stDecoration"] {
                visibility: hidden;
                height: 0%;
                position: fixed;
                }
                div[data-testid="stStatusWidget"] {
                visibility: hidden;
                height: 0%;
                position: fixed;
                }
                #MainMenu {
                visibility: hidden;
                height: 0%;
                }
                header {
                visibility: hidden;
                height: 0%;
                }
                footer {
                visibility: hidden;
                height: 0%;
                }
                </style>
                """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

@st.cache_data
def fetch_transaction(connection=conn):
    query = '''
        SELECT * 
        FROM "transaction";
    '''
    data = pd.read_sql(query, conn)
    
    data['ACTUAL ARRIVAL DATE'] = pd.to_datetime(data['ACTUAL ARRIVAL DATE'])
    mintime = data['ACTUAL ARRIVAL DATE'].min().to_pydatetime()
    maxtime = data['ACTUAL ARRIVAL DATE'].max().to_pydatetime()
    
    return data, mintime, maxtime

@st.cache_data
def fetch_buyer(connection=conn):
    query = '''
        SELECT * 
        FROM "buyer_info";
    '''
    data = pd.read_sql(query, conn)
    
    return data

def aggregate_filter(df, transaction, volume, country=None):
    trans = df.groupby(['BUYER'])['WEIGHT (MT)'].count().reset_index().rename(columns={'WEIGHT (MT)':'transaction_no'})
    vols = df.groupby(['BUYER'])['WEIGHT (MT)'].sum().reset_index().rename(columns={'WEIGHT (MT)':'volume'})
    buyer = fetch_buyer()
    buyer = buyer.merge(trans, how='left', left_on='name', right_on='BUYER')
    buyer = buyer.merge(vols, how='left', left_on='name', right_on='BUYER')
    
    result = buyer[(buyer['transaction_no'] > transaction) & (buyer['volume'] > volume)]
    
    result.drop(columns=['BUYER_x','BUYER_y'], inplace=True)
    
    return result
    

def filter_data_datetime(df, mintime, maxtime):
    return df[df['ACTUAL ARRIVAL DATE'].between(mintime, maxtime, inclusive='both')]

def overall_chart(df):
    pass

timeframe_area = st.empty()
overall_area = st.empty()
filter_area = st.empty()
detail_area = st.empty()

data, mintime, maxtime = fetch_transaction()

with timeframe_area.container(border=True):
    st.markdown('### Set timeframe to consider')  
    timeframe = st.slider('Select timeframe', 
                           min_value=mintime,
                           max_value=maxtime,
                           value=(mintime, maxtime))
    
with overall_area.container(border=True):
    st.markdown('### Overview')    
    stat_area = st.empty()
    
    df = filter_data_datetime(data, timeframe[0], timeframe[1])
        
    with stat_area.container():
        col1, col2, col3, col4 = st.columns([0.15,0.15,0.15,0.15])
        with col1.container(border=True):
            record_count = st.metric(
                label='Total Transaction No.',
                value='{:,}'.format(df.shape[0]),
            )
        with col2.container(border=True):
            volume_sum = st.metric(
                label='Total Volume (in MT)',
                value = '{:,.2f}'.format(df['WEIGHT (MT)'].sum()),
            )
        with col3.container(border=True):
            buyer_count = st.metric(
                label='Buyer No.',
                value='{:,}'.format(len(df['BUYER'].unique())),
            )
        with col4.container(border=True):
            supplier_count = st.metric(
                label='Supplier No.',
                value='{:,}'.format(len(df['SUPPLIER'].unique())),
            )
        general_chart = st.empty()        
        
        with general_chart.container(border=True):
            time_basis = st.radio(label='Time basis',
                                      options=['Monthly','Daily'],
                                      index=0)
            temp = df.copy()
            if time_basis == 'Daily':
                temp['Time'] = temp['ACTUAL ARRIVAL DATE']
                temp['Time'] = temp['Time'].astype(str)
                agg_volume = temp.groupby(['Time'])['WEIGHT (MT)'].sum().reset_index()
                agg_buyer = temp.groupby(['Time'])['BUYER'].nunique().reset_index()
                agg_buyer.rename(columns={'BUYER':'count'}, inplace=True)
                agg_buyer['role'] = 'BUYER'
                agg_supplier = temp.groupby(['Time'])['SUPPLIER'].nunique().reset_index()
                agg_supplier.rename(columns={'SUPPLIER':'count'}, inplace=True)
                agg_supplier['role'] = 'SUPPLIER'
                agg_buyer_sup = pd.concat([agg_buyer,agg_supplier], ignore_index=True)
                
            elif time_basis == 'Monthly':
                temp['Time'] = temp['ACTUAL ARRIVAL DATE'].apply(lambda x: str(x.year) + str(x.month) if x.month > 9 else str(x.year) + '0' + str(x.month)) 
                agg_volume = temp.groupby(['Time'])['WEIGHT (MT)'].sum().reset_index()
                agg_buyer = temp.groupby(['Time'])['BUYER'].nunique().reset_index()
                agg_buyer.rename(columns={'BUYER':'count'}, inplace=True)
                agg_buyer['role'] = 'BUYER'
                agg_supplier = temp.groupby(['Time'])['SUPPLIER'].nunique().reset_index()
                agg_supplier.rename(columns={'SUPPLIER':'count'}, inplace=True)
                agg_supplier['role'] = 'SUPPLIER'
                agg_buyer_sup = pd.concat([agg_buyer,agg_supplier], ignore_index=True)
                agg_buyer_byvol = temp.groupby(['BUYER'])['WEIGHT (MT)'].sum().sort_values(ascending=True)[-10:].reset_index()
                agg_buyer_bytrans = temp.groupby(['BUYER'])['WEIGHT (MT)'].count().sort_values(ascending=True)[-10:].reset_index()
                
            col1, col2 = st.columns([0.5,0.6])
            with col1:
                fig = px.bar(
                    agg_buyer_byvol, 
                    x='WEIGHT (MT)', 
                    y='BUYER',
                    orientation='h',
                    title='Top 10 Buyer in Volume'
                )
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig = px.bar(
                    agg_buyer_bytrans, 
                    x='WEIGHT (MT)', 
                    y='BUYER',
                    orientation='h',
                    title='Top 10 Buyer in Transaction No.'
                )
                st.plotly_chart(fig, use_container_width=True)
                
            col1, col2 = st.columns([0.5,0.6])
            with col1:                
                fig = px.line(
                    agg_volume, 
                    x='Time', 
                    y='WEIGHT (MT)',
                    title='Total Volume Over Time'
                )
                fig.update_layout(
                    xaxis_type='category',
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig = px.bar(
                    agg_buyer_sup, 
                    x='Time', 
                    y='count',
                    color='role',
                    title='No. of Buyers and Supplier Involved in Trades Over Time'
                )
                fig.update_layout(
                    xaxis_type='category',
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with filter_area.container(border=True):
        st.markdown('### Buyer Filter')
        criteria_area = st.form("Criteria to filter")
        result_area = st.empty()
        export_area = st.empty()
        with criteria_area.container():
            st.markdown('##### Criteria')
            col1, col2, col3 = st.columns([0.3,0.3,0.2])
            with col1:
                transaction_threshold = st.number_input(label='Minimum Transaction No.',
                                                        min_value=0,
                                                        max_value=None,
                                                        value='min',
                )
            with col2:
                volume_threshold = st.number_input(label='Minimum Volume (in MT)',
                                                   min_value=0,
                                                   max_value=None,
                                                   step=1,
                                                   value='min'
                )
            with col3:
                country = st.selectbox(label='Country',
                                       options=[],
                                       index=None,
                                       disabled=True
                )
            
            submit_button = st.form_submit_button(label="Generate") 
        
        if submit_button:
            result = aggregate_filter(df, transaction_threshold, volume_threshold, country)
            st.dataframe(result, height=300)
            datetime_stamp = f"{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"
            
            result.to_excel(f'logs/report_{datetime_stamp}.xlsx', index=None)
            with open(f'logs/report_{datetime_stamp}.xlsx', 'rb') as file:
                byte = file.read()
            
            st.download_button(
                label='Download data',
                data=byte,
                file_name=f'report_{datetime_stamp}.xlsx',
                mime='application/octet-stream',
                )
                
    with detail_area.container(border=True):
        buyer = fetch_buyer()
        st.markdown('### Buyer Information')
        criteria_area = st.empty()
        chart_area = st.empty()
        with criteria_area.container():
            buyer_name = st.selectbox(
                label='Buyer name',
                options=buyer['name'].tolist(),
                index=None
            )
        if buyer_name != None:
            buyer_info = buyer[buyer['name'] == buyer_name]
            st.markdown('##### Infomation')
            st.dataframe(buyer_info, hide_index=True, use_container_width=True)
            temp = data[data['BUYER'] == buyer_name]
            col1, col2 = st.columns([0.7,0.3])
            with col2.container(border=True):
                st.metric(
                    label='Supplier No.',
                    value='{:,}'.format(len(temp['SUPPLIER'].unique()))
                )
                st.metric(
                    label='Transaction No.',
                    value='{:,}'.format(temp.shape[0])
                )
                st.metric(
                    label='Total Volume (in MT)',
                    value='{:,.2f}'.format(temp['WEIGHT (MT)'].sum())
                )
                
            with col1.container(border=True):
                temp['Time'] = temp['ACTUAL ARRIVAL DATE'].apply(lambda x: str(x.year) + str(x.month) if x.month > 9 else str(x.year) + '0' + str(x.month)) 
                agg_volume = temp.groupby(['Time'])['WEIGHT (MT)'].sum().reset_index()
                agg_supplier = temp.groupby(['Time'])['SUPPLIER'].nunique().reset_index()
                agg_supplier.rename(columns={'SUPPLIER':'count'}, inplace=True)
                
                fig = px.line(
                    agg_volume, 
                    x='Time', 
                    y='WEIGHT (MT)',
                    markers=True,
                    title='Volume Over Time',
                )
                fig.update_layout(
                    xaxis_type='category',
                )
                st.plotly_chart(fig, use_container_width=True)