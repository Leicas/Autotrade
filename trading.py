from private import Privateinfos
import json
import cherrypy
class Trading:
    def __init__(self, pair, pairs):
        self.name = pair
        self.privateinfos = Privateinfos()
        self.pairs = pairs
        self.orders = {}
        with open("conf.json","r") as data_file:
            self.conf = json.load(data_file)
    def update(self):
        #print("trading update")
        try:
            if self.pairs[self.name].value != -1:
                self.do_trade()
            self.privateinfos.update()
            self.updateorder()
        except Exception as e:
            cherrypy.log("pb update trading!", traceback=True)
    def reloadconf(self):
        """ 
        rechargement de la conf
        """
        with open("conf.json","w") as outfile:
            json.dump(self.conf, outfile, indent=4)
        with open("conf.json","r") as data_file:
            self.conf = json.load(data_file)
    def save_order(self, order):
        """ 
        enregistrement des achats
        """
        with open("data.json","r") as data_file:
            data = json.load(data_file)
        data['orders'].append(order['txid'][0])
        with open("data.json","w") as outfile:
            json.dump(data, outfile, indent=4)
    def CondiAchat(self):
        retour = 0
        if self.conf['enabled'] == 1:
            if self.conf['cagnote'] >= self.conf['mini']:
                mini = self.SmallestOrder()
                if mini != -1 and (mini == 0 or mini*0.98 >= (self.pairs[self.name].value)):
                    self.pairs[self.name].getlin(1800)
                    self.pairs[self.name].getlin(3600)
                    if self.pairs[self.name].coef[3600] <= self.pairs[self.name].coef[1800]:
                        if self.pairs[self.name].coef[1800] >= -0.2:
                            print(self.pairs[self.name].value)
                            print(mini*0.98)
                            retour = 1
        return retour
    def do_trade(self):
        """ Choix de l'action a mener
        """
        self.pairs[self.name].getlin(1800)
        self.pairs[self.name].getlin(3600)
        pente = self.pairs[self.name].coef[1800]
        print(pente)
        if pente >= 0.0:
            print("vente")
            if self.CondiVente() == 1:
                print("on vend")
                self.VenteProfit()
        else:
            print("achat")
            if self.CondiAchat() == 1:
                prix = str(self.pairs[self.name].value)
                vol = str(self.conf['mini'] / float(prix))
                neworder = self.privateinfos.achat(prix, vol)
                self.conf['cagnote'] = self.conf['cagnote'] - self.conf['mini']
                self.save_order(neworder)
                print("achete" + vol + " a " + prix)
                #self.conf['enabled'] = 0
                self.reloadconf()
    def vente_order(self, txid):
        prix = str(self.pairs[self.name].value)
        vol = self.orders[txid]['vol']
        neworder = self.privateinfos.vente(prix, vol)
        self.save_vente(neworder,txid)
        print("vends" + vol + " a " + prix)
    def save_vente(self, order, txid):
        """ 
        enregistrement des ventes
        """
        with open("data.json","r") as data_file:
            data = json.load(data_file)
        data['ventes'].append(order['txid'][0])
        data['orders'].remove(txid)
        transaction = order['txid'][0] + " pour " + txid
        data['transactions'].append(transaction)
        with open("data.json","w") as outfile:
            json.dump(data, outfile, indent=4)
        del self.orders[txid]
    def VenteProfit(self):
        with open("data.json","r") as data_file:
            data = json.load(data_file)
        if data['orders']:
            for txid in data['orders']:
                if txid in self.orders:
                    if (float(self.pairs[self.name].value) * float(self.orders[txid]['vol'])-self.orders[txid]['cout'])*0.9984 >= self.orders[txid]['cout']*0.01:
                        self.vente_order(txid)
    def CondiVente(self):
        retour = 0
        if self.conf['enabled'] == 1:
            if self.pairs[self.name].coef[1800] <= self.pairs[self.name].coef[3600]:
                if self.pairs[self.name].coef[1800] <= 0.2:
                    #en debut d inflexion
                    retour = 1
        return retour
    def SmallestOrder(self):
        retour = 0
        with open("data.json","r") as data_file:
            data = json.load(data_file)
        if data['orders']:
            for txid in data['orders']:
                if txid in self.orders:
                    if (retour >= float(self.orders[txid]['descr']['price'])) or (retour == 0):
                        #print(self.orders[txid]['descr']['price'])
                        retour = float(self.orders[txid]['descr']['price'])
                else:
                    retour = -1
        return retour
    def updateorder(self):
        """
        On met a jour les achats sauf si ferme
        """
        with open("data.json","r") as data_file:
            data = json.load(data_file)
        for txid in data['orders']:
            if (not txid in self.orders) or  self.orders[txid]['status'] != "closed":
                self.orders[txid] = self.privateinfos.getorderinfo(txid)
                self.orders[txid]['cout'] = round(float(self.orders[txid]['price'])*float(self.orders[txid]['vol'])*1.0016,2)
            self.orders[txid]['value'] = round((float(self.pairs[self.name].value) * float(self.orders[txid]['vol'])-self.orders[txid]['cout'])*0.9984,2)
    def graph(self):
        return {self.privateinfos.eqgraph("history"),self.privateinfos.eqgraph("eqhistory")}
    def assets(self):
        return self.privateinfos.assets()
    def infos(self):
        retour = self.conf
        return retour