"""Доменные API-исключения приложения crypto."""

from rest_framework import status
from rest_framework.exceptions import APIException


class SymbolNotFoundOnExchangeError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Symbol not found on exchange."
    default_code = "symbol_not_found"


class WatchlistDuplicateError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Coin already in your watchlist."
    default_code = "watchlist_duplicate"


class WatchlistItemNotFoundError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Coin is not in your watchlist."
    default_code = "watchlist_item_not_found"


class NoDataForAnalysisError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "No data available for analysis."
    default_code = "no_data_for_analysis"


class CoinNotInLatestSnapshotError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Coin not present in the latest market snapshot."
    default_code = "coin_not_in_snapshot"


class InsufficientFundsError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Insufficient balance for this purchase."
    default_code = "insufficient_funds"
