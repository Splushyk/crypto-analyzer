import pytest

from src.models import Cryptocurrency
from src.parsers import GeckoParser, CMCParser


@pytest.mark.parametrize("parser_class, data_fixture", [
    (GeckoParser, "gecko_raw_data"),
    (CMCParser, "cmc_raw_data"),
], ids=["Gecko", "CMC"])
def test_parsers_work_correctly(parser_class, data_fixture, request, sample_coin):
    raw_data = request.getfixturevalue(data_fixture)
    result = parser_class().parse(raw_data)

    assert len(result) == 1
    assert isinstance(result[0], Cryptocurrency)
    assert result[0].name == sample_coin.name
    assert result[0].symbol == sample_coin.symbol
    assert result[0].price == sample_coin.price
    assert result[0].change_24h == sample_coin.change_24h
    assert result[0].volume == sample_coin.volume
    assert result[0].market_cap == sample_coin.market_cap


@pytest.mark.parametrize("parser_class", [GeckoParser, CMCParser])
def test_parsers_empty_data(parser_class):
    result = parser_class().parse([])
    assert result == []
