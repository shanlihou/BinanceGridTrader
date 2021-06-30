# coding:utf-8
from lib import grid_trader
from common import const
from binance import Client
import sys


def main():
    gt = grid_trader.GridTrader.create_from_arg(
        'THETAUSDT',
        side=Client.SIDE_SELL,
        start_price=6,
        end_price=9,
        grid_num=40,
        max_quantity=7.68,
        grid_type=const.GridType.EQUAL_RATIO,
        price_fix_type=const.FixType.RESERVED_THREE
        )

    if len(sys.argv) >= 2:
        if sys.argv[1] == 'test':
            gt.test()
        elif sys.argv[1] == 'cancel':
            gt.cancel_order('CAKEUSDT', sys.argv[2])
        elif sys.argv[1] == 'show':
            gt.show_orders(sys.argv[2])
        elif sys.argv[1] == 'price':
            print(gt.get_cur_price(sys.argv[2]))
        elif sys.argv[1] == 'info':
            print(gt.get_symbol_info(sys.argv[2]))
        elif sys.argv[1] == 'cancelall':
            gt.cancel_all(sys.argv[2])
        elif sys.argv[1] == 'profit':
            gt.get_grid_profit(sys.argv[2])
        elif sys.argv[1] == 'calc':
            rets = gt.calc()
            for ret in rets:
                print(ret)
            ratio = gt.get_end_equal_ratio()
            print(f'ratio:{ratio}')
        elif sys.argv[1] == 'lp':
            gt.lp_calc()
        elif sys.argv[1] == 'gridtest':
            gt.grid_test(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
        elif sys.argv[1] == 'gridtestone':
            gt.grid_test_one(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])

if __name__ == '__main__':
    main()
