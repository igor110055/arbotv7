from datetime import datetime
import pandas as pd
import names as nm
from wonderwords import RandomWord
from cstr import Bin_man, Krak_man
import threading
from os import path
import os



r = RandomWord()
class Botmaker():
    
    '''creates bots with specified params
    ticker list : list of tiokers in format 'COIN/USDT'
    crit_spread :  the crit spread applied to bot
    capital : the capital applied to bot'''
    
    
    def __init__(self, ticker_list, crit_spread, capital) -> None:
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

    def get_delta (self):
        """Returns a dict {buy, sell}
        if spread is < threshold, returns False"""
        hfirst_sell =float(hedge_ob['sell'].iloc[0]['price'])
        hfirst_buy = float(hedge_ob['buy'].iloc[0]['price'])
        # last_price = float(self.hedge_manager.get_trades()['price'].iloc[-1])
        first_sell = float(trade_ob['sell'].iloc[0]['price'])
        first_buy = float(trade_ob['buy'].iloc[0]['price'])
        buy_delta = round(hfirst_sell-first_buy,6)
        sell_delta = round(first_sell-hfirst_buy,6)
        buy_spread = round(buy_delta/first_sell*100, 3)
        sell_spread = round(sell_delta/first_buy*100, 3)
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

            




ticker_list = ['XBT/USDT', 'ETH/USDT', 'DOT/USDT', 'LTC/USDT', 'BCH/USDT', 'ADA/USDT', 'EOS/USDT', 'LINK/USDT']
bm = Botmaker(ticker_list, 0.1, 20000)
bl = bm.generate_bot_list()
for bot in bl :
    # print(f'Hello, I am {bot.name}, i am trading the {bot.ticker} pair, capital {bot.capital}, crit spread {bot.crit_spread}'
    pass

class Main_prog():
    '''for test pupposes'''
    def __init__(self, botlist, load_from_file=False):
        self.raw_botlist = botlist
        self.botlist = self.get_botlist()
        self.ticker_list = self.get_tickerlist()
        self.new_trades = {}
        self.obs = {}
        self.managers = {}       

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
        for bot in self.botlist:
            bot.trade_manager = self.managers['trade']
            bot.hedge_manager = self.managers['hedge']
            bot.init_wallet()
            # bot.init_transac_hist()
            print(f'{bot.name} got its mnanagers')


ticker_list = ['XBT/USDT', 'ETH/USDT', 'DOT/USDT', 'LTC/USDT', 'BCH/USDT', 'ADA/USDT', 'EOS/USDT', 'LINK/USDT']
bm1 = Botmaker(ticker_list, 0.1, 20000)
bl = bm.generate_bot_list()
bm2 = Botmaker(ticker_list, 0.5, 10000)
bl2 = bm2.generate_bot_list()


m = Main_prog([bl, bl2])


m.run()
# print(m.managers['trade'].books)
# for bot in m.botlist:
#     m.run()







# # demarrer la collecte de data
# # print(self.managers['hedge'].ticker_list)
# # input()
# for ticker in self.managers['hedge'].ticker_list:
#     tbin = threading.Thread(target=self.managers['hedge'].loop_ob, args = [ticker]) #VOIR POUR FAIR UN FOR LOOP AVEC TICKERLIST
#     tbin.start()
# tkrak = threading.Thread(target=self.managers['trade'].gather_data, args = [self.tickerlist])
# tkrak.start()
# print('attributin managers to bots')
# for bot in self.botlist:
#     bot.trade_manager = self.managers['trade']
#     bot.hedge_manager = self.managers['hedge']
#     bot.init_wallet()
#     bot.init_transac_hist()
#     print(f'{bot.name} got its mnanagers')