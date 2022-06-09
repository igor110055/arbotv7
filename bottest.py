from datetime import datetime
from bot2 import Botmaker, constructor, Main_prog

tick = ['XBT/USDT']
c = constructor()
b = Botmaker(tick, 0.01, 10000)
bl = b.generate_bot_list()
# m = Main_prog(bl)
m = Main_prog(None, 'csv/bots.csv')
m.run()
bot = m.botlist[0]
while True:
    print('NEW LOOP')
    print(datetime.now())
    bot.run()
    print('***---***\n')

