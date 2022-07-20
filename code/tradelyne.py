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
import plotly.graph_objs as go
from rsi import RSIStrategy
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup as bs
from string import Template
from datetime import date, timedelta
st.set_page_config(page_title='Tradelyne', layout="wide",initial_sidebar_state='collapsed')
today=date.today()
oneyr= today - timedelta(days=365)
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
def backtestrsi():
    global strategy
    s1,s2,s3,s4=st.columns(4)
    with s1:
        ticker=st.text_input("Stock ticker", value="AAPL")
    with s2:
        start=st.text_input("Start date", value="2018-01-31")
    with s3:
        end=st.text_input("End date", value=date.today())
    with s4:
        cash=st.text_input("Starting cash", value=10000)
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
    graph, info=st.columns([2,1])
    print(stratdd[0].analyzers.dd.get_analysis())
    with graph:
        st.pyplot(figure)
    with info:
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
            st.plotly_chart(fig, width=5)
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
            st.image(fig)
            st.plotly_chart(fig)
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


page_bg_img = '''
<style>
body {
background-image: url('https://cdn.myportfolio.com/fd40c2a8-1f6f-47d7-8997-48ba5415a69c/6c46ac13-6a18-427a-9baa-01ad3b53ac45_rw_600.png?h=21b14417887f0576feb32fcbfd191788');
background-size: cover;
}
</style>
<body>
</body>
'''
st.markdown(page_bg_img, unsafe_allow_html=True)
menu_data = [
    {'icon': "bi bi-window", 'label':"Screener"},
    {'icon': "bi bi-clipboard-data", 'label':"Fundamental analysis"},
    {'icon': "bi bi-binoculars", 'label':"Technical Indicators"},
    {'icon': "bi bi-skip-backward", 'label':"Backtesting"},
    {'icon': "bi bi-pie-chart", 'label':"Portfolio Optimizer"},
    {'icon': "bi bi-telephone", 'label':"Contact us"},
]
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
#selected=option_menu(
#    menu_title=None,
#    options=[1,2,3],
#    icons=['stocks', 'laptop', 'plane'],
#    orientation='horizontal',
#    styles={
#            "container": {"padding": "0!important", "background-color": "#fafafa"},
#            "icon": {"color": "orange", "font-size": "25px"}, 
#            "nav-link": {"font-size": "25px", "text-align": "left", "margin":"0px", "--hover-color": "#eee"},
#            "nav-link-selected": {"background-color": "green"},
#        }
#)'''
if dashboard=='Tradelyne':
    logo='''
        <style>
        .logo{
            width: 600px;
            margin-top:-210px;
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
        margin-left: 40px;
        }
        </style>
        <body>
        <img src="https://cdn.myportfolio.com/fd40c2a8-1f6f-47d7-8997-48ba5415a69c/5422f547-b577-4c88-8d2d-be32f80ddb6e_rw_1200.png?h=d5f92fc4f63b8cace8a88e175fba4c09" alt="House" class='taimg'></img>
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
        margin-left: 40px;
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

elif dashboard=='Screener':
    screen, start, end, stock=st.columns([1,0.7,0.7,0.7])
    screener='''
    <link href='https://fonts.googleapis.com/css?family=Montserrat' rel="stylesheet">
    <style>
    .screener {
        font-family:Montserrat;
        font-size:40px;
        font-weight:1000;
        font-style: bold;
        float:left;
        margin-left:80px;
        margin-top: 35px;
    }
    </style>

    <body>
    <p1 class='screener'>SCREENER</p1>
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
        
            matplotlib.use('Agg')
            plt.show(block=False)
            def get_historical_data(symbol, start_date = None):
                df = pdr.get_data_yahoo(symbol, start=start_date, end=datetime.datetime.now())
                df = df.rename(columns = {'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Adj Close': 'adj close', 'Volume': 'volume'})
                for i in df.columns:
                    df[i] = df[i].astype(float)
                df.index = pd.to_datetime(df.index)
                if start_date:
                    df = df[df.index >= start_date]
                return df
        
            settingsoption, chart=st.columns([1,3])
            with settingsoption:
                st.markdown('---')

                st.subheader('Settings')
                st.caption('Adjust charts settings and then press apply')

                with st.form('settings_form'):
                    #show_data = st.checkbox('Show data table', True)

                    show_nontrading_days = st.checkbox('Show non-trading days', False)

                    # https://github.com/matplotlib/mplfinance/blob/master/examples/styles.ipynb
                    chart_styles = [
                        'default', 'binance', 'blueskies', 'brasil', 
                        'charles', 'checkers', 'classic', 'yahoo',
                        'mike', 'nightclouds', 'sas', 'starsandstripes'
                    ]
                    chart_style = st.selectbox('Chart style', options=chart_styles, index=chart_styles.index('yahoo'))
                    chart_types = [
                        'candle', 'ohlc', 'line', 'renko', 'pnf'
                    ]
                    chart_type = st.selectbox('Chart type', options=chart_types, index=chart_types.index('candle'))

                    mav1 = st.number_input('MAV 1', min_value=3, max_value=30, value=3, step=1)
                    mav2 = st.number_input('MAV 2', min_value=3, max_value=30, value=6, step=1)
                    mav3 = st.number_input('MAV 3', min_value=3, max_value=30, value=9, step=1)

                    st.form_submit_button('Apply')

                data = get_historical_data(tickerSymbol, str(start_date))

                fig, ax = fplt.plot(
                    data,
                    title=f'{tickerSymbol}, {start_date} to {end_date}',
                    type=chart_type,
                    show_nontrading=show_nontrading_days,
                    mav=(int(mav1),int(mav2),int(mav3)),
                    volume=True,

                    style=chart_style,
                    figsize=(15,10),
                
                    # Need this setting for Streamlit, see source code (line 778) here:
                    # https://github.com/matplotlib/mplfinance/blob/master/src/mplfinance/plotting.py
                    returnfig=True
                )
                with chart:
                    st.write('_________________')
                    st.pyplot(fig)
            fundamentals, data_show=st.columns([0.7,1])
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
                        <center><p1 class='fundamenthead'> &nbsp $fundamentheader 's Fundamental Data  &nbsp</p1></center>
                        </body>
                        '''
                compfundheader = Template(fundament_header).safe_substitute(fundamentheader=tickerSymbol)
                st.markdown(compfundheader, unsafe_allow_html=True)
                # Set up scraper
                url = ("https://finviz.com/quote.ashx?t=" + tickerSymbol.lower())
                req = Request(url=url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0'})
                webpage = urlopen(req)
                html = bs(webpage, "html.parser")
                fundament=get_fundamentals()
                st.dataframe(fundament)
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

if dashboard=='Backtesting':
    strategy='RSI'
    while strategy=='RSI':
        backtestrsi()
