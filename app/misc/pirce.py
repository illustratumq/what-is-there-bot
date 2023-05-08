

class List:
    minimal_price = 30
    maximal_price = 15000


class PriceList:

    @staticmethod
    def current() -> List:
        return List()

    @staticmethod
    def calculate_commission(price: int) -> int:
        if price <= 200:
            return 5
        else:
            return int(round(price * 0.05))
