import streamlit as st
import hydralit_components as hc
import datetime
import pandas as pd 
import yfinance as yf
import numpy as np
import pandas_datareader as pdr
import mplfinance as fplt
import backtrader as bt 
import matplotlib.pyplot as plt
import matplotlib
import requests
import tweepy
import plotly.graph_objs as go
from rsi import RSIStrategy
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup as bs
from string import Template
from datetime import date, timedelta
from yahoo_fin import stock_info as si 
from pandas_datareader import data as pdr
from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices
from pypfopt import EfficientFrontier
from pypfopt import risk_models
from pypfopt import expected_returns
from pypfopt import plotting
from pypfopt import objective_functions
import plotly.express as px
import copy
from datetime import datetime
from io import BytesIO
from yahooquery import Screener
import nltk
nltk.download("vader_lexicon")
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from bollingerband import BOLLStrat
import os
import sys
import subprocess

# check if the library folder already exists, to avoid building everytime you load the pahe
if not os.path.isdir("/tmp/ta-lib"):

    # Download ta-lib to disk
    with open("/tmp/ta-lib-0.4.0-src.tar.gz", "wb") as file:
        response = requests.get(
            "http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz"
        )
        file.write(response.content)
    # get our current dir, to configure it back again. Just house keeping
    default_cwd = os.getcwd()
    os.chdir("/tmp")
    # untar
    os.system("tar -zxvf ta-lib-0.4.0-src.tar.gz")
    os.chdir("/tmp/ta-lib")
    os.system("ls -la /app/equity/")
    # build
    os.system("./configure --prefix=/home/appuser")
    os.system("make")
    # install
    os.system("make install")
    # back to the cwd
    os.chdir(default_cwd)
    sys.stdout.flush()

# add the library to our current environment
from ctypes import *

lib = CDLL("/home/appuser/lib/libta_lib.so.0.0.0")
# import library
try:
    import talib
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--global-option=build_ext", "--global-option=-L/home/appuser/lib/", "--global-option=-I/home/appuser/include/", "ta-lib"])
finally:
    import talib
st.set_page_config(page_title='Tradelyne', page_icon='📈', layout="wide",initial_sidebar_state='collapsed')
st.markdown('<style>div.block-container{padding-left:0rem;}</style>', unsafe_allow_html=True)
st.markdown("""
        <style>
               .css-18e3th9 {
                    padding-top: 0rem;
                    padding-bottom: 10rem;
                    padding-left: 0rem;
                    padding-right: 5rem;
                }
               .css-1d391kg {
                    padding-top: 3.5rem;
                    padding-right: 1rem;
                    padding-bottom: 3.5rem;
                    padding-left: 1rem;
                }
        </style>
        """, unsafe_allow_html=True)

today=date.today()
oneyr= today - timedelta(days=365)
count=1
newscount=0
additional=[]
def news_headlines(ticker):
    url = finviz_url + ticker
    req = Request(url=url,headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0'}) 
    response = urlopen(req)    
    # Read the contents of the file into 'html'
    html = bs(response)
    # Find 'news-table' in the Soup and load it into 'news_table'
    news_table = html.find(id='news-table')
    return news_table
	
# parse news into dataframe
def parse_news(news_table):
    parsed_news = []
    
    for x in news_table.findAll('tr'):
        # read the text from each tr tag into text
        # get text from a only
        text = x.a.get_text() 
        # splite text in the td tag into a list 
        date_scrape = x.td.text.split()
        # if the length of 'date_scrape' is 1, load 'time' as the only element

        if len(date_scrape) == 1:
            time = date_scrape[0]
            
        # else load 'date' as the 1st element and 'time' as the second    
        else:
            date = date_scrape[0]
            time = date_scrape[1]
        
        # Append ticker, date, time and headline as a list to the 'parsed_news' list
        parsed_news.append([date, time, text])        
        # Set column names
        columns = ['date', 'time', 'headline']
        # Convert the parsed_news list into a DataFrame called 'parsed_and_scored_news'
        parsed_news_df = pd.DataFrame(parsed_news, columns=columns)        
        # Create a pandas datetime object from the strings in 'date' and 'time' column
        parsed_news_df['datetime'] = pd.to_datetime(parsed_news_df['date'] + ' ' + parsed_news_df['time'])
        
    return parsed_news_df
        
def score_news(parsed_news_df):
    vader = SentimentIntensityAnalyzer()
    
    # Iterate through the headlines and get the polarity scores using vader
    scores = parsed_news_df['headline'].apply(vader.polarity_scores).tolist()

    # Convert the 'scores' list of dicts into a DataFrame
    scores_df = pd.DataFrame(scores)

    # Join the DataFrames of the news and the list of dicts
    parsed_and_scored_news = parsed_news_df.join(scores_df, rsuffix='_right')             
    parsed_and_scored_news = parsed_and_scored_news.set_index('datetime')    
    parsed_and_scored_news = parsed_and_scored_news.drop(['date', 'time'], 1)          
    parsed_and_scored_news = parsed_and_scored_news.rename(columns={"compound": "sentiment_score"})

    return parsed_and_scored_news

def plot_hourly_sentiment(parsed_and_scored_news, ticker):
   
    # Group by date and ticker columns from scored_news and calculate the mean
    mean_scores = parsed_and_scored_news.resample('H').mean()

    # Plot a bar chart with plotly
    fig = px.bar(mean_scores, x=mean_scores.index, y='sentiment_score', title = ticker + ' Hourly Sentiment Scores')
    return fig # instead of using fig.show(), we return fig and turn it into a graphjson object for displaying in web page later

def plot_daily_sentiment(parsed_and_scored_news, ticker):
   
    # Group by date and ticker columns from scored_news and calculate the mean
    mean_scores = parsed_and_scored_news.resample('D').mean()

    # Plot a bar chart with plotly
    fig = px.bar(mean_scores, x=mean_scores.index, y='sentiment_score', title = ticker + ' Daily Sentiment Scores')
    return fig # instead of using fig.show(), we return fig and turn it into a graphjson object for displaying in web page later


def get_fundamentals():
    try:
        # Find fundamentals table
        fundamentals = pd.read_html(str(html), attrs = {'class': 'snapshot-table2'})[0]
        
        # Clean up fundamentals dataframe
        fundamentals.columns = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11']
        colOne = []
        colLength = len(fundamentals)
        for k in np.arange(0, colLength, 2):
            colOne.append(fundamentals[f'{k}'])
        attrs = pd.concat(colOne, ignore_index=True)
    
        colTwo = []
        colLength = len(fundamentals)
        for k in np.arange(1, colLength, 2):
            colTwo.append(fundamentals[f'{k}'])
        vals = pd.concat(colTwo, ignore_index=True)
        
        fundamentals = pd.DataFrame()
        fundamentals['Attributes'] = attrs
        fundamentals['Values'] = vals
        fundamentals = fundamentals.set_index('Attributes')
        return fundamentals

    except Exception as e:
        return e
def get_news():
    try:
        # Find news table
        news = pd.read_html(str(html), attrs = {'class': 'fullview-news-outer'})[0]
        links = []
        for a in html.find_all('a', class_="tab-link-news"):
            links.append(a['href'])
        
        # Clean up news dataframe
        news.columns = ['Date', 'News Headline']
        news['Article Link'] = links
        news = news.set_index('Date')
        return news

    except Exception as e:
        return e

def get_insider():
    try:
        # Find insider table
        insider = pd.read_html(str(html), attrs = {'class': 'body-table'})[0]
        
        # Clean up insider dataframe
        insider = insider.iloc[1:]
        insider.columns = ['Trader', 'Relationship', 'Date', 'Transaction', 'Cost', '# Shares', 'Value ($)', '# Shares Total', 'SEC Form 4']
        insider = insider[['Date', 'Trader', 'Relationship', 'Transaction', 'Cost', '# Shares', 'Value ($)', '# Shares Total', 'SEC Form 4']]
        insider = insider.set_index('Date')
        return insider

    except Exception as e:
        return e
def backtestrsi(ticker, start, end, cash):
    global strategy
    cash=int(cash)
    cerebro=bt.Cerebro()
    cerebro.broker.set_cash(cash)
    start_value=cash
    data = bt.feeds.PandasData(dataname=yf.download(ticker, start, end))
    start=start.split("-")
    end=end.split("-")
    for i in range(len(start)):
        start[i]=int(start[i])
    for j in range(len(end)):
        end[j]=int(end[j])
    year=end[0]-start[0]
    month=end[1]-start[1]
    day=end[2]-start[2]
    totalyear=year+(month/12)+(day/365)
    matplotlib.use('Agg')
    plt.show(block=False)
    cerebro.adddata(data)
    cerebro.addstrategy(RSIStrategy)
    cerebro.addanalyzer(bt.analyzers.PyFolio ,_name='pf')
    cerebro.addanalyzer(bt.analyzers.PeriodStats, _name='cm')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='dd')
    cerebro.addanalyzer(bt.analyzers.VWR, _name='vwr')
    cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer ,_name='ta')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio ,_name='sr')

    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    stratdd=cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    #back=Backtest(data, RSIStrategy, cash=10000)
    #stats=back.run()
    strat0 = stratdd[0]
    pyfolio = strat0.analyzers.getbyname('pf')
    returnss, positions, transactions, gross_lev,  = pyfolio.get_pf_items()
    final_value=cerebro.broker.getvalue()
    final_value=round(final_value, 2)
    returns=(final_value-start_value)*100/start_value
    annual_return=returns/totalyear
    returns=str(round(returns, 2))
    annual_return=str(round(annual_return,2))
    figure = cerebro.plot(style='line')[0][0]
    graph, blank, info=st.columns([2,0.2, 1])
    print(stratdd[0].analyzers.dd.get_analysis())
    with graph:
        st.pyplot(figure)
    with blank: 
        st.write(' ')
    with info:
        st.header(strategy)
        st.write(' ')
        st.write(' ')
        trade=stratdd[0].analyzers.ta.get_analysis()
        tra=''
        trade=stratdd[0].analyzers.ta.get_analysis()
                #x=trade[i]
                #for i in x:
                #    tra=tra+(i.upper(), ':', x[i])
                #    st.write(tra)
        print(trade)
        #st.write(trade)
        if int(start_value)<=int(final_value):
            fig = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = final_value,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Strategy returns"},
            delta = {'reference': start_value, 'increasing': {'color': "royalblue"}},
            gauge={'axis': {'range': [None, final_value*6/5], 'tickwidth': 1, 'tickcolor': "green"},
                'bar': {'color': "green"},
                'steps': [
                    {'range': [0, start_value], 'color': '#D3D3D3'},
                    {'range': [start_value, final_value], 'color': 'royalblue'}],}
            ))
            fig.update_layout(paper_bgcolor = "white", font = {'color': "black", 'family': "Arial"}, width=500, height=500,)
            #st.plotly_chart(fig, width=5)
        else:
            fig = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = final_value,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Strategy returns"},
            delta = {'reference': start_value, 'decreasing': {'color': "black"}},
            gauge={'axis': {'range': [None, start_value*6/5], 'tickwidth': 1, 'tickcolor': "red"},
                'bar': {'color': "red"},
                'steps': [
                    {'range': [0, start_value], 'color': 'white'},
                    {'range': [final_value, start_value], 'color': '#D3D3D3'}],}
            ))
            fig.update_layout(paper_bgcolor = "white", font = {'color': "black", 'family': "Arial"}, width=500, height=500)
            #st.plotly_chart(fig)
        #st.subheader('Total returns: ', f"{returns}")
        #st.subheader('Annual returns: ', f"{annual_return}")
        st.subheader(f"{ticker}'s total returns are {returns}% with a {annual_return}% APY")
        st.subheader(f'Initial investment: {cash}')
        st.subheader(f'Final investment value: {final_value}')
        sr=stratdd[0].analyzers.sr.get_analysis()
        print(sr)
        for i in sr:
            ratio=sr[i]
        ratio=str(round(ratio, 3))
        print(ratio)
        st.subheader(f'Sharpe Ratio: {ratio}')
        dd=stratdd[0].analyzers.dd.get_analysis()
        max=dd['max']
        print(max)
        #max=max[1]
        drawdown='Drawdown Stats: \n'
        for i in max:
            max[i]=str(round(max[i], 3))
            drawdown=f"{drawdown} {i} : {max[i]}  |    "
        print(drawdown)
        st.subheader(drawdown)
        st.subheader('Trade Details')
        for i in trade:
            if i=='total' or i=='pnl' or i=='streak' or i=='lost' or i=='won':
                if i=='pnl':
                    pass
                    for j in i:
                        pass
                x=str(trade[i])
                for k in "[]()''":
                    x=x.replace(k, '')
                x=x.replace('AutoOrderedDict', '')
                st.write(i,x)
    st.write('')
    st.subheader(f"{ticker}'s total returns are {returns}% with a {annual_return}% APY")
    #final_value=round(returns, 2)
    st.write(f'Initial investment: {cash}')
    st.write(f'Final money: {final_value}')
    st.write(stratdd[0].analyzers.sr.get_analysis())
    #st.write(stats)
    strategy=''
def volatility(ticker, start, end, cash):
    global strategy
    import backtrader as bt
    import os
    from VIXStrategy import VIXStrategy
    import yfinance as yf
    import pandas as pd
    cash=int(cash)
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(cash)
    start_value=cash
    class SPYVIXData(bt.feeds.GenericCSVData):
        lines = ('vixopen', 'vixhigh', 'vixlow', 'vixclose',)

        params = (
            ('dtformat', '%Y-%m-%d'),#'dtformat', '%Y-%m-%d'),
            ('date', 0),
            ('spyopen', 1),
            ('spyhigh', 2),
            ('spylow', 3),
            ('spyclose', 4),
            ('spyadjclose', 5),
            ('spyvolume', 6),
            ('vixopen', 7),
            ('vixhigh', 8),
            ('vixlow', 9),
            ('vixclose', 10)
        )

    class VIXData(bt.feeds.GenericCSVData):
            params = (
            ('dtformat', '%Y-%m-%d'),
            ('date', 0),
            ('vixopen', 1),
            ('vixhigh', 2),
            ('vixlow', 3),
            ('vixclose', 4),
            ('volume', -1),
            ('openinterest', -1)
        )
    #
    ticker=ticker
    df = yf.download(tickers=ticker, start=start, end=end, rounding= False)
    df=df.reset_index() 
    df2 = yf.download(tickers='^VIX', start=start, end=end, rounding= False)
    df2.rename(columns = {'Open':'Vix Open', 'High':'Vix High', 'Low':'Vix Low', 'Close':'Vix Close'}, inplace = True)
    df2=df2.drop("Volume", axis=1)
    df2=df2.drop("Adj Close", axis=1)
    df2=df2.reset_index()
    df3=df2
    df2=df2.drop("Date", axis=1)
    result=pd.concat([df, df2], axis=1, join='inner')
    results=result
    df3.to_csv(r'https://github.com/Utkarshhh20/tradelyne/blob/main/code/trial.csv')
    results.to_csv(r'https://github.com/Utkarshhh20/tradelyne/blob/main/code/trial2.csv')
    first_column1 = results.columns[0]
    results.to_csv('trial2.csv', index=False)
    results = pd.read_csv('trial2.csv')
    # If you know the name of the column skip this
    # Delete first
    #result = result.iloc[: , 1:]
    # If you know the name of the column skip this
    first_column2 = df3.columns[0]
    # Delete first
    df3.to_csv('trial.csv', index=False)
    st.dataframe(result)
    st.dataframe(df3)
    csv_file = os.path.dirname(os.path.realpath(__file__)) + "/trial2.csv"
    vix_csv_file = os.path.dirname(os.path.realpath(__file__)) + "/trial.csv"

    spyVixDataFeed = SPYVIXData(dataname=csv_file)
    vixDataFeed = VIXData(dataname=vix_csv_file)
    start=start.split("-")
    end=end.split("-")
    for i in range(len(start)):
        start[i]=int(start[i])
    for j in range(len(end)):
        end[j]=int(end[j])
    year=end[0]-start[0]
    month=end[1]-start[1]
    day=end[2]-start[2]
    totalyear=year+(month/12)+(day/365)
    matplotlib.use('Agg')
    cerebro.adddata(spyVixDataFeed)
    cerebro.adddata(vixDataFeed)

    cerebro.addstrategy(VIXStrategy)

    cerebro.run()
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    final_value=cerebro.broker.getvalue()
    returns=(final_value-start_value)*100/start_value
    annual_return=returns/totalyear
    returns=round(returns, 2)
    annual_return=round(annual_return,2)
    returns=str(returns)
    annual_return=str(annual_return)
    figure = cerebro.plot(volume=False)[0][0]
    st.pyplot(figure)
    st.subheader(f"{ticker}'s total returns are {returns}% with a {annual_return}% APY")
    strategy=''

def backtestgolden(ticker, start, end, cash):
    global strategy
    cash=int(cash)
    cerebro=bt.Cerebro()
    cerebro.broker.set_cash(cash)
    start_value=cash
    data = bt.feeds.PandasData(dataname=yf.download(ticker, start, end))
    start=start.split("-")
    end=end.split("-")
    for i in range(len(start)):
        start[i]=int(start[i])
    for j in range(len(end)):
        end[j]=int(end[j])
    year=end[0]-start[0]
    month=end[1]-start[1]
    day=end[2]-start[2]
    totalyear=year+(month/12)+(day/365)
    matplotlib.use('Agg')
    cerebro.adddata(data)

    cerebro.addstrategy(goldencrossover)

    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    cerebro.run()

    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    final_value=cerebro.broker.getvalue()
    returns=(final_value-start_value)*100/start_value
    annual_return=returns/totalyear
    returns=round(returns, 2)
    annual_return=round(annual_return,2)
    returns=str(returns)
    annual_return=str(annual_return)
    figure = cerebro.plot()[0][0]
    graph, blank, info = st.columns([2,0.2,1])
    with graph:
        st.pyplot(figure)
    with blank:
        st.write(' ')
    with info:
        st.header(strategy)
        st.write(' ')
        st.write(' ')
        st.subheader(f"{ticker}'s total returns are {returns}% with a {annual_return}% APY")
    strategy=''
def backtestbb(ticker, start, end, cash):
    global strategy
    cash=int(cash)
    cerebro=bt.Cerebro()
    cerebro.broker.set_cash(cash)
    start_value=cash
    data = bt.feeds.PandasData(dataname=yf.download(ticker, start, end))
    matplotlib.use('Agg')
    plt.show(block=False)
    cerebro.adddata(data)
    cerebro.addstrategy(BOLLStrat)
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
    figure = cerebro.plot(style='line')[0][0]
    graph, blank, info = st.columns([2,0.2,1])
    with graph:
        st.pyplot(figure)
    with blank:
        st.write(' ')
    with info:
        st.header(strategy)
        st.write(' ')
        st.write(' ')
        st.subheader(f"{ticker}'s total returns are {returns}% with a {annual_return}% APY")
    strategy=''

menu_data = [
    {'icon': "fa fa-desktop", 'label':"Fundamental Indicators"},
    {'icon': "fa fa-signal", 'label':"Chart Analysis"},
    {'icon': "fa fa-angle-double-left", 'label':"Backtesting"},
    {'icon': "bi bi-pie-chart", 'label':"Portfolio Optimizer"},
    {'icon': "bi bi-twitter", 'label':"Twitter Analysis"},
]
#    {'icon': "bi bi-telephone", 'label':"Contact us"},
over_theme = {'txc_inactive': "#D3D3D3",'menu_background':'#3948A5','txc_active':'white','option_active':'#3948A5'}
dashboard = hc.nav_bar(
menu_definition=menu_data,
override_theme=over_theme,
home_name='Tradelyne',
hide_streamlit_markers=True, #will show the st hamburger as well as the navbar now!
sticky_nav=True, #at the top or not
sticky_mode='sticky', #jumpy or not-jumpy, but sticky or pinned
use_animation=True,
key='NavBar'
)
if dashboard=='Tradelyne':
    logo='''
        <style>
        .logo{
            width: 370px;
            margin-top:-20px;
            margin-left:-30px;
        }
        </style>
        <body>
        <center><img src='https://cdn.myportfolio.com/fd40c2a8-1f6f-47d7-8997-48ba5415a69c/6c46ac13-6a18-427a-9baa-01ad3b53ac45_rw_600.png?h=21b14417887f0576feb32fcbfd191788' alt='logo' class='logo'></img></center> 
        </body>
        '''
    what='''
    <link href='https://fonts.googleapis.com/css?family=Montserrat' rel="stylesheet">
    <style>
    .what{
        font-family: 'Montserrat';
        font-size:1.8em;
        color:limegreen;
        font-weight:600;
        margin-top:0px;
    }
    </style>
    <body>
        <center><p1 class='what'>What is Tradelyne?</p1></center>
    </body>
    '''
    whatinfo='''
    <link href='https://fonts.googleapis.com/css?family=Montserrat' rel="stylesheet">
    <style>
    .whatinfo{
        font-family: 'Montserrat';
        font-size:1.2em;
        color:;
        font-weight:600;
        margin-top:80px;
    }
    </style>
    <body>
        <center><p1 class='whatinfo'>Tradelyne is a web application developed on python using the streamlit library which aims to provide you with the tools necessary to make trading and investing much simpler. Using this web app you can enhance and optimize your investing skills and take advantage of every opportunity presented to you by the market</p1></center>
    </body>
    '''
    whatcan='''
    <link href='https://fonts.googleapis.com/css?family=Montserrat' rel="stylesheet">
    <style>
    .whatcan{
        font-family: 'Montserrat';
        font-size:1.8em;
        color:limegreen;
        font-weight:600;
        margin-top:;
    }
    </style>
    <body>
        <center><p1 class='whatcan'>What can I do with Tradelyne?</p1></center>
    </body>
    '''
    tech='''
        <style>
        .taimg {
        float: center;
        z-index: 1;
        width: 400px;
        position: relative;
        border-radius: 5%;
        margin-left: 0px;
        }
        </style>
        <body>
        <center><img src="https://cdn.myportfolio.com/fd40c2a8-1f6f-47d7-8997-48ba5415a69c/5422f547-b577-4c88-8d2d-be32f80ddb6e_rw_1200.png?h=d5f92fc4f63b8cace8a88e175fba4c09" alt="House" class='taimg'></img> </center>
        </body>'''
    techtxt='''
        <link href='https://fonts.googleapis.com/css?family=Montserrat' rel="stylesheet">
        <style>
        .techtxt {
            font-family: 'Montserrat';
            font-size: 25px;
            margin-top:0px;
            font-weight: 700;
            margin-bottom: 0px;
        }
        </style>
        <body>
        <center> <p1 class='techtxt'> TECHNICAL INDICATORS </p1> </center>
        </body>
        '''
    techsubtxt='''
        <link href='https://fonts.googleapis.com/css?family=Montserrat' rel="stylesheet">
        <style>
        .techsubtxt {
            font-family: 'Montserrat';
            font-size: 15px;
            margin-top:20px;
            font-weight: 600;
            margin-bottom: 0px;
        }
        </style>
        <body>
        <center> <p1 class='techsubtxt'> Find the latest patterns emerging within stocks or locate stocks that showcase a recent pattern using our technical indicators feature. This will help you speculate the upcoming price movement for a stock.</p1> </center>
        </body>
        '''
    fundament='''
    <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
        .faimg {
        float: center;
        z-index: 1;
        width: 400px;
        position: relative;
        border-radius: 5%;
        margin-left: 10px;
        }
        </style>
        <body>
        <img src="https://cdn.myportfolio.com/fd40c2a8-1f6f-47d7-8997-48ba5415a69c/b2b81a88-c138-4f39-98c4-30e584c2630d_rw_1200.png?h=e48bbaf3b2070bfd3564e3dfb90693f6" alt="House" class='faimg'></img>
        </body>'''
    fundtxt='''
        <link href='https://fonts.googleapis.com/css?family=Montserrat' rel="stylesheet">
        <style>
        .fundtxt {
            font-family: 'Montserrat';
            font-size: 25px;
            margin-top:0px;
            font-weight: 700;
            margin-bottom: 0px;
        }
        </style>
        <body>
        <center> <p1 class='fundtxt'> FUNDAMENTAL ANALYSIS </p1> </center>
        </body>
        '''
    fundsubtxt='''
        <link href='https://fonts.googleapis.com/css?family=Montserrat' rel="stylesheet">
        <style>
        .fundsubtxt {
            font-family: 'Montserrat';
            font-size: 15px;
            margin-top:20px;
            font-weight: 600;
            margin-bottom: 0px;
        }
        </style>
        <body>
        <center> <p1 class='fundsubtxt'> Check the latest fundamentals of a stock using our fundamental analysis feature. Utilize the information on the recent insider trades and news of the company of your choice to make profits. </p1> </center>
        </body>
        '''
    backt='''
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
        .btimg {
        float: center;
        z-index: 1;
        width: 400px;
        position: relative;
        border-radius: 5%;
        }
        </style>
        <body>
        <center><img src="https://cdn.myportfolio.com/fd40c2a8-1f6f-47d7-8997-48ba5415a69c/9fc904be-d0ec-4133-8195-eb3b3a70baa0_rw_1200.png?h=ed21f3a2df57756a450942d68ed6c7a4" alt="House" class='btimg'></img></center>
        <p1 class>
        </body>'''
    bttxt='''
        <link href='https://fonts.googleapis.com/css?family=Montserrat' rel="stylesheet">
        <style>
        .techtxt {
            font-family: 'Montserrat';
            font-size: 25px;
            margin-top:0px;
            font-weight: 700;
            margin-bottom: 0px;
        }
        </style>
        <body>
        <center> <p1 class='techtxt'> BACKTESTING </p1> </center>
        </body>
        '''
    btsubtxt='''
        <link href='https://fonts.googleapis.com/css?family=Montserrat' rel="stylesheet">
        <style>
        .btsubtxt {
            font-family: 'Montserrat';
            font-size: 15px;
            margin-top:20px;
            font-weight: 600;
            margin-bottom: 0px;
        }
        </style>
        <body>
        <center> <p1 class='btsubtxt'> What if you had invested your money in a stock using a certain startegy? How much profit would you have made? Find out using our backtesting feature which has certain predefined strategies to backtest. </p1> </center>
        </body>
        '''
    st.markdown(logo, unsafe_allow_html=True)
    st.markdown(what, unsafe_allow_html=True)
    st.write('')
    blank1,text,blank2=st.columns([0.1,1,0.1])
    st.write('')
    st.write('______________________________________')
    with blank1:
        st.write('')
    with text:
        st.markdown(whatinfo, unsafe_allow_html=True)
    with blank2:
        st.write('')
    st.markdown(whatcan, unsafe_allow_html=True)
    technical,fundamental,backtest=st.columns(3)
    with technical:
        st.markdown(tech, unsafe_allow_html=True)
        st.markdown(techtxt, unsafe_allow_html=True)
        st.markdown(techsubtxt, unsafe_allow_html=True)
        st.write('____________________')
    with fundamental:
        st.markdown(fundament, unsafe_allow_html=True)
        st.markdown(fundtxt, unsafe_allow_html=True)
        st.markdown(fundsubtxt, unsafe_allow_html=True)
        st.write('____________________')
    with backtest:
        st.markdown(backt, unsafe_allow_html=True)
        st.markdown(bttxt, unsafe_allow_html=True)
        st.markdown(btsubtxt, unsafe_allow_html=True)
        st.write('____________________')

elif dashboard=='Fundamental Indicators':
    st.write(' ')
    st.write(' ')
    st.write(' ')	
    screen, start, end, stock=st.columns([0.7,0.7,0.7,0.7])	
    screener='''
    <link href='https://fonts.googleapis.com/css?family=Montserrat' rel="stylesheet">
    <style>
    .screener {
        font-family:Montserrat;
        font-size:35px;
        font-weight:1000;
        font-style: bold;
        margin-left:0px;
        margin-top: 35px;
    }
    </style>

    <body>
    <center><p1 class='screener'>FUNDAMENTALS</p1></center>
    </body>
    '''
    with screen:
        st.markdown(screener, unsafe_allow_html=True)
    with start:
        start_date= st.date_input("Start date", oneyr)
    with end:
        end_date = st.date_input("End date", today)
    with stock:
            ticker_list = pd.read_csv('https://raw.githubusercontent.com/dataprofessor/s-and-p-500-companies/master/data/constituents_symbols.txt')
            tickerSymbol = st.text_input('Stock ticker', value='TSLA')# ticker_list Select ticker symbol
            tickerData = yf.Ticker(tickerSymbol) # Get ticker data
            tickerDf = tickerData.history(period='1d', start=start_date, end=end_date) #get the historical prices for this ticker

            # Ticker information
            string_image=tickerData.info['logo_url']
            string_logo = '<img src=%s>' % tickerData.info['logo_url']
    if string_logo=='<img src=>':
            blank1, error, blank2=st.columns([0.8,1,0.2])
            with blank1:
                st.write(' ')
            with error:
                st.write(' ')
                st.write('Please enter a valid stock ticker or timeline for the stock. Please ensure the ticker is capitalized')
            with blank2:
                st.write(' ')
    else:
            company_logo='''
            <style>
            .companylogo {
                width:180px;
                margin-left:20px;
            }
            </style>
            <body>
            <img src=$code alt='Company logo' class='companylogo'></img>
            </body>
            '''
            company_image = Template(company_logo).safe_substitute(code=string_image)

            name='''
            <link href='https://fonts.googleapis.com/css?family=Montserrat' rel="stylesheet">
            <style>
            .companyname {
                font-family: Montserrat;
                font-size:35px;
                font-weight:700;
                margin-left:-10px;
                margin-top:0px;
            }
            </style>
            <body>
            <p1 class='companyname'>$compname</p1>
            </body>
            '''
            string_name = tickerData.info['longName']
            company_name = Template(name).safe_substitute(compname=string_name)

            sector='''
            <link href='https://fonts.googleapis.com/css?family=Montserrat' rel="stylesheet">
            <style>
            .companysector {
                font-family: Montserrat;
                font-size:25px;
                font-weight:600;
                margin-left:-10px;
                margin-top:0px;
            }
            </style>
            <body>
            <p1 class='companysector'>Sector: $compsector</p1>
            </body>
            '''
            string_sector=tickerData.info['sector']
            company_sector = Template(sector).safe_substitute(compsector=string_sector)

            blank,image,info=st.columns([0.15,1.2,2])
            with blank:
                st.write(' ')
            with image:
                st.write(' ')
                st.write(' ')
                st.write(' ')
                st.markdown(company_image, unsafe_allow_html=True)
                st.write(' ')
                st.write(' ')
                st.markdown(company_name, unsafe_allow_html=True)
                st.markdown(company_sector, unsafe_allow_html=True)
            with info:
                st.write(' ')
                string_summary = tickerData.info['longBusinessSummary']
                st.info(string_summary)
            fundamentals, blank, data_show=st.columns([0.35,0.02,1])
            #if show_data:
            with fundamentals:
                st.markdown('---')
                pd.set_option('display.max_colwidth', 25)
                fundament_header='''
                        <link href='https://fonts.googleapis.com/css?family=Montserrat' rel="stylesheet">
                        <style>
                            .fundamenthead {
                            font-family:Montserrat;
                            font-size:30px;
                            font-weight:1000;
                            font-style: bold;
                            float:left;
                            margin-left:0px;
                            margin-top: 10px;
                        }
                        </style>

                        <body>
                        <center><p1 class='fundamenthead'> &nbsp $fundamentheader 's Fundamentals  &nbsp</p1></center>
                        </body>
                        '''
                cofpltundheader = Template(fundament_header).safe_substitute(fundamentheader=tickerSymbol)
                st.markdown(cofpltundheader, unsafe_allow_html=True)
                # Set up scraper
                url = ("https://finviz.com/quote.ashx?t=" + tickerSymbol.lower())
                req = Request(url=url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0'})
                webpage = urlopen(req)
                html = bs(webpage, "html.parser")
                fundament=get_fundamentals()
                st.table(fundament)
            with blank:
                st.write(' ')
            with data_show:
                st.markdown('---')
                dataheader='''
                        <link href='https://fonts.googleapis.com/css?family=Montserrat' rel="stylesheet">
                        <style>
                            .datahead {
                            font-family:Montserrat;
                            font-size:30px;
                            font-weight:1000;
                            font-style: bold;
                            float:left;
                            margin-left:0px;
                            margin-top: 10px;
                        }
                        </style>

                        <body>
                        <center><p1 class='datahead'> &nbsp $compdata 's Ticker Data  &nbsp</p1></center>
                        </body>
                        '''
                compdataheader = Template(dataheader).safe_substitute(compdata=tickerSymbol)
                st.markdown(compdataheader, unsafe_allow_html=True)
                st.dataframe(tickerDf)
                info = tickerData.info 
                st.write('___________________________')
                st.write('')
                insiderheader='''
                        <link href='https://fonts.googleapis.com/css?family=Montserrat' rel="stylesheet">
                        <style>
                            .insidehead {
                            font-family:Montserrat;
                            font-size:30px;
                            font-weight:1000;
                            font-style: bold;
                            float:left;
                            margin-left:0px;
                            margin-top: 10px;
                        }
                        </style>

                        <body>
                        <center><p1 class='insidehead'> Recent trades made by company's officials </p1></center>
                        </body>
                        '''
                st.markdown(insiderheader, unsafe_allow_html=True)
                #st.subheader("\n\nRecent trades made by company's officials")
                inside=get_insider()
                st.dataframe(inside)
                st.write('___________________________')
                st.write('')
                news=get_news()
                insiderheader='''
                        <link href='https://fonts.googleapis.com/css?family=Montserrat' rel="stylesheet">
                        <style>
                            .insidehead {
                            font-family:Montserrat;
                            font-size:30px;
                            font-weight:1000;
                            font-style: bold;
                            float:left;
                            margin-left:0px;
                            margin-top: 10px;
                        }
                        </style>

                        <body>
                        <center><p1 class='insidehead'> Recent news on $insiderdata stock </p1></center>
                        </body>
                        '''
                insiderdataheader = Template(insiderheader).safe_substitute(insiderdata=tickerSymbol)
                st.markdown(insiderdataheader, unsafe_allow_html=True)
                #st.dataframe(news, width=10000)
                st.write(' ')
                tickers = si.tickers_sp500()
                recommendations = []
                print(news)
                for i in range(len(news)):
                    headline=news['News Headline'][i]
                    link=news['Article Link'][i]
                    st.write(f"{headline}: [More on this article]({link})")
                    newscount=newscount+1
                    if newscount<13:
                        st.write('____________________')
                    if newscount==13:
                        break
            # for extracting data from finviz
            finviz_url = 'https://finviz.com/quote.ashx?t='
            st.write(' ')
            st.write(' ')
            st.write(' ')
            st.header("Stock News Sentiment Analyzer")
            if dashboard=='Fundamental Indicators':
		
	        
                st.subheader("Hourly and Daily Sentiment of {} Stock".format(tickerSymbol))
                news_table = news_headlines(tickerSymbol)
                parsed_news_df = parse_news(news_table)
                parsed_and_scored_news = score_news(parsed_news_df)
                fig_hourly = plot_hourly_sentiment(parsed_and_scored_news, tickerSymbol)
                fig_daily = plot_daily_sentiment(parsed_and_scored_news, tickerSymbol) 
                graph1, graph2=st.columns(2)
                with graph1:
                    st.plotly_chart(fig_hourly, use_container_width=True)
                with graph2:
                    st.plotly_chart(fig_daily, use_container_width=True)

                description = """
                        The above chart averages the sentiment scores of {} stock hourly and daily.
                        The table below gives each of the most recent headlines of the stock and the negative, neutral, positive and an aggregated sentiment score.
                        Sentiments are given by the nltk.sentiment.vader Python library.
                        """.format(tickerSymbol)
                        
                st.write(description)	 
                st.table(parsed_and_scored_news)
                    
if dashboard=='Chart Analysis':
            screen, start, end, stock=st.columns([1.5,0.7,0.7,0.7])
            screener='''
            <link href='https://fonts.googleapis.com/css?family=Montserrat' rel="stylesheet">
            <style>
            .screener {
                font-family:Montserrat;
                font-size:40px;
                font-weight:1000;
                font-style: bold;
                float:left;
                margin-left:20px;
                margin-top: 35px;
            }
            </style>

            <body>
            <p1 class='screener'>CHART ANALYTICS</p1>
            </body>
            '''
            with screen:
                st.markdown(screener, unsafe_allow_html=True)
            with start:
                start_date= st.date_input("Start date", oneyr)
            with end:
                end_date = st.date_input("End date", today)
            with stock:
                    tickerSymbol = st.text_input('Stock ticker', value='TSLA')# ticker_list Select ticker symbol
            matplotlib.use('Agg')
            plt.show(block=False)
        
            st.markdown('---')

            st.subheader('Chart Settings')
            st.caption('Adjust charts settings and then press apply')
                
            with st.form('settings_form'):
                    a,b,c,d,e,f=st.columns(6)
                    #show_data = st.checkbox('Show data table', True)
                    with a:
                        chart_types = [
                        'candle', 'ohlc', 'line', 'renko', 'pnf'
                    ]
                        chart_type = st.selectbox('Chart type', options=chart_types, index=chart_types.index('candle'))
                    with b:
                        chart_styles = [
                        'default', 'binance', 'blueskies', 'brasil', 
                        'charles', 'checkers', 'classic', 'yahoo',
                        'mike', 'nightclouds', 'sas', 'starsandstripes'
                    ]
                        chart_style = st.selectbox('Chart style', options=chart_styles, index=chart_styles.index('yahoo'))
                    with c:
                        overlap_indicators=st.multiselect('Overlap Indicators', options=['Bollinger Bands','SMA20', 'SMA50', 'SMA200', 'EMA12', 'EMA24', 'EMA50', 'EMA200'])
                    with d:
                        momentum_indicators=st.multiselect('Momentum Indicators', options=['RSI', 'MACD', 'Stochastic Indicator', 'Average Directional Index'])
                    with e:
                        volume_indicators=st.multiselect('Volume Indicators', options=['A/D Line', 'On-Balance Volume'])
                    with f:
                        volatility_indicators=st.multiselect('Volatility Indicators', options=['Average True Range', 'Normalized Average True Range'])
                    # https://github.com/matplotlib/mplfinance/blob/master/examples/styles.ipynb
                    g,h,i=st.columns(3)
                    with g:
                        show_nontrading_days = st.checkbox('Non-trading days', False)
                    with h:
                        show_volume = st.checkbox('Volume', True)
                    with i:
                        st.form_submit_button('Apply')

            df=yf.download(tickerSymbol, start=start_date, end=end_date)
            if show_volume==True:
                count=count+1
            for i in overlap_indicators:
                    if i=='Bollinger Bands':
                        #BOLLINGER BANDS
                        start_date_bb=start_date - timedelta(days=17)
                        df_bb=yf.download(tickerSymbol, start=start_date_bb, end=end_date)
                        df_bb=df_bb['Close']
                        upperband, middleband, lowerband = talib.BBANDS(df_bb, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
                        upperband,middleband, lowerband=upperband.dropna(), middleband.dropna(), lowerband.dropna()
                        while len(upperband)<len(df):
                            start_date_bb=start_date_bb - timedelta(days=1)
                            df_bb=yf.download(tickerSymbol, start=start_date_bb, end=end_date)
                            df_bb=df_bb['Close']
                            upperband, middleband, lowerband = talib.BBANDS(df_bb, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
                            upperband,middleband, lowerband=upperband.dropna(), middleband.dropna(), lowerband.dropna()
                        additional.append(fplt.make_addplot(upperband, width=0.5))
                        additional.append(fplt.make_addplot(middleband, width=0.5))
                        additional.append(fplt.make_addplot(lowerband, width=0.5))
                    if i=='SMA20':
                        #SMA 20
                        start_date_sma20=start_date - timedelta(days=18)
                        df_sma20=yf.download(tickerSymbol, start=start_date_sma20, end=end_date)
                        sma20=talib.SMA(df_sma20["Close"], timeperiod=20)
                        sma20=sma20.dropna()
                        while len(sma20)<len(df):
                            start_date_sma20=start_date_sma20 - timedelta(days=1)
                            df_sma20=yf.download(tickerSymbol, start=start_date_sma20, end=end_date)
                            sma20=talib.SMA(df_sma20["Close"], timeperiod=20)
                            sma20=sma20.dropna()
                        additional.append(fplt.make_addplot(sma20, width=0.5))
                    if i=='SMA50':
                        #SMA 50
                        start_date_sma50=start_date - timedelta(days=48)
                        df_sma50=yf.download(tickerSymbol, start=start_date_sma50, end=end_date)
                        sma50=talib.SMA(df_sma50["Close"], timeperiod=50)
                        sma50=sma50.dropna()
                        while len(sma50)<len(df):
                            start_date_sma50=start_date_sma50 - timedelta(days=1)
                            df_sma50=yf.download(tickerSymbol, start=start_date_sma50, end=end_date)
                            sma50=talib.SMA(df_sma50["Close"], timeperiod=50)
                            sma50=sma50.dropna()
                        additional.append(fplt.make_addplot(sma50, width=0.5))
                    if i=='SMA200':
                        #SMA 200
                        start_date_sma200=start_date - timedelta(days=198)
                        df_sma200=yf.download(tickerSymbol, start=start_date_sma200, end=end_date)
                        sma200=talib.SMA(df_sma200["Close"], timeperiod=200)
                        sma200=sma200.dropna()
                        while len(sma200)<len(df):
                            start_date_sma200=start_date_sma200 - timedelta(days=1)
                            df_sma200=yf.download(tickerSymbol, start=start_date_sma200, end=end_date)
                            sma200=talib.SMA(df_sma200["Close"], timeperiod=200)
                            sma200=sma200.dropna()
                        additional.append(fplt.make_addplot(sma200, width=0.5))
                    if i=='EMA12':
                        #EMA 12
                        start_date_ema12=start_date - timedelta(days=10)
                        df_ema12=yf.download(tickerSymbol, start=start_date_ema12, end=end_date)
                        ema12=talib.EMA(df_ema12["Close"], timeperiod=12)
                        ema12=ema12.dropna()
                        while len(ema12)<len(df):
                            start_date_ema12=start_date_ema12 - timedelta(days=1)
                            df_ema12=yf.download(tickerSymbol, start=start_date_ema12, end=end_date)
                            ema12=talib.EMA(df_ema12["Close"], timeperiod=12)
                            ema12=ema12.dropna()
                        additional.append(fplt.make_addplot(ema12, width=0.5))
                    if i=='EMA24':
                        #EMA 24
                        start_date_ema24=start_date - timedelta(days=22)
                        df_ema24=yf.download(tickerSymbol, start=start_date_ema24, end=end_date)
                        ema24=talib.EMA(df_ema24["Close"], timeperiod=24)
                        ema24=ema24.dropna()
                        while len(ema24)<len(df):
                            start_date_ema24=start_date_ema24 - timedelta(days=1)
                            df_ema24=yf.download(tickerSymbol, start=start_date_ema24, end=end_date)
                            ema24=talib.EMA(df_ema24["Close"], timeperiod=24)
                            ema24=ema24.dropna()
                        additional.append(fplt.make_addplot(ema24, width=0.5))
                    if i=='EMA50':
                        #EMA 50
                        start_date_ema50=start_date - timedelta(days=48)
                        df_ema50=yf.download(tickerSymbol, start=start_date_ema50, end=end_date)
                        ema50=talib.EMA(df_ema50["Close"], timeperiod=50)
                        ema50=ema50.dropna()
                        while len(ema50)<len(df):
                            start_date_ema50=start_date_ema50 - timedelta(days=1)
                            df_ema50=yf.download(tickerSymbol, start=start_date_ema50, end=end_date)
                            ema50=talib.EMA(df_ema50["Close"], timeperiod=50)
                            ema50=ema50.dropna()
                
                        additional.append(fplt.make_addplot(ema50, width=0.5))
                    if i=='EMA200':
                        #EMA 200
                        start_date_ema200=start_date - timedelta(days=198)
                        df_ema200=yf.download(tickerSymbol, start=start_date_ema200, end=end_date)
                        ema200=talib.EMA(df_ema200["Close"], timeperiod=200)
                        ema200=ema200.dropna()
                        while len(ema200)<len(df):
                            start_date_ema200=start_date_ema200 - timedelta(days=1)
                            df_ema200=yf.download(tickerSymbol, start=start_date_ema200, end=end_date)
                            ema200=talib.EMA(df_ema200["Close"], timeperiod=200)
                            ema200=ema200.dropna()
                        additional.append(fplt.make_addplot(ema200, width=0.5))
                    
            for i in momentum_indicators:
                    if i=='RSI':
                        #RSI
                        start_date_rsi=start_date - timedelta(days=14)
                        df_rsi=yf.download(tickerSymbol, start=start_date_rsi, end=end_date)
                        rsi_data=talib.RSI(df_rsi['Close'], timeperiod=14)
                        rsi_data=rsi_data.dropna()
                        while len(rsi_data)<len(df):
                            print(len(rsi_data),len(df))
                            start_date_rsi=start_date_rsi - timedelta(days=1)
                            df_rsi=yf.download(tickerSymbol, start=start_date_rsi, end=end_date)
                            rsi_data=talib.RSI(df_rsi['Close'], timeperiod=14)
                            rsi_data=rsi_data.dropna()
                        additional.append(fplt.make_addplot(rsi_data,color='#096cad', panel=count, ylabel="RSI"))
                        count=count+1
                    if i=='MACD':
                        #MACD
                        start_date_macd=start_date - timedelta(days=41)
                        df_macd=yf.download(tickerSymbol, start=start_date_macd, end=end_date)
                        macd, macdsignal, macdhist = talib.MACD(df_macd['Close'], fastperiod=12, slowperiod=26, signalperiod=9)
                        macd, macdsignal, macdhist= macd.dropna(), macdsignal.dropna(), macdhist.dropna()
                        while len(macd)<len(df):
                            print(len(macd),len(df))
                            start_date_macd=start_date_macd - timedelta(days=1)
                            df_macd=yf.download(tickerSymbol, start=start_date_macd, end=end_date)
                            macd, macdsignal, macdhist = talib.MACD(df_macd['Close'], fastperiod=12, slowperiod=26, signalperiod=9)
                            macd, macdsignal, macdhist= macd.dropna(), macdsignal.dropna(), macdhist.dropna()
                        additional.append(fplt.make_addplot(macdhist,type='bar',width=0.7,panel=count, color='grey',alpha=1,ylabel='MACD', secondary_y=False))
                        additional.append(fplt.make_addplot(macd,panel=count,color='#096cad',secondary_y=False))
                        additional.append(fplt.make_addplot(macdsignal,panel=count,color='orange',secondary_y=False))
                        count=count+1
                    if i=='Stochastic Indicator':
                        #STOCHASTIC INDICATOR
                        start_date_stoch=start_date-timedelta(days=13)
                        df_stoch=yf.download(tickerSymbol, start=start_date_stoch, end=end_date)
                        slowk, slowd = talib.STOCH(df_stoch['High'], df_stoch['Low'], df_stoch['Close'], fastk_period=14, slowk_period=3, slowk_matype=1, slowd_period=3, slowd_matype=0)
                        slowk, slowd= slowk.dropna(), slowd.dropna()
                        while len(slowk)<len(df):
                            start_date_stoch=start_date_stoch - timedelta(days=1)
                            df_stoch=yf.download(tickerSymbol, start=start_date_stoch, end=end_date)
                            slowk, slowd = talib.STOCH(df_stoch['High'], df_stoch['Low'], df_stoch['Close'], fastk_period=14, slowk_period=3, slowk_matype=1, slowd_period=3, slowd_matype=0)
                            slowk, slowd= slowk.dropna(), slowd.dropna()
                        additional.append(fplt.make_addplot(slowk,panel=count,color='#096cad',ylabel='Stochastic'))
                        additional.append(fplt.make_addplot(slowd,panel=count,color='orange',secondary_y=False))
                        count=count+1
                    if i=='Average Directional Index':
                        #ADX
                        start_date_adx=start_date - timedelta(days=12)
                        df_adx=yf.download(tickerSymbol, start=start_date_adx, end=end_date)
                        adx=talib.ADX(df_adx['High'], df_adx['Low'], df_adx["Close"], timeperiod=14)
                        adx=adx.dropna()
                        while len(adx)<len(df):
                            start_date_adx=start_date_adx - timedelta(days=1)
                            df_adx=yf.download(tickerSymbol, start=start_date_adx, end=end_date)
                            adx=talib.ADX(df_adx['High'], df_adx['Low'], df_adx["Close"], timeperiod=14)
                            adx=adx.dropna()
                        additional.append(fplt.make_addplot(adx,color='#096cad', panel=count, ylabel="ADX"))
                        count=count+1
            for i in volume_indicators:
                    if i=='A/D Line':
                        #A/D LINE
                        ad=talib.AD(df['High'], df['Low'], df['Close'], df['Volume'])
                        additional.append(fplt.make_addplot(ad, panel=count, ylabel="A/D"))
                        count=count+1
                    if i=='On-Balance Volume':
                        obv=talib.OBV(df['Close'], df['Volume'])
                        additional.append(fplt.make_addplot(obv, panel=count, ylabel="OBV"))
                        count=count+1
            for i in volatility_indicators:
                    if i=='Average True Range':
                        #ATR
                        start_date_atr=start_date - timedelta(days=12)
                        df_atr=yf.download(tickerSymbol, start=start_date_atr, end=end_date)
                        avg_tr=talib.ATR(df_atr['High'], df_atr['Low'], df_atr['Close'], timeperiod=14)
                        avg_tr=avg_tr.dropna()
                        while len(avg_tr)<len(df):
                            start_date_atr=start_date_atr - timedelta(days=1)
                            df_atr=yf.download(tickerSymbol, start=start_date_atr, end=end_date)
                            avg_tr=talib.ATR(df_atr['High'], df_atr['Low'], df_atr['Close'], timeperiod=14)
                            avg_tr=talib.ATR(df_atr['High'], df_atr['Low'], df_atr['Close'], timeperiod=14)
                            avg_tr=avg_tr.dropna()
                        additional.append(fplt.make_addplot(avg_tr,color='red', panel=count, ylabel="ATR"))
                        count=count+1
                    if i=='Normalized Average True Range':
                        start_date_natr=start_date - timedelta(days=12)
                        df_natr=yf.download(tickerSymbol, start=start_date_natr, end=end_date)
                        natr=talib.NATR(df_natr['High'], df_natr['Low'], df_natr['Close'], timeperiod=14)
                        natr=natr.dropna()
                        while len(natr)<len(df):
                            start_date_natr=start_date_natr - timedelta(days=1)
                            df_natr=yf.download(tickerSymbol, start=start_date_natr, end=end_date)
                            natr=talib.NATR(df_natr['High'], df_natr['Low'], df_natr['Close'], timeperiod=14)
                            natr=talib.NATR(df_natr['High'], df_natr['Low'], df_natr['Close'], timeperiod=14)
                            natr=natr.dropna()
                        additional.append(fplt.make_addplot(natr,color='red', panel=count, ylabel="NATR"))
                        count=count+1
            fig, ax = fplt.plot(
                    df,
                    title=f'{tickerSymbol}, {start_date} to {end_date}',
                    type=chart_type,
                    show_nontrading=show_nontrading_days,
                    volume=show_volume,
                    addplot=additional,
                    style=chart_style,
                    figsize=(15,10),
                
                    # Need this setting for Streamlit, see source code (line 778) here:
                    # https://github.com/matplotlib/mplfinance/blob/master/src/mplfinance/plotting.py
                    returnfig=True
                )
            
            st.write('_________________')
            st.pyplot(fig)
if dashboard=='Backtesting':
    st.write(' ')
    st.write(' ')
    st.write(' ')	 
    backtest, blank, s1,s2,s3,s4, s5 =st.columns([2, 0.5, 0.75, 0.75, 0.75, 0.75, 0.75])
    with backtest:
        backtest_head='''
            <link href='https://fonts.googleapis.com/css?family=Montserrat' rel="stylesheet">
            <style>
            .backtesthead {
                font-family:Montserrat;
                font-size:40px;
                font-weight:1000;
                font-style: bold;
                float:left;
                margin-left:60px;
                margin-top: 20px;
                margin-right: 20px;
                        }
            #backtesticon {
                margin-top: 20px;
             }
            </style>

            <body>
            <center><p1 class='backtesthead'> Backtesting</p1></center>
            <svg xmlns="http://www.w3.org/2000/svg" width="45" height="45" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" id='backtesticon'>
            <path d="M1 11a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1v-3zm5-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V7zm5-5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1V2z"/>
            </svg>
            </body>
                        '''
        st.markdown(backtest_head, unsafe_allow_html=True)
    with blank:
        st.write(' ')
    with s1:
        ticker=st.text_input("Stock ticker", value="AAPL")
    with s2:
        start=st.date_input("Start date", value="2018-01-31")
    with s3:
        end=st.date_input("End date", value=date.today())
    with s4:
        cash=st.text_input("Starting cash", value=10000)
    with s5:
        strategy=st.selectbox('Choose your strategy', options=['RSI', 'Volatility VIX', 'Golden Crossover', 'Bollinger Bands'])
    st.write(' ')
    st.write(' ')
    st.write(' ')
    while strategy=='RSI':
        backtestrsi(ticker=ticker, start=start, end=end, cash=cash)
    while strategy=='Volatility VIX':
        volatility(ticker=ticker, start=start, end=end, cash=cash)
    while strategy=='Golden Crossover':
        backtestgolden(ticker=ticker, start=start, end=end, cash=cash)
    while strategy=='Bollinger Bands':
        backtestbb(ticker=ticker, start=start, end=end, cash=cash)
if dashboard=='Portfolio Optimizer':
    st.write(' ')
    st.write(' ')
    st.write(' ')	
    #st.set_page_config(page_title = "Bohmian's Stock Portfolio Optimizer", layout = "wide")
    s = Screener()
    tickers_strings = ''
    count=0
    sectordict={}
    sectornames=['Individual Stocks', 'Technology', 'Utilities', 'Real Estate', 'Healthcare', 'Energy', 'Industrials', 'Materials', 'Communication Services', 'Financial Services', 'Consumer Defensive', 'Cryptocurrency']
    sectors=['ms_technology', 'ms_utilities', 'ms_real_estate', 'ms_healthcare', 'ms_energy', 'ms_industrials', 'ms_basic_materials', 'ms_communication_services','ms_financial_services','ms_consumer_defensive', 'all_cryptocurrencies_us',]
    portfolioinp=['Individual Stocks','ms_technology', 'ms_utilities', 'ms_real_estate', 'ms_healthcare', 'ms_energy', 'ms_industrials', 'ms_basic_materials', 'ms_communication_services','ms_financial_services','ms_consumer_defensive', 'all_cryptocurrencies_us']
    for i in range(len(sectornames)):
        sectordict[sectornames[i]]=portfolioinp[i]

    yf.pdr_override()
    def plot_cum_returns(data, title):    
        daily_cum_returns = 1 + data.dropna().pct_change()
        daily_cum_returns = daily_cum_returns.cumprod()*100
        fig = px.line(daily_cum_returns, title=title)
        return fig
        
    def plot_efficient_frontier_and_max_sharpe(mu, S): 
        # Optimize portfolio for max Sharpe ratio and plot it out with efficient frontier curve
        ef = EfficientFrontier(mu, S)
        fig, ax = plt.subplots(figsize=(6,4))
        ef_max_sharpe = copy.deepcopy(ef)
        plotting.plot_efficient_frontier(ef, ax=ax, show_assets=False)
        # Find the max sharpe portfolio
        ef_max_sharpe.max_sharpe(risk_free_rate=0.02)
        ret_tangent, std_tangent, _ = ef_max_sharpe.portfolio_performance()
        ax.scatter(std_tangent, ret_tangent, marker="*", s=100, c="r", label="Max Sharpe")
        # Generate random portfolios
        n_samples = 1000
        w = np.random.dirichlet(np.ones(ef.n_assets), n_samples)
        rets = w.dot(ef.expected_returns)
        stds = np.sqrt(np.diag(w @ ef.cov_matrix @ w.T))
        sharpes = rets / stds
        ax.scatter(stds, rets, marker=".", c=sharpes, cmap="viridis_r")
        # Output
        ax.legend()
        return fig


    st.header("Mean-variance Stock Portfolio Optimizer")

    col1, col2, col3 = st.columns(3)

    with col1:
        start_date = st.date_input("Start Date",datetime(2015, 1, 1))
        
    with col2:
        end_date = st.date_input("End Date") # it defaults to current date
    with col3:
        sectorinp=st.selectbox(label='Select a sector', options=sectornames, index=0)
    data = s.get_screeners(sectors,  count=15)
    for i in sectors:
        if i==sectordict[sectorinp]:
            df=pd.DataFrame(data[i]['quotes'])
            tickers=df['symbol']
            for j in tickers:
                if count!=0:
                    tickers_strings = tickers_strings+','+j
                else:
                    tickers_strings = tickers_strings+j
                count=count+1
        else:
            pass
    if sectorinp=='Individual Stocks':
        tickers_string = st.text_input('Enter all stock tickers to be included in portfolio separated by commas \
                                    WITHOUT spaces, e.g. "MA,FB,V,AMZN,JPM,BA"', '').upper()
    else:
        tickers_string = st.text_input('Enter all stock tickers to be included in portfolio separated by commas \
                                    WITHOUT spaces, e.g. "MA,FB,V,AMZN,JPM,BA"', value=tickers_strings).upper()
    tickers = tickers_string.split(',')
    try:
        # Get Stock Prices using pandas_datareader Library	
        stocks_df = pdr.get_data_yahoo(tickers, start = start_date, end = end_date)['Adj Close']
        sp500=pdr.get_data_yahoo('SPY', start = start_date, end = end_date)['Adj Close']
            # Plot Individual Stock Prices
        fig_price = px.line(stocks_df, title='')
            # Plot Individual Cumulative Returns
        fig_cum_returns = plot_cum_returns(stocks_df, '')
            # Calculatge and Plot Correlation Matrix between Stocks
        corr_df = stocks_df.corr().round(2)
        fig_corr = px.imshow(corr_df, text_auto=True)
            # Calculate expected returns and sample covariance matrix for portfolio optimization later
        mu = expected_returns.mean_historical_return(stocks_df)
        S = risk_models.sample_cov(stocks_df)
            
            # Plot efficient frontier curve
        fig = plot_efficient_frontier_and_max_sharpe(mu, S)
        fig_efficient_frontier = BytesIO()
        fig.savefig(fig_efficient_frontier, format="png")
            
            # Get optimized weights
        ef = EfficientFrontier(mu, S)
        ef.add_objective(objective_functions.L2_reg, gamma=0.1)
        ef.max_sharpe(risk_free_rate=0.02)
        weights = ef.clean_weights()
        expected_annual_return, annual_volatility, sharpe_ratio = ef.portfolio_performance()
        weights_df = pd.DataFrame.from_dict(weights, orient = 'index')
        weights_df.columns = ['weights']  
            # Calculate returns of portfolio with optimized weights
        stocks_df['Optimized Portfolio'] = 0
        for ticker, weight in weights.items():
                stocks_df['Optimized Portfolio'] += stocks_df[ticker]*weight
            
            # Plot Cumulative Returns of Optimized Portfolio
        fig_cum_returns_optimized = plot_cum_returns(stocks_df['Optimized Portfolio'], 'Cumulative Returns of Optimized Portfolio Starting with $100')
        latest_prices = get_latest_prices(stocks_df)
        da = DiscreteAllocation(weights, latest_prices, total_portfolio_value=100000)
        allocation, leftover = da.greedy_portfolio()
        print(allocation, leftover)
                # Display everything on Streamlit
        st.subheader("Your Portfolio Consists of: {} Stocks".format(tickers_string))
        col1,col2=st.columns([1.3,1])
        with col1:
            st.plotly_chart(fig_cum_returns_optimized, use_container_width=True)
        with col2:
            st.write('')	
            st.write('')	
            st.subheader('\tStock Prices')
            st.write(stocks_df)
        st.write('___________________________')
        col1,col2, stats=st.columns([0.5,1.3, 0.7])   
        with col1: 
            st.write('')
            st.write('')
            st.write('')
            st.subheader("Max Sharpe Portfolio Weights")
            st.dataframe(weights_df)
        with col2:
            st.write('')
            st.write('')
            stock_tickers=[]
            weightage=[]
            for i in weights:
                if weights[i]!=0:
                    stock_tickers.append(i)
                    weightage.append(weights[i])
            fig_pie = go.Figure(
                go.Pie(
                labels =stock_tickers,
                values = weightage,
                hoverinfo = "label+percent",
                textinfo = "value"
                ))
            holdings='''
            <style>
            .holding{
                float: center;
                font-weight: 600;
                font-size: 35px;
                font-family: arial;
            }
            </style>
            <body>
            <center><p1 class='holding'> Optimized Portfolio Holdings </p1></center>
            </body>
            '''
            st.markdown(holdings, unsafe_allow_html=True)
            st.plotly_chart(fig_pie, use_container_width=True)
        with stats:
            st.subheader('Expected annual return: {}%'.format((expected_annual_return*100).round(2)))
            st.write('___________')
            st.subheader('Annual volatility: {}%'.format((annual_volatility*100).round(2)))
            st.write('___________')
            st.subheader('Sharpe Ratio: {}'.format(sharpe_ratio.round(2)))
            st.write('___________')
            st.subheader('''Discrete allocation: 
            {}'''.format(allocation))
            st.write('___________')
            st.subheader("Funds remaining: ${:.2f}".format(leftover))
        st.write('___________________________')
        col1, col2=st.columns(2)
        with col1:
            st.subheader("Optimized Max Sharpe Portfolio Performance")
            st.image(fig_efficient_frontier)
        with col2:
            st.subheader("Correlation between stocks")
            st.plotly_chart(fig_corr, use_container_width=True) # fig_corr is not a plotly chart
        col1,col2=st.columns(2)
        with col1:
            st.subheader('Price of Individual Stocks')
            st.plotly_chart(fig_price, use_container_width=True)
        with col2:
            st.subheader('Cumulative Returns of Stocks Starting with $100')
            st.plotly_chart(fig_cum_returns, use_container_width=True)	
    except:
        st.write('Enter correct stock tickers to be included in portfolio separated\
        by commas WITHOUT spaces, e.g. "MA,FB,V,AMZN,JPM,BA"and hit Enter.')
if dashboard=='Twitter Analysis':
    st.write(' ')
    st.write(' ')
    st.write(' ')
    icon, dashboard, dashboard2=st.columns([1.0,0.7,0.7])
    tweepytxt='''
            <link href='https://fonts.googleapis.com/css?family=Montserrat' rel="stylesheet">
            <style>
            .tweepyhead {
                font-family:Montserrat;
                font-size:40px;
                font-weight:1000;
                font-style: bold;
                float:left;
                margin-left:60px;
                margin-top: 20px;
                margin-right: 20px;
                        }
            #twittericon {
                margin-top: 20px;
             }
            </style>

            <body>
            <center><p1 class='tweepyhead'> Twitter Analysis</p1></center>
            <svg xmlns="http://www.w3.org/2000/svg" width="55" height="55" fill="currentColor" class="bi bi-twitter" viewBox="0 0 16 16" id='twittericon'>
            <path d="M5.026 15c6.038 0 9.341-5.003 9.341-9.334 0-.14 0-.282-.006-.422A6.685 6.685 0 0 0 16 3.542a6.658 6.658 0 0 1-1.889.518 3.301 3.301 0 0 0 1.447-1.817 6.533 6.533 0 0 1-2.087.793A3.286 3.286 0 0 0 7.875 6.03a9.325 9.325 0 0 1-6.767-3.429 3.289 3.289 0 0 0 1.018 4.382A3.323 3.323 0 0 1 .64 6.575v.045a3.288 3.288 0 0 0 2.632 3.218 3.203 3.203 0 0 1-.865.115 3.23 3.23 0 0 1-.614-.057 3.283 3.283 0 0 0 3.067 2.277A6.588 6.588 0 0 1 .78 13.58a6.32 6.32 0 0 1-.78-.045A9.344 9.344 0 0 0 5.026 15z"/>
            </svg>
            </body>
                        '''
    with icon:
        st.markdown(tweepytxt, unsafe_allow_html=True)
    with dashboard:
        option=st.selectbox(label='Select dashboard', options=['Twitter', 'Stocktwits'])
    #client = tweepy.Client(bearer_token='AAAAAAAAAAAAAAAAAAAAAJ1meQEAAAAAMiu8HiZQp72esUQWDn6R2MwUHcg%3DUYSBVvz3CAGC0tNgCdq53QWQlnRyWaVx6kj8AR1671E8VIG0dX')
    auth = tweepy.OAuthHandler('GoYcKuWHMDxBInUcaml8XrPrc', 'u9MEKZtN6MqZ0Q2Aq3r6Cg4RcMadTbBCVcIkwAdOJUytvK7tEY')
    auth.set_access_token('1542799215813971974-5s4w5KiEI9dzcFdcSim0mDwMoTy6VF', '8c6Z5aBYl2uWLhcT150Pu9iOyhcagKddZbnFCdgRpRsgS')
    api = tweepy.API(auth)
    st.write(' ')
    st.write(' ')
    st.write(' ')
    if option == 'Twitter':
        with dashboard2:
            usernames=[]
            account=st.selectbox(label='Select a twitter account', options=['Traderstewie', 'The_chart_life', 'Tmltrader', 'Benzinga', 'Breakoutstocks', 'Stephanie_link', 'SunriseTrader'])
            usernames.append(account)
        for username in usernames:
            user = api.get_user(screen_name=username)
            tweets = api.user_timeline(screen_name=username)
            st.header(username)
            st.image(user.profile_image_url)
            for tweet in tweets:
                if '$' in tweet.text:
                    words = tweet.text.split(' ')
                    for word in words:
                        if word.startswith('$') and word[1:].isalpha():
                            symbol = word[1:]
                            st.subheader(symbol)
                            st.write(tweet.text)
                            st.image(f"https://finviz.com/chart.ashx?t={symbol}")
                            st.write('___________________________')
    elif option=='Stocktwits':
        with dashboard2:
            symbol = st.text_input("Symbol", value='AAPL', max_chars=5)
        r = requests.get(f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json")
        data=r.json()
        for message in data['messages']:
            st.image(message['user']['avatar_url'], width=40)
            st.subheader(message['user']['username'])
            st.write(message['created_at'])
            st.subheader(message['body'])
            st.write('_______________________')
