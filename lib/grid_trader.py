from genericpath import exists
from common.sh_log import sh_print
from binance import Client, ThreadedWebsocketManager, ThreadedDepthCacheManager
from common import utils
from common import const
from binance_f import RequestClient
from . import grid
from . import klines
from . import grid_test
import math
import time
import json
import os
import pickle


class GridTrader(object):
    def __init__(self, symbol, side=-1, start_price=-1, end_price=-1, grid_num=-1, max_quantity=-1, grid_type=-1, price_fix_type=-1) -> None:
        super().__init__()
        self.client = self.get_init_client()
        self.future = self.get_init_future()
        self.start_price = start_price
        self.end_price = end_price
        self.grid_num = grid_num
        self.max_quantity = max_quantity
        self.grid_type = grid_type
        self.symbol = symbol
        self.side = side
        self.price_fix_type = price_fix_type

        self.grids = []
        self.order_id_2_grids = {}  # type: dict[int, grid.Grid]

    def get_end_by_ratio(self, start, max_num, ratio):
        ratio += 1
        end = start
        for i in range(max_num):
            end *= ratio

        return end

    def get_end_equal_ratio(self):
        max_range = 100000
        l = 0
        r = max_range
        while l <= r:
            mid = int((l + r) // 2)
            val = self.get_end_by_ratio(self.start_price, self.grid_num, mid / max_range)
            if val <= self.end_price:
                l = mid + 1
            else:
                r = mid - 1

        return r / max_range

    def calc(self):
        grids = []
        if self.grid_type == const.GridType.EQUAL_RATIO:
            ratio = self.get_end_equal_ratio()
            price = self.start_price
            for i in range(self.grid_num):
                old_price = price
                price *= 1 + ratio
                grids.append((old_price, price))

        elif self.grid_type == const.GridType.EQUAL_DIFFERENCE:
            delta = (self.end_price - self.start_price) / self.grid_num
            price = self.start_price
            for i in range(self.grid_num):
                old_price = price
                price += delta
                grids.append(old_price, price)

        return grids

    def get_init_client(self):
        json_data = utils.get_binance_user_json()
        proxies = {
            'http': 'http://127.0.0.1:7890',
            'https': 'http://127.0.0.1:7890'
        }
        return Client(json_data['api_key'], json_data['secret_key'], {'proxies': proxies})

    def get_init_future(self):
        json_data = utils.get_binance_user_json()
        return RequestClient(api_key=json_data['api_key'], secret_key=json_data['secret_key'])

    def cancel_order(self, symbol, order_id):
        ret = self.client.cancel_order(symbol=symbol, orderId=order_id)
        self.print_order(ret)

    def print_order(self, order):
        print(
            f"symbol:{order['symbol']}\n"
            f"\torderId:{order['orderId']}\n"
            f"\tprice:{order['price']}\n"
            f"\torigQty:{order['origQty']}\n"
            f"\tside:{order['side']}\n"
        )

    def show_orders(self, symbol):
        orders = self.client.get_open_orders(symbol=symbol)
        for order in orders:
            self.print_order(order)

    def sell(self, symbol, price, quantity):
        order = self.client.create_order(
            symbol=symbol,
            side=Client.SIDE_SELL,
            type=Client.ORDER_TYPE_LIMIT,
            price=price,
            timeInForce=Client.TIME_IN_FORCE_GTC,
            quantity=quantity)

        # self.print_order(order)
        return order

    def buy(self, symbol, price, quantity):
        order = self.client.create_order(
            symbol=symbol,
            side=Client.SIDE_BUY,
            type=Client.ORDER_TYPE_LIMIT,
            price=price,
            timeInForce=Client.TIME_IN_FORCE_GTC,
            quantity=quantity)

        # self.print_order(order)
        return order


    def get_klines(self, symbol, interval, limit):
        _klines = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
        kls = []
        for _kline in _klines:
            kl = klines.KLines(*_kline)
            kls.append(kl)

        return kls

    def get_open_order(self, symbol):
        orders = self.client.get_open_orders(symbol=symbol)
        for order in orders:
            print(type(order))

    def _pre_run_sell(self):
        cur_price = self.get_cur_price(self.symbol)
        grids = []

        min_price = -1
        price_sections = self.calc()
        for i, (_start_price, _end_price) in enumerate(price_sections):
            if min_price == -1 and _end_price > cur_price:
                min_price = _end_price

            grids.append(grid.Grid(
                Client.SIDE_SELL,
                _start_price,
                _end_price
            ))

        avg_qty = self.max_quantity / self.grid_num
        ratio = self.get_end_equal_ratio()
        print(avg_qty, ratio)

        for _grid in grids:
            _price = max(min_price, _grid.up_price)
            _price = self.fix_price(_price)
            print(_price, avg_qty)
            _order = self.sell(self.symbol, _price, avg_qty)
            order_id = _order['orderId']
            self.order_id_2_grids[order_id] = _grid
            _grid.set_order_id(order_id)

    def fix_price(self, price):
        if self.price_fix_type == const.FixType.RESERVED_THREE:
            return '{:.3f}'.format(price)

    def get_symbol_info(self, symbol):
        ret = self.client.get_symbol_info(symbol)
        for filt in ret['filters']:
            print(filt)

    def print_dict(self, dic):
        for k, v in dic.items():
            print(k, v)

    def pre_run(self):
        if self.side == Client.SIDE_SELL:
            self._pre_run_sell()

        self.save()

    def get_cur_price(self, symbol):
        kls = self.get_klines(symbol, '5m', 1)
        return kls[0].end_rice

    def save(self):
        grids = [grid.to_save_dict() for grid in self.order_id_2_grids.values()]
        save_dict = {
            'symbol': self.symbol,
            'grids': grids,
        }

        with open(f'storage/{self.symbol}.json', 'w') as fw:
            json.dump(save_dict, fw)

    @classmethod
    def create_from_arg(cls, symbol, **kwargs):
        if cls.is_exist_storage(symbol):
            return None

        return cls(symbol, **kwargs)

    @staticmethod
    def is_exist_storage(symbol):
        return os.path.exists(f'storage/{symbol}.json')

    @classmethod
    def create_from_storage(cls, symbol):
        if not cls.is_exist_storage(symbol):
            return None

        with open(f'storage/{symbol}.json') as fr:
            json_data = json.load(fr)
            gt = cls(json_data['symbol'])
            grids = json_data['grids']
            for _grid_data in grids:
                gt.order_id_2_grids[_grid_data['cur_order_id']] = grid.Grid.create_from_dict(_grid_data)

            return gt

    def tick_once(self):
        pass

    def cancel_all(self, symbol):
        orders = self.client.get_open_orders(symbol=symbol)
        for order in orders:
            self.cancel_order(symbol, order['orderId'])

    def get_grid_profit(self, symbol):
        kls = self.get_klines(symbol, '1h', 10)
        count = 0
        sum = 0
        for kl in kls:
            diff = kl.max_rice - kl.min_rice
            ratio = diff / kl.min_rice
            ratio = abs(ratio)
            ratio *= 100
            sh_print(f'{ratio}%')
            sum += ratio * ratio
            count += 1

        sh_print('ret:', math.sqrt(sum / count))

    def lp_calc(self):
        ra = 0.00308
        rb = 1
        l = 651

        aa = l * math.sqrt(rb / ra)
        ab = l * math.sqrt(ra / rb)

        val = ra * aa + rb * ab
        sh_print(f'aa:{aa}, ab:{ab}, val:{val}')

    def run(self):
        while 1:
            self.tick_once()
            time.sleep(1)

    def _get_grid_test_klines(self, symbol, start_time_str, end_time_str):
        ts_start = int(time.mktime(time.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")))
        ts_start = int(ts_start // 3600 * 3600)
        ts_end = int(time.mktime(time.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")))
        kls = []

        while 1:
            _end = ts_start + 60 * 60
            hour_file_name = f'tmp\\.{symbol}.{ts_start}.{_end}.kls'
            hour_kls = []

            if os.path.exists(hour_file_name):
                sh_print('from local')
                with open(hour_file_name, 'rb') as fr:
                    data = pickle.load(fr)
                    for _data in data:
                        hour_kls.append(_data)
            else:
                sh_print('from remote')
                try:
                    rets = self.future.get_candlestick_data(symbol, '1m', ts_start * 1000, _end * 1000, 60)
                except Exception as e:
                    sh_print(e)
                    continue

                for i in rets:
                    hour_kls.append(klines.KLines.get_from_candle(i))

                with open(f'tmp\\.{symbol}.{ts_start}.{hour_kls[-1].end_time + 1}.kls', 'wb') as fw:
                    pickle.dump(hour_kls, fw)
                time.sleep(1)


            if _end >= ts_end:
                break

            if not hour_kls:
                break

            ts_start = _end
            kls.extend(hour_kls)

            sh_print(hour_kls[0].open_time, hour_kls[-1].end_time, ts_start)
            sh_print(time.localtime(ts_start))

        return kls

    def _load_kls(self, symbol, start_time_str, end_time_str):
        with open(self._get_file_name(symbol, start_time_str, end_time_str), 'rb') as fr:
            return pickle.load(fr)

    def _get_file_name(self, symbol, start_time_str, end_time_str):
        return (f'tmp\\.kls.{symbol}.{start_time_str}.{end_time_str}')\
            .replace(' ', '_')\
            .replace(':', '-')

    def grid_test(self, symbol, time_start_str, time_end_str, side):
        kls = self._get_grid_test_klines(symbol, time_start_str, time_end_str)

        rets = []
        for grid_num in range(10, 200):
            ret = self._grid_test(grid_num, kls, side)
            rets.append((ret, grid_num))

        rets.sort(key=lambda x: x[0]['buy_all'])
        for ret, grid_num in rets:
            #sh_print(, grid_num, ret['ratio'], ret['buy'])
            sh_print(f"profit:{ret['buy_all']}, grid_num:{grid_num}, ratio:{ret['ratio'] * 100:.2f}%, buy:{ret['buy']}, qty:{ret['qty']}")

    def grid_test_one(self, symbol, time_start_str, time_end_str, side):
        kls = self._get_grid_test_klines(symbol, time_start_str, time_end_str)

        self._grid_test(37, kls, side)

    def _grid_test(self, grid_num, kls, side):
        from common import sh_log
        self.grid_num = grid_num

        # sh_log.sh_print(len(kls))
        start_rice = kls[0].open_rice
        grids = self.calc()
        ratio = self.get_end_equal_ratio()
        gt = grid_test.GridTest(grids, start_rice, kls, 284, ratio, side)
        return gt.test()

    def test(self):
        #self.get_open_order('CAKEUSDT')
        self.pre_run()
