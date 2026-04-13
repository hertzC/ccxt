# -*- coding: utf-8 -*-

from ccxt.async_support.base.exchange import Exchange
from ccxt.abstract.ltp import ImplicitAPI
import hashlib
from ccxt.base.types import Any, Balances, Currencies, Int, Market, Num, Str
from typing import List
from ccxt.base.errors import ExchangeError
from ccxt.base.errors import AuthenticationError


class ltp(Exchange, ImplicitAPI):

    def describe(self) -> dict[str, Any]:
        return self.deep_extend(super(ltp, self).describe(), {
            'id': 'ltp',
            'name': 'Liquidity Tech Platform',
            'countries': [],
            'rateLimit': 200,
            'certified': False,
            'pro': True,
            'has': {
                'CORS': False,
                'spot': False,
                'margin': False,
                'swap': False,
                'future': False,
                'option': False,
                'fetchBalance': True,
                'fetchCurrencies': True,
                'fetchDeposits': True,
                'fetchMarkets': 'emulated',
                'fetchWithdrawals': True,
                'fetchTransfers': True,
                'fetchTicker': False,
                'fetchOHLCV': False,
                'fetchOrderBook': False,
                'fetchTrades': False,
                'createOrder': False,
                'cancelOrder': False,
                'fetchOrders': False,
                'fetchOpenOrders': False,
                'fetchClosedOrders': False,
            },
            'urls': {
                'api': {
                    'rest': 'https://api.liquiditytech.com',
                },
                'www': 'https://www.liquiditytech.com',
                'doc': [],
            },
            'api': {
                'private': {
                    'get': {
                        'api/v1/tradeAccount/list': 1,
                        'api/v1/asset/getAccountCurrencyInfo': 1,
                        'api/v1/trading/account': 1,
                        'api/v1/asset/currencies': 1,
                        'api/v1/deposit/address': 1,
                        'api/v1/deposit/list': 1,
                        'api/v1/userWithdrawRecord/list': 1,
                        'api/v1/transfer/list': 1,
                    },
                },
            },
            'requiredCredentials': {
                'apiKey': True,
                'secret': True,
            },
            'options': {
                'defaultType': 'funding',
            },
            'successCodes': {200, 200000},
        })

    async def fetch_markets(self, params: dict = {}) -> list[Market]:
        return []

    async def fetch_balance(self, params: dict = {}) -> Balances:
        balance_type: str = self.safe_string(
            params, 'type',
            self.safe_string(self.options, 'defaultType', 'funding'),
        )
        params = self.omit(params, 'type')
        if balance_type == 'trading':
            return await self.fetch_trading_balance(params)
        return await self.fetch_funding_balance(params)

    async def fetch_funding_balance(self, params: dict = {}) -> Balances:
        response: dict = await self.privateGetApiV1AssetGetaccountcurrencyinfo(params)
        return self.parse_funding_balance(response)

    def parse_funding_balance(self, response: dict) -> Balances:
        data: list = self.safe_list(response, 'data', [])
        result: dict = {
            'info': response,
            'timestamp': None,
            'datetime': None,
        }
        for acct in data:
            assets: list = self.safe_list(acct, 'assetInfo', [])
            for asset in assets:
                currency_id: str | None = self.safe_string(asset, 'currency')
                if currency_id is None:
                    continue
                code: str = self.safe_currency_code(currency_id)
                account: dict = self.account()
                account['total'] = self.safe_string(asset, 'totalBalance')
                account['free'] = self.safe_string(asset, 'available')
                account['used'] = self.safe_string(asset, 'frozen')
                result[code] = account
        return self.safe_balance(result)

    async def fetch_trading_balance(self, params: dict = {}) -> Balances:
        response: dict = await self.privateGetApiV1TradingAccount(params)
        return self.parse_trading_balance(response)

    def parse_trading_balance(self, response: dict) -> Balances:
        data: list = self.safe_list(response, 'data', [])
        result: dict = {
            'info': response,
            'timestamp': None,
            'datetime': None,
        }
        total_equity: float = 0.0
        total_available: float = 0.0
        total_frozen: float = 0.0
        for venue in data:
            equity: float = self.safe_float(venue, 'equity', 0)
            if equity == 0:
                continue
            total_equity += equity
            total_available += self.safe_float(venue, 'availableMargin', 0)
            total_frozen += self.safe_float(venue, 'frozenMargin', 0)
        if total_equity > 0:
            account: dict = self.account()
            account['total'] = str(total_equity)
            account['free'] = str(total_available)
            account['used'] = str(total_frozen)
            result['USDT'] = account
        return self.safe_balance(result)

    async def fetch_currencies(self, params: dict = {}) -> Currencies:
        response: dict = await self.privateGetApiV1AssetCurrencies(params)
        data: list = self.safe_list(response, 'data', [])
        result: dict = {}
        for entry in data:
            currency_id: str = self.safe_string(entry, 'currency')
            code: str = self.safe_currency_code(currency_id)
            result[code] = {
                'id': currency_id,
                'code': code,
                'name': self.safe_string(entry, 'currencyName', code),
                'active': True,
                'deposit': None,
                'withdraw': None,
                'fee': None,
                'precision': None,
                'limits': {
                    'amount': {'min': None, 'max': None},
                    'withdraw': {'min': None, 'max': None},
                },
                'info': entry,
            }
        return result

    async def fetch_deposits(self, code: Str = None, since: Int = None, limit: Int = None, params: dict = {}) -> list[dict]:
        response: dict = await self.privateGetApiV1DepositList(params)
        return self.safe_list(response, 'data', [])

    async def fetch_withdrawals(self, code: Str = None, since: Int = None, limit: Int = None, params: dict = {}) -> list[dict]:
        response: dict = await self.privateGetApiV1UserwithdrawrecordList(params)
        return self.safe_list(response, 'data', [])

    async def fetch_transfers(self, code: Str = None, since: Int = None, limit: Int = None, params: dict = {}) -> list[dict]:
        response: dict = await self.privateGetApiV1TransferList(params)
        return self.safe_list(response, 'data', [])

    def sign(self, path: str, api: str = 'public', method: str = 'GET', params: dict = {}, headers: dict | None = None, body: str | None = None) -> dict[str, Any]:
        url: str = self.urls['api']['rest'] + '/' + path
        nonce: str = str(int(self.seconds()))
        sorted_params: list[tuple] = sorted(params.items())
        query_string: str = '&'.join(str(k) + '=' + str(v) for k, v in sorted_params)
        sign_string: str = query_string + '&' + nonce
        signature: str = self.hmac(
            self.encode(sign_string),
            self.encode(self.secret),
            hashlib.sha256,
        )
        headers = {
            'X-MBX-APIKEY': self.apiKey,
            'signature': signature,
            'nonce': nonce,
            'Content-Type': 'application/json',
        }
        if method == 'GET' and params:
            url += '?' + self.urlencode(params)
        elif method == 'POST' and params:
            body = self.json(params)
        return {'url': url, 'method': method, 'body': body, 'headers': headers}

    def handle_errors(self, code: int, reason: str, url: str, method: str, headers: dict, body: str, response: dict | None, requestHeaders: dict, requestBody: str | None) -> None:
        if response is None:
            return None
        response_code: int | None = self.safe_integer(response, 'code')
        if response_code is None:
            return None
        success_codes: set[int] = self.safe_value(self.options, 'successCodes', {200, 200000})
        if response_code in success_codes:
            return None
        message: str = self.safe_string(response, 'message', '')
        feedback: str = self.id + ' ' + body
        if 'no permission' in message.lower() or 'invalid' in message.lower():
            raise AuthenticationError(feedback)
        raise ExchangeError(feedback)
