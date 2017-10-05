import krakenex
import time
import math
import pandas as pd
import matplotlib
import matplotlib.finance as mpf
import matplotlib.dates as mdates
import datetime
import base64
matplotlib.use('Agg')
import seaborn as sns
import matplotlib.pyplot as plt
from cStringIO import StringIO

class Privateinfos:
    def __init__(self):
        self.api = krakenex.API()
        self.api.load_key('kraken.key')
        self.hdf = pd.HDFStore('private.h5')
        self.cc = 0
        self.lt = 0
        if not('/history' in self.hdf.keys()):
            print('Create file')
            response = self.api.query_private('Balance')
            self.cc+=1
            if "result" in response:
                dft=pd.DataFrame(response["result"],index=[time.time()], dtype='float')
                self.hdf.put('history', dft, format='table', data_columns=True)
        if not('/eqhistory' in self.hdf.keys()):
            print('Create equivalent balance file')
            response = self.api.query_private('TradeBalance')
            self.cc+=1
            if "result" in response:
                dft=pd.DataFrame(response["result"],index=[time.time()], dtype='float')
                self.hdf.put('eqhistory', dft, format='table', data_columns=True)
    def CC(self):
        now = time.time()
        diff = math.floor((now - self.lt)/3.0)
        if diff >= 1:
            self.lt = now
        self.cc = max(self.cc - diff, 0)
        return self.cc
    def CCcheck(self):
        """ 
        check if counter is ok then wait
        """
        while self.CC() >= 14:
            time.sleep(1)
    def balance(self):
        if self.CC() < 14:
            response = self.api.query_private('Balance')
            self.cc+=1
            if "result" in response:
                dft=pd.DataFrame(response["result"],index=[time.time()], dtype='float')
                try:
                    self.hdf.append('history', dft, format='table', data_columns=True)
                except:
                    print("erreur ajout balance")
    def eqbalance(self):
        if self.CC() < 14:
            response = self.api.query_private('TradeBalance')
            self.cc+=1
            if "result" in response:
                dft=pd.DataFrame(response["result"],index=[time.time()], dtype='float')
                try:
                    self.hdf.append('eqhistory', dft, format='table', data_columns=True)
                    #print("valeurs historique ajoutees")
                except:
                    print("erreur ajout equivalente balance")
    def eqgraph(self, name='eqhistory'):
                data = self.hdf.select(name)#, where='index >='+str(now-since))
                sns.set()
                sns.set_style("whitegrid")
                sns.set_context("paper")
                data.index = pd.to_datetime(data.index,unit='s')
                if name == 'eqhistory':
                    ax = data[['e']].dropna().plot(figsize=(3.5,2.5))
                else:
                    ax = data.dropna().plot(figsize=(3.5,2.5))
                image = StringIO()
                plt.ticklabel_format(style='plain', axis='y',useOffset=False)
                plt.tight_layout()
                plt.savefig(image, format='png')
                fig = ax.get_figure()
                plt.close(fig)
                return base64.encodestring(image.getvalue())
    def assets(self):
        nrows = self.hdf.get_storer('history').nrows
        data = self.hdf.select('history', start=nrows-1,stop=nrows)
        return data
    def achat(self,prix,vol):
        """ 
        achat
        """
        neworder = self.api.query_private('AddOrder',{'pair' : 'XXBTZEUR', 'type' : 'buy', 'ordertype': 'limit', 'price' : prix, 'volume' : vol })['result']
        return neworder
    def vente(self,prix,vol):
        """
        vente
        """
        neworder = self.api.query_private('AddOrder',{'pair' : 'XXBTZEUR', 'type' : 'sell', 'ordertype': 'limit', 'price' : prix, 'volume' : vol })['result']
        return neworder
    def getorderinfo(self, txid):
        self.CCcheck()
        result = self.api.query_private('QueryOrders', {'txid' : txid})['result'][txid]
        self.cc +=1
        return result
    def update(self):
        if self.CC() < 14:
            print("call counter ok")
            self.balance()
            self.eqbalance()
        else:
            print("wait call counter")