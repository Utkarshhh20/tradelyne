import backtrader as bt
import datetime as dt
import math
from numpy import size
import streamlit as st
import pandas as pd
class RSIStrategy(bt.Strategy):
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat, txt))

    def __init__(self):
        #Keep a reference to the "close" line in the data[0] dataseries
        self.date=self.datas[0].datetime.date(0)
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        self.order=None

    def notify_order(self,order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED: {}'.format(order.executed.price))
            elif order.issell():
                self.log('SELL EXECUTED: {}'.format(order.executed.price))
            self.bar_executed=len(self)
        self.order=None
    def next(self):
        global x
        global RSI
        global RS
        global total
        global amount
        global trades
        trades=[]
        up,down,total=0,0,0
        # Simply log the closing price of the series of the reference
        '''self.log('Close, {0:8.2f}' .format(self.dataclose[0]))
        self.log('Open, {0:8.2f}' .format(self.dataopen[0]))'''

        if not self.position:
            y=self.dataopen[0]
            x=self.dataclose[0]
            for i in range(0,-14,-1):
                if self.dataclose[i]>self.dataclose[i-1]:
                    total=total+self.dataclose[i]-self.dataclose[i-1]
                    up=up+(self.dataclose[i]-self.dataclose[i-1])/14
                
                elif self.dataclose[i]<self.dataclose[i-1]:
                    total=total+self.dataclose[i-1]-self.dataclose[i]
                    down=down+(self.dataclose[i-1]-self.dataclose[i])/14
            RS = up / down
            RSI= 100- (100/(1+RS))
            if RSI<=30:
                amount_to_invest=(0.95 * self.broker.cash)
                self.size=math.floor(amount_to_invest/self.data.close)
                amount=self.size
                x=self.dataclose[0]
                #BUY, BUY, BUY!!! (with all possible default parameters)
                self.log('BUY EXECUTED: %.2f' % self.dataclose[0])
                trades.append(self.dataclose[0])
                self.order=self.buy(size=self.size)
            
        else:
                #if self.dataclose[0] > self.dataclose[-1]:
                for i in range(0,-14,-1):
                    if self.dataclose[i]>self.dataclose[i-1]:
                        total=total+self.dataclose[i]-self.dataclose[i-1]
                        up=up+(self.dataclose[i]-self.dataclose[i-1])/14
                    
                    elif self.dataclose[i]<self.dataclose[i-1]:
                        total=total+self.dataclose[i-1]-self.dataclose[i]
                        down=down+(self.dataclose[i-1]-self.dataclose[i])/14
                RS = up / down
                RSI= 100- (100/(1+RS))
                if RSI>=70 and self.dataclose[0]>x:
                    #if self.dataclose[0]>x:
                            self.log('SELL EXECUTED: %.2f' % self.dataclose[0])
                            trades.append(self.dataclose[0])
                            self.order=self.sell(size=amount)
                            #x=st.write(f"SELL EXECUTED FOR {self.dataclose[0]} ON {self.datas[0].datetime.date(0)}")