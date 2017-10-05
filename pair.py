import pandas as pd
import numpy as np
import requests, json, time, os, sys
import matplotlib
import matplotlib.finance as mpf
import matplotlib.dates as mdates
import datetime
import base64
from sklearn import linear_model
matplotlib.use('Agg')
import seaborn as sns
import matplotlib.pyplot as plt
from cStringIO import StringIO
import cherrypy

class Pair:
    def __init__(self, pair):
        self.name = pair
        self.hdf = pd.HDFStore(self.name+'.h5')
        self.coef={}
        self.value=-1
        print(self.hdf.keys())
        if not('/history' in self.hdf.keys()):
            print('Create file')
            data = self.requesthistory()
            self.hdf.put('history', data[:-1], format='table', data_columns=True)
        self.checkhistory()
        self.getnew()
    def checkhistory(self):
        now = time.time()
        test = self.hdf.select('history', where='index <='+str(now-60*60*24*7))
        if(test.empty):
            print("oups semaine")
            self.addhistory(15)
        test = self.hdf.select('history', where='index <='+str(now-60*60*24*31))
        if(test.empty):
            print("oups mois")
            self.addhistory(60)
        test = self.hdf.select('history', where='index <='+str(now-60*60*24*360))
        if(test.empty):
            print("oups annee")
            self.addhistory(240)
            self.addhistory(1440)
    def addhistory(self, interval):
        now = time.time()
        data = self.requesthistory(interval)
        #print(data[data.index <now-60*60*24*31])
        try:
            self.hdf.append('history', data[:-1], format='table', data_columns=True)
        except:
            print("erreur")
    def requesthistory(self, interval=1):
        try:
                response = requests.get('https://api.kraken.com/0/public/OHLC?pair='+self.name+'&interval='+str(interval))
                response.raise_for_status()
                reponsejson=response.json()
                if "result" in reponsejson:
                    stri = json.dumps(reponsejson['result'][self.name])
                    data=pd.read_json(stri, orient='columns')
                    data.columns = ["time", "open", "high", "low", "close", "vwap", "volume", "count"]
                    data = data.set_index('time')
                    return data
        except requests.exceptions.RequestException as e:
                print "Bug recuperation historique"
                print e
    def getnew(self):
        nrows = self.hdf.get_storer('history').nrows
        df = self.hdf.select('history',start=nrows-1,stop=nrows)
        #print(df.index.tolist())
        last = df.index.tolist()[0]
        try:
            response = requests.get('https://api.kraken.com/0/public/OHLC?pair='+self.name+'&interval=1'+'&since='+str(last))
            response.raise_for_status()
            reponsejson=response.json()
            if ("result" in reponsejson) and (reponsejson['result']['last'] != last):
                #print(reponsejson['result']['last'])
                stri = json.dumps(reponsejson['result'][self.name])
                data=pd.read_json(stri, orient='columns')
                data.columns = ["time", "open", "high", "low", "close", "vwap", "volume", "count"]
                data = data.set_index('time')
                data[['open','close','high','low','close','vwap','volume']] = data[['open','close','high','low','close','vwap','volume']].astype(float)
                try:
                    print("essai ajout")
                    self.hdf.append('history', data[:-1], format='table', data_columns=True)
                    print("ajout fini")
                except Exception as e:
                    cherrypy.log("ajout rate!", traceback=True)
                #data['time'] = pd.to_datetime(data['time'],unit='s')
                #print(data[:-1].tail(1))
                self.value=data[:-1].tail(1)["close"].values[0]
        except requests.exceptions.RequestException as e:
            print "bug nouvelles valeurs"
            print e
    def graph(self, since=3600):
                now = time.time()
                data = self.hdf.select('history', where='index >='+str(now-since))
                sns.set()
                sns.set_style("whitegrid")
                sns.set_context("paper")
                oldindex = data.index
                data.index = pd.to_datetime(data.index,unit='s')
                lin = self.getlin(since)
                data['ransac'] = pd.Series(oldindex*lin.coef_[0]+lin.intercept_, index=data.index)
                lin = self.getlin(since/2)
                data['ransac/2'] = pd.Series(oldindex*lin.coef_[0]+lin.intercept_, index=data.index)
                ax = data[['high','low','close','ransac','ransac/2']].dropna().plot(figsize=(3.5,2.5))
                image = StringIO()
                plt.tight_layout()
                plt.savefig(image, format='png')
                fig = ax.get_figure()
                plt.close(fig)
                return base64.encodestring(image.getvalue())
    def getlin(self, since=3600):
        now = time.time()
        data = self.hdf.select('history', where='index >='+str(now-since))
        data.index = pd.to_datetime(data.index,unit='s')
        data = data.groupby(level=0).first().resample('min').pad()
        data.index = data.index.astype(np.int64) // 10**9
        try:
            model = linear_model.RANSACRegressor()
            model.fit(data.index.values.reshape(len(data.index.values), 1),data['close'].values)
            self.coef[since] = model.estimator_.coef_[0]*60*60/self.value*100.0
            return model.estimator_
        except:
            print("not ransac")
            model = linear_model.LinearRegression()
            model.fit(data.index.values.reshape(len(data.index.values), 1),data['close'].values)
            self.coef[since] = model.coef_[0]*60*60/self.value*100.0
            return model
    def allgraph(self):
        liste = []
        self.coef={}
        liste.append(self.graph(3600))
        liste.append(self.graph(86400))
        liste.append(self.graph(2628000))
        liste.append(self.graph(31536000))
        return liste
    def update(self):
        try:
            self.getnew()
        except:
            cherrypy.log("kaboom!", traceback=True)
            print("erreur boucle data")