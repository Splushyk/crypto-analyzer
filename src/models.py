class Cryptocurrency:
    """Представляет криптовалюту с основными рыночными данными."""

    def __init__(self, name: str, symbol: str, price: float, change_24h: float, volume: float, market_cap: float):
        self.name = name
        self.symbol = symbol.upper()
        self.price = price or 0.0
        self.change_24h = change_24h or 0.0
        self.volume = volume or 0.0
        self.market_cap = market_cap or 0.0

    def __str__(self):
        return f"{self.name} ({self.symbol}): ${self.price:,.2f} ({self.change_24h:+.2f}%)"

    def __lt__(self, other):
        if not isinstance(other, Cryptocurrency):
            return NotImplemented
        return self.change_24h < other.change_24h
