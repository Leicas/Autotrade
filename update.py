# -*- coding: utf-8 -*-
import requests, json, time, os, sys
import pyimgur
#import numpy as np
#import pandas as pd
import cherrypy

import random
import string
import collections


#os.chdir(sys.path[0])
from jinja2 import Environment, FileSystemLoader
envi = Environment(loader=FileSystemLoader('layout'))

from pair import Pair
from trading import Trading

def HumanTime(c):
    attrs = ['jours', 'heures', 'minutes', 'secondes']
    delta={}
    c = c
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
def datetimeformat(value, format='%H:%M / %d-%m-%Y'):
    return time.strftime(format, time.localtime(value))
envi.filters['datetimeformat'] = datetimeformat
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
        balanceeq = trading.graph()
        assets=trading.assets()
        infos=trading.infos()
        tmpl = envi.get_template('index.html')
        orders = trading.orders
        return tmpl.render(graphs=datas, coefs=coefs, valeurs=valeurs, balanceeq=balanceeq, assets=assets, infos=infos, orders=orders)
        #return open('index.html')



#listpaires=['XXBTZEUR','XETHZEUR']
catapaires={'XXBTZEUR':0,'XETHZEUR':0}
for paire in catapaires:
    catapaires[paire] = Pair(paire)
trading = Trading('XXBTZEUR',catapaires)
if __name__ == '__main__':
  for paire in catapaires:
    cherrypy.process.plugins.BackgroundTask(15, catapaires[paire].update).start()
  cherrypy.process.plugins.BackgroundTask(15, trading.update).start()
  webapp = StringGenerator()
  webapp.generator = StringGeneratorWebService()
  cherrypy.quickstart(webapp, '/', "app.conf")
