# -*- coding: utf-8 -*-
import requests, json, time, os, sys
import pyimgur
import numpy as np
import pandas as pd
import cherrypy
import matplotlib
import random
import string
import collections
from cStringIO import StringIO
matplotlib.use('Agg')
import seaborn as sns
import matplotlib.pyplot as plt
#os.chdir(sys.path[0])
from jinja2 import Environment, FileSystemLoader
envi = Environment(loader=FileSystemLoader('layout'))
import matplotlib.finance as mpf
import matplotlib.dates as mdates
import datetime
import base64
from sklearn import linear_model

def HumanTime(c):
    attrs = ['jours', 'heures', 'minutes', 'secondes']
    delta={}
    c = c*60
    delta['jours'] = c // 86400
    delta['heures'] = c // 3600 % 24
    delta['minutes'] = c // 60 % 60
    delta['secondes'] = c % 60
    retour = ""
    for attr in attrs:
        if delta[attr] > 1:
            retour+= "%d %s" % (delta[attr], attr)
        elif delta[attr] == 1:
            retour+= "%d %s" % (delta[attr], attr[:-1])
    return retour
envi.filters['human'] = HumanTime
@cherrypy.expose
class StringGeneratorWebService(object):

    @cherrypy.tools.accept(media='text/plain')
    def GET(self):
        return cherrypy.session['mystring']

    def POST(self, length=8):
        some_string = ''.join(random.sample(string.hexdigits, int(length)))
        cherrypy.session['mystring'] = some_string
        return some_string

    def PUT(self, another_string):
        cherrypy.session['mystring'] = another_string

    def DELETE(self):
        cherrypy.session.pop('mystring', None)

class StringGenerator(object):
    @cherrypy.expose
    def index(self):
        datas={}
        coefs={}
        valeurs={}
        for paire in catapaires:
            datas[paire] = catapaires[paire].allgraph()
            coefs[paire] = collections.OrderedDict(sorted(catapaires[paire].coef.items()))
            valeurs[paire] = catapaires[paire].value
        #btceur.allgraph()
        tmpl = envi.get_template('index.html')
        return tmpl.render(graphs=datas, coefs=coefs, valeurs=valeurs)
        #return open('index.html')

class Pair:
    def __init__(self, pair):
        self.name = pair
        self.hdf = pd.HDFStore(self.name+'.h5')
        self.coef={}
        self.value=1
        print(self.hdf.keys())
        if not('/history' in self.hdf.keys()):
            print('Create file')
            data = self.requesthistory()
            self.hdf.put('history', data[:-1], format='table', data_columns=True)
        self.checkhistory()
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
                print(reponsejson['result']['last'])
                stri = json.dumps(reponsejson['result'][self.name])
                data=pd.read_json(stri, orient='columns')
                data.columns = ["time", "open", "high", "low", "close", "vwap", "volume", "count"]
                data = data.set_index('time')
                try:
                    self.hdf.append('history', data[:-1], format='table', data_columns=True)
                except:
                    print("erreur")
                #data['time'] = pd.to_datetime(data['time'],unit='s')
                print(data[:-1].tail(1))
                self.value=data[:-1].tail(1)["close"].values[0]
        except requests.exceptions.RequestException as e:
            print e
    def graph(self, since=60):
                nrows = self.hdf.get_storer('history').nrows
                start = max(nrows-since,0)
                since = nrows-start
                data = self.hdf.select('history',start=start,stop=nrows)
                #data[['close']] = (data[['close']] - data[['close']].iloc[0]) / data[['close']].iloc[0]*100
                sns.set()
                sns.set_style("whitegrid")
                sns.set_context("paper")
                oldindex = data.index
                data.index = pd.to_datetime(data.index,unit='s')
                lin = self.getlin(since)
                data['ransac'] = pd.Series(oldindex*lin.coef_[0]+lin.intercept_, index=data.index)
                lin = self.getlin(since/2)
                data['ransac/2'] = pd.Series(oldindex*lin.coef_[0]+lin.intercept_, index=data.index)
                lin = self.getlin(since/6)
                data['ransac/6'] = pd.Series(oldindex*lin.coef_[0]+lin.intercept_, index=data.index)
                #fig, ax1 = plt.subplots()
                #sax1.plot(pd.to_datetime(lin['x'],unit='s'),lin['y'], color='cornflowerblue', linestyle='-', label='RANSAC regressor')
                ax = data[['high','low','close','ransac','ransac/2','ransac/6']].dropna().plot(figsize=(3.5,2.5))
                #fig = plt.figure()
                #plt.fill_between(data.index.tolist(),data['high'],data['low'])
                #plt.plot(data.index.tolist(),data['close'])
                image = StringIO()
                #plt.show()
                #plt.savefig('img/'+self.name+str(since)+'.png')
                plt.tight_layout()
                plt.savefig(image, format='png')
                fig = ax.get_figure()
                plt.close(fig)
                return base64.encodestring(image.getvalue())
    def getlin(self, since=60):
        nrows = self.hdf.get_storer('history').nrows
        start = max(nrows-since,0)
        data = self.hdf.select('history',start=start,stop=nrows)
        #print(data['close'].median)
        try:
            model = linear_model.RANSACRegressor()
            #data.index = pd.to_datetime(data.index,unit='s')
            model.fit(data.index.values.reshape(len(data.index.values), 1),data['close'].values)
            self.coef[since] = model.estimator_.coef_[0]*60*60/self.value*100.0
            return model.estimator_
        except:
            print("not ransac")
            model = linear_model.LinearRegression()
            model.fit(data.index.values.reshape(len(data.index.values), 1),data['close'].values)
            self.coef[since] = model.coef_[0]*60*60/self.value*100.0
            return model
        #self.coef[since] = model.estimator_.coef_[0]*60*60/self.value*100.0
        
        #return cataresult
    def allgraph(self):
        liste = []
        self.coef={}
        liste.append(self.graph(60))
        liste.append(self.graph(1440))
        liste.append(self.graph(44640))
        return liste

#listpaires=['XXBTZEUR','XETHZEUR']
catapaires={'XXBTZEUR':0,'XETHZEUR':0}
for paire in catapaires:
    catapaires[paire] = Pair(paire)

if __name__ == '__main__':
  for paire in catapaires:
    #catapaires[paire] = Pair(pair)
    cherrypy.process.plugins.BackgroundTask(15, catapaires[paire].getnew).start()
  webapp = StringGenerator()
  webapp.generator = StringGeneratorWebService()
  cherrypy.quickstart(webapp, '/', "app.conf")
