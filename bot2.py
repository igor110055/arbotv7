from datetime import datetime
from numpy import linspace
import pandas as pd
import names as nm
from wonderwords import RandomWord
from cstr import Bin_man, Krak_man
import threading
from os import path
import os



r = RandomWord()


class constructor():
    def __init__(self) -> None:
        pass
    def transpose_ticker(self, ticker):
        '''transposes the ticker from kraken format to binance fomat'''

        if ticker == 'XBT/USDT':
            ticker = 'BTCUSDT'
            return ticker
        else :              
            s = ticker
            s = s.replace('/','')
            return s


class Botmaker():
    
    '''creates bots with specified params
    ticker list : list of tiokers in format 'COIN/USDT'
    crit_spread :  the crit spread applied to bot
    capital : the capital applied to bot'''
    
    
    def __init__(self, ticker_list, crit_spread, capital, load=False) -> None:
        self.load=load
        self.botlist = False
        self.ticker_list = ticker_list
        self.crit_spread = crit_spread
        self.capital = capital

    def generate_name(self):
        fname = nm.get_first_name(gender="female")
        adj = r.word(include_parts_of_speech=["adjectives"])
        name = f"{fname}_the_{adj}"
        return name

    def generate_bot_list(self):
        ls = []
        for ticker in self.ticker_list:
            ls.append(Bot(ticker, self.generate_name(), self.capital, self.crit_spread))
        return ls

    def store_bot_list(self, botlist):
        pass

class Bot():
    '''Creates the bot, the args are passed by botmanager, 
    trade manager, hedge manger and wallet needs to be initalised in matrix main loop'''
    def __init__(self, ticker, name, capital, crit_spread) :
        self.ticker = ticker
        self.name = name
        self.capital = float(capital)
        self.crit_spread = float(crit_spread)
        self.trade_manager = False
        self.hedge_manager = False
        self.wallet = False
        self.transac_hist = False
        self.last_trade = False
        self.decimals = False
        self.orders = {'buy':False, 'sell':False}
        self.restrict = {'buy':False, 'sell':False}

    def get_delta (self):
        """Returns a dict {buy, sell}
        if spread is < threshold, returns False"""
        hfirst_sell = self.hedge_manager.books[self.ticker]['sell'].iloc(0)['price']
        hfirst_buy = self.hedge_manager.books[self.ticker]['buy'].iloc(0)['price']
        # last_price = float(self.hedge_manager.get_trades()['price'].iloc[-1])
        first_sell = self.trade_manager.books[self.ticker]['sell'].iloc(0)['price']
        first_buy = self.trade_manager.books[self.ticker]['buy'].iloc(0)['price']
        buy_delta = hfirst_sell-first_buy
        sell_delta = first_sell-hfirst_buy
        buy_spread = buy_delta/first_sell*100
        sell_spread = sell_delta/first_buy*100
        if buy_spread < self.threshold:
            buy_spread = False
        if sell_spread < self.threshold:
            sell_spread = False
        return {'buy':buy_spread, 'sell':sell_spread}

    def init_wallet(self):
        '''calculate the crypto amount, makes the csv file for the wallet, returnd the DF'''
        if path.exists(f'csv/wallet_{self.name}.csv'):
            print(f'{self.name}wallet found')
            wallet = pd.read_csv(f'csv/wallet_{self.name}.csv', index_col=False)
            self.wallet=wallet
            print(wallet)
        else:
            crypto_amount = (self.capital/4)/self.trade_manager.books[self.ticker]['sell'].iloc[0]['price']
            fiat_amount = self.capital/4
            df = pd.DataFrame({'date':datetime.now(),
                f'{self.trade_manager.name}_crypto':crypto_amount,
                f'{self.trade_manager.name}_fiat':fiat_amount,
                f'{self.hedge_manager.name}_crypto':crypto_amount, 
                f'{self.hedge_manager.name}_fiat':fiat_amount}, index=[0])
            df.to_csv(f'csv/wallet_{self.name}.csv', index=False)
            self.wallet = df

    def get_decimals(self, num):
        '''to see how many decimals to adjust the trade amount for being first'''
        string = str(num)
        dec = len(string.split(".")[1])
        print(dec)
        diff = '0.'
        for n in range(dec):
            if n == dec-1:
                diff += "1"
            else:
                diff += "0"
        print(f'diff is {diff}')
        self.decimals = float(diff)
    
    def init_transac_hist(self):
        '''creates or loads the DF'''
        if path.exists('csv/trade_hist_{}.csv'.format(self.name)):
            print(f'{self.name}trade_hist found')
            t_hist = pd.read_csv('csv/trade_hist_{}.csv'.format(self.name), index_col=False)
        else :
            print(f'{self.name}creating trade hist')
            t_hist = pd.DataFrame(columns=['date', 'exchange', 'side', 'price','qtt', 'value', 'fee'])
            t_hist.to_csv('csv/trade_hist_{}.csv'.format(self.name), index=False)
        self.transac_hist = t_hist
        return t_hist

    def set_order(self, side, target='fiat', multiplicator=0.2, fake=False):
        ''''Sets the order according to the config of the bot, returns a dict {price, qtt, value}
        target valid params are 'crypto' or 'fiat', how the profit is made
        fake to get the price to restrict'''

        if side == 'buy':
            if not self.restrict['buy']:
                price = self.trade_manager.books[self.ticker][side] + self.decimals
            else:
                return False
        elif side == 'sell':
            if not self.restrict['sell']:
                price = self.trade_manager.books[self.ticker][side] - self.decimals
            else : 
                return False
        if target =='fiat':
            value = self.wallet[f'{self.trade_manager.name}_fiat'].iloc[-1]*multiplicator
            qtt = value/price
        elif target =='crypto':
            qtt = self.wallet[f'{self.trade_manager.name}_crypto'].iloc[-1]*multiplicator
            value = qtt*price
        order = {'price':price, 'qtt':qtt, 'value':value}
        if not fake:
            self.orders[side] = order
        return order

    def check_if_order_is_first(self, order):
        '''returns bool if order is or not longer at the top'''
        first = self.trade_manager.books[self.ticker][order['side'].iloc[0]['price']]
        if order['side'] == 'buy':
            price = first+self.decimals
        elif order['side'] == 'sell':
            price = first-self.decimals
        if price == order['price']:
            return True
        else:
            print('Not first')
            return False

    def execute_order(self, order):
        '''checks if the order got filled
        returns a dict with the amount liquidated or False, updates order'''
        #check if filled
        last_trades = self.get_last_trades()
        if isinstance(last_trades, pd.DataFrame):
            df = last_trades
            if order['side']=='buy':
                df = df[df['price']<=order['price']]
                print('some got filled')
            elif order['side']=='sell':
                df = df[df['price']>=order['price']]
                print('some got filled')
            if df['qtt'].sum()>=order['qtt']:
                print('ORDER FULLY FILLED')
                self.orders[order['side']] = False
                return order
            else :
                order['qtt'] = df['qtt'].sum()
                order['value'] == df['qtt'].sum()*order['price']
                self.orders[order['side']]['qtt'] -= df['qtt'].sum()
                self.orders[order['side']]['value'] == self.orders['side']['qtt']*self.orders[order['side']['price']]
                return order
        else :
            return False
            
    def hedge_market(self, exec_order):
        qtt = exec_order['qtt']
        if exec_order['side'] == 'buy':
            side = 'sell'
        elif exec_order['side'] == 'sell':
            side = 'buy'
        rest = qtt
        ob = self.hedge_manager.books[c.transpose_ticker(self.ticker)][side]
        lsprice = []
        lsqtt = []
        n = 0
        while rest > 0:
            if ob.iloc[n]['qtt'] >= rest:
                lsprice.append(ob.iloc[n]['price'])
                lsqtt.append(rest)
                rest = 0
            else :
                lsprice.append(ob.iloc[n]['price'])
                lsqtt.append(ob.iloc[n]['qtt'])
                rest -= ob.iloc[n]['qtt']
                n+=1

        df = pd.DataFrame({'price':lsprice, 'qtt':lsqtt})
        df['value'] = df['price']*df['qtt']
        avg = df['value'].sum()/df['qtt'].sum()
        exec = {'price':avg, 'qtt':df['qtt'].sum(), 'value':df['value'].sum()}
        return exec

    def get_last_trades(self):
        if not self.last_trade:
            last_trades= self.trade_manager.trade_hist[self.ticker]
            self.last_trade = self.trade_manager.trade_hist[self.ticker].iloc[-1]
            return last_trades
        if self.last_trade.equals(self.trade_manager.trade_hist[self.ticker].iloc[-1]):
            return False
        else:
            last_trades = self.trade_manager[self.trade_manager.trade_hist[self.ticker]['unix']>self.last_trade['unix']]
            self.last_trade = self.trade_manager.trade_hist[self.ticker].iloc[-1]
            return last_trades

    def restrict(self, margin=1.1):
        if bool(self.orders):
            available_amounts = {
                'fiat':self.wallet[f'{self.hedge_manager.name}_fiat'].iloc[-1],
                'crypto':self.wallet[f'{self.hedge_manager.name}_crypto'].iloc[-1]
            }
            for side, order in self.orders.items():
                if side == 'buy':
                    qtt = order['qtt']
                    if available_amounts['crypto'] < qtt*margin:
                        print('NOT ENOUGH TO HEDGE')
                        self.restrict={'buy':True}
                    else : 
                        self.restrict={'buy':False}
                elif side == 'sell':
                    value = order['value']
                    if available_amounts['fiat'] < qtt*margin:
                        print('NOT ENOUGH TO HEDGE')
                        self.restrict={'sell':True}
                    else : 
                        self.restrict={'sell':False}

    def run(self):
        
        def loop(side):
            if isinstance(self.orders[side], dict):
                exec = self.execute_order(self.orders[side])
                if isinstance(exec, dict):
                    self.hedge_market(exec)
            


ticker_list = ['XBT/USDT', 'ETH/USDT', 'DOT/USDT', 'LTC/USDT', 'BCH/USDT', 'ADA/USDT', 'EOS/USDT', 'LINK/USDT']
bm = Botmaker(ticker_list, 0.1, 20000)
bl = bm.generate_bot_list()
for bot in bl :
    # print(f'Hello, I am {bot.name}, i am trading the {bot.ticker} pair, capital {bot.capital}, crit spread {bot.crit_spread}'
    pass

class Main_prog():
    '''for test pupposes
    load from file : put path if load'''
    def __init__(self, botlist, load_from_file=False):
        if not load_from_file:
            self.raw_botlist = botlist
            self.botlist = self.get_botlist()
            self.ticker_list = self.get_tickerlist()

        else:
            self.botlist = []
            df = pd.read_csv(load_from_file, index_col=False)
            for n in range(len(df)):
                self.botlist.append(Bot(df.iloc[n]['ticker'], df.iloc[n]['name'], 1, df.iloc[n]['crit_spread']))
            self.ticker_list=df['ticker'].drop_duplicates().to_list()
        self.new_trades = {}
        self.obs = {}
        self.managers = {}

    def load_from_file(self):
        '''reads the bots.csv file and generates the botlist'''
        pass

    def get_tickerlist(self):
        ls = []
        for bot in self.botlist:
            if bot.ticker not in ls:
                ls.append(bot.ticker)
        return ls

    def get_botlist(self):
        if any(isinstance(i, list) for i in self.raw_botlist):
            print('nest detected')
            res = [item for sublist in self.raw_botlist for item in sublist]
            return res
        else:
            return self.botlist

    def run(self):

        #Start managers
        self.managers['trade']=Krak_man(self.ticker_list)
        self.managers['hedge']=Bin_man(self.ticker_list)
        self.managers['hedge'].ticker_list = self.managers['hedge'].get_ticker(self.ticker_list)
        for ticker in self.managers['hedge'].ticker_list:
            tbin = threading.Thread(target=self.managers['hedge'].loop_ob, args = [ticker]) #VOIR POUR FAIR UN FOR LOOP AVEC TICKERLIST
            tbin.start()
        tkrak = threading.Thread(target=self.managers['trade'].gather_data, args = [self.ticker_list])
        tkrak.start()
        for pair in self.managers['hedge'].ticker_list:
            while pair not in self.managers['hedge'].books:
                pass
                # print(f'{pair} not in books yet')
        for pair in self.managers['trade'].ticker_list:
            while pair not in self.managers['trade'].books:
                pass
                # print(f'{pair} not in books yet')
        print('all books gathered')
        #initialise bots
        for bot in self.botlist:
            bot.trade_manager = self.managers['trade']
            bot.hedge_manager = self.managers['hedge']
            bot.init_wallet()
            bot.get_decimals(bot.trade_manager.books[bot.ticker]['buy'].iloc[0]['price'])
            bot.init_transac_hist()
        #store botlist if not present
        if os.path.isfile('csv/bots.csv'):
            print('botlist detected')
        else :
            df = pd.DataFrame(columns=['name', 'ticker', 'crit_spread', 'decimals'])
            n=0
            for bot in self.botlist:
                df.loc[n] = [bot.name, bot.ticker, bot.crit_spread, bot.decimals]
                n+=1
            df.to_csv('csv/bots.csv', index=False)
                # print(df)





#TEST RUNS UNCOMMENT FOR TEST

# ticker_list = ['XBT/USDT', 'ETH/USDT', 'DOT/USDT', 'LTC/USDT', 'BCH/USDT', 'ADA/USDT', 'EOS/USDT', 'LINK/USDT']
# bm1 = Botmaker(ticker_list, 0.1, 20000)
# bl = bm.generate_bot_list()
# bm2 = Botmaker(ticker_list, 0.5, 10000)
# bl2 = bm2.generate_bot_list()
c = constructor()
m = Main_prog(None, load_from_file='csv/bots.csv')
m.run()
while True:
    print(m.managers['trade'].trade_hist)
print(m.botlist)
for bot in m.botlist:
    print(bot.name)
    print(bot.wallet)

