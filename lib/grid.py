class Grid(object):
    """
    """
    def __init__(self, cur_order_side, down_price, up_price, cur_order_id=0) -> None:
        super().__init__()
        self.cur_order_side = cur_order_side
        self.down_price = down_price
        self.up_price = up_price
        self.cur_order_id = cur_order_id

    def __repr__(self):
        return f'cur_order_side:{self.cur_order_side}\n'\
            f'\t down_price:{self.down_price}\n'\
            f'\t up_price:{self.up_price}\n'\
            f'\t cur_order_id:{self.cur_order_id}\n'

    def set_order_id(self, order_id):
        self.cur_order_id = order_id

    def to_save_dict(self):
        return {
            'cur_order_side': self.cur_order_side,
            'down_price': self.down_price,
            'up_price': self.up_price,
            'cur_order_id': self.cur_order_id,
        }

    @classmethod
    def create_from_dict(cls, dic):
        return cls(
            dic['cur_order_side'],
            dic['down_price'],
            dic['up_price'],
            dic['cur_order_id'],
        )