from common import sh_log


class GridTest(object):
    def __init__(self, grids, start_rice, kls, sum_balance, ratio, side) -> None:
        super().__init__()
        self.grids = grids
        self.cur_rice = start_rice
        self.kls = kls
        self.cur_idx = -1
        self.sell_list = []
        self.buy_list = []
        self.fw = open('tmp\\grid.log', 'w')
        self.last_rice = -1
        self.sum_balance = sum_balance
        self.sell_all = 0
        self.buy_all = 0
        self.ratio = ratio
        self.side = side
        self.qty = self.calc_qty()
        self.fw.write(str(self.grids))

    def get_sum_rice_by_qty(self, qty):
        sum = 0
        for i in self.grids:
            if self.side == 'long':
                sum += qty * min(self.cur_rice, i[0])
            else:
                sum += qty * max(i[1], self.cur_rice)

        return sum

    def calc_qty(self):
        max_amount = 1000000
        l = 0
        r = max_amount
        max_qty = 1000
        while l <= r:
            mid = int((l + r) // 2)
            val = self.get_sum_rice_by_qty(max_qty / max_amount * mid)
            if val <= self.sum_balance:
                l = mid + 1
            else:
                r = mid - 1

        return max_qty / max_amount * r

    def do_once(self, end_rice, kl):
        end_idx = self.get_cur_grid_idx(end_rice)
        if self.cur_idx == end_idx:
            self.cur_rice = end_rice
            return

        if self.cur_idx < end_idx:
            _cur_idx = max(0, self.cur_idx)
            for i in range(_cur_idx, end_idx):
                _rice = self.grids[i][1]
                if _rice == self.last_rice:
                    continue

                self.last_rice = _rice
                self.sell_list.append(_rice)
                profit = self.qty * (self.grids[i][1] - self.grids[i][0])
                self.sell_all += profit
                self.fw.write(f'sell: profit:{profit} rice:{_rice} cur:{self.cur_rice}, end:{end_rice}, kl:{kl}\n')
        else:
            _cur_idx = min(len(self.grids) - 1, self.cur_idx)
            for i in range(_cur_idx, end_idx, -1):
                _rice = self.grids[i][0]
                if _rice == self.last_rice:
                    continue

                self.last_rice = _rice
                self.buy_list.append(_rice)
                profit = self.qty * (self.grids[i][1] - self.grids[i][0])
                self.buy_all += profit
                self.fw.write(f'buy: profit:{profit} rice:{_rice} cur:{self.cur_rice}, end:{end_rice}, kl:{kl}\n')

        self.cur_rice = end_rice
        self.cur_idx = end_idx

    def get_cur_grid_idx(self, rice):
        if rice < self.grids[0][0]:
            return -1

        for idx, grid in enumerate(self.grids):
            if rice < grid[1]:
                return idx
        else:
            return len(self.grids)

    def test(self):
        self.cur_idx = self.get_cur_grid_idx(self.cur_rice)

        for kl in self.kls:
            self.do_once(kl.min_rice, kl)
            self.do_once(kl.max_rice, kl)
            self.do_once(kl.end_rice, kl)

        # sh_log.sh_print('buy:', len(self.buy_list))
        # sh_log.sh_print('sell:', len(self.sell_list))
        # sh_log.sh_print('qty:', self.qty)
        # sh_log.sh_print('sell:', self.sell_all)
        # sh_log.sh_print('buy:', self.buy_all)
        return {
            'buy': len(self.buy_list),
            'sell': len(self.sell_list),
            'qty': self.qty,
            'sell_all': self.sell_all,
            'buy_all': self.buy_all,
            'ratio': self.ratio
        }