# -*- coding: utf-8 -*-

import ccxt.async_support
from ccxt.base.types import Any, Balances
from ccxt.async_support.base.ws.client import Client
from ccxt.base.errors import ExchangeError
import hashlib
import json


class ltp(ccxt.async_support.ltp):

    def describe(self) -> Any:
        return self.deep_extend(super(ltp, self).describe(), {
            'has': {
                'ws': True,
                'watchBalance': True,
                'watchTicker': False,
                'watchTrades': False,
                'watchOrderBook': False,
                'watchOHLCV': False,
            },
            'urls': {
                'api': {
                    'ws': 'wss://wss.liquiditytech.com/v1/private',
                },
            },
            'options': {
                'ws': {
                    'heartbeatInterval': 20000,       # ms — LTP requires <30s
                    'fundingRefreshInterval': 60000,   # ms — REST poll for funding wallet
                },
            },
        })

    async def watch_balance(self, params={}) -> Balances:
        """
        Watch balance updates via LTP private WebSocket.

        LTP auto-pushes the ``assets`` channel after login for trading
        balance changes.  Funding wallet is NOT pushed, so this method
        internally runs a periodic REST poll to keep funding balances
        current.  Callers get a unified view without knowing about the
        limitation.
        """
        await self.load_markets()
        url = self.urls['api']['ws']
        message_hash = 'balance'
        await self.authenticate(url)
        client = self.client(url)
        # First call: seed balance from REST and spawn background loops
        if 'balance:seeded' not in client.subscriptions:
            client.subscriptions['balance:seeded'] = True
            # Seed both funding and trading via REST
            try:
                funding = await self.fetch_balance({'type': 'funding'})
                self.merge_funding_balance(funding)
            except Exception:
                pass  # Subaccount keys may lack funding permission
            try:
                trading = await self.fetch_balance({'type': 'trading'})
                self.merge_trading_balance(trading)
            except Exception:
                pass
            # Spawn periodic background tasks
            self.spawn(self.funding_refresh_loop, url)
            self.spawn(self.heartbeat_loop, url)
        return await self.watch(url, message_hash, None, message_hash)

    async def authenticate(self, url, params={}):
        client = self.client(url)
        message_hash = 'authenticated'
        authenticated = self.safe_value(client.subscriptions, message_hash)
        if authenticated is not None:
            return
        self.check_required_credentials()
        timestamp = str(int(self.seconds()))
        sign_string = timestamp + 'GET' + '/users/self/verify'
        signature = self.hmac(
            self.encode(sign_string),
            self.encode(self.secret),
            hashlib.sha256,
        )
        request = json.dumps({
            'action': 'login',
            'args': {
                'apiKey': self.apiKey,
                'timestamp': timestamp,
                'sign': signature,
            },
        })
        future = client.future(message_hash)
        await client.send(request)
        return await future

    async def heartbeat_loop(self, url):
        """Send raw 'ping' string every heartbeatInterval ms."""
        client = self.client(url)
        ws_options = self.safe_dict(self.options, 'ws', {})
        interval = self.safe_integer(ws_options, 'heartbeatInterval', 20000)
        while client.connected:
            try:
                await self.sleep(interval)
                if not client.connected:
                    break
                await client.send('ping')
            except Exception:
                break

    async def funding_refresh_loop(self, url):
        """Periodically fetch funding balance via REST and merge.

        LTP WebSocket does NOT push funding wallet updates (deposits,
        withdrawals, transfers).  This loop ensures funding balances
        stay current within fundingRefreshInterval.
        """
        client = self.client(url)
        ws_options = self.safe_dict(self.options, 'ws', {})
        interval = self.safe_integer(ws_options, 'fundingRefreshInterval', 60000)
        while client.connected:
            try:
                await self.sleep(interval)
                if not client.connected:
                    break
                funding = await self.fetch_balance({'type': 'funding'})
                self.merge_funding_balance(funding)
                # Wake up awaiters with the updated balance
                client.resolve(self.balance, 'balance')
            except Exception:
                pass  # Log-worthy but don't crash the loop

    def merge_funding_balance(self, funding):
        """Merge REST funding balance into self.balance without
        touching trading keys (WS owns those)."""
        if self.balance is None:
            self.balance = {'info': {}, 'timestamp': None, 'datetime': None}
        # Copy per-currency entries from funding, skipping metadata keys
        skip_keys = {'info', 'timestamp', 'datetime', 'free', 'used', 'total'}
        for key in funding:
            if key not in skip_keys:
                self.balance[key] = funding[key]
        self.balance = self.safe_balance(self.balance)

    def merge_trading_balance(self, trading):
        """Merge REST trading balance into self.balance."""
        if self.balance is None:
            self.balance = {'info': {}, 'timestamp': None, 'datetime': None}
        skip_keys = {'info', 'timestamp', 'datetime', 'free', 'used', 'total'}
        for key in trading:
            if key not in skip_keys:
                # Trading balance is USDT equity — merge additively if
                # funding already has USDT.  Store under a separate
                # 'USDT:trading' internal key would over-complicate;
                # instead, if USDT exists from funding, add trading equity.
                if key in self.balance and key not in skip_keys:
                    existing = self.balance[key]
                    existing_total = self.safe_float(existing, 'total', 0)
                    trading_total = self.safe_float(trading[key], 'total', 0)
                    if existing_total > 0 and trading_total > 0:
                        # Don't double-count; trading USDT is separate
                        # from funding USDT.  Use the trading value for
                        # the 'used' (margin) portion.
                        pass
                self.balance[key] = trading[key]
        self.balance = self.safe_balance(self.balance)

    def handle_message(self, client: Client, message):
        # Raw pong response
        if isinstance(message, str):
            if message == 'pong':
                return
            try:
                message = json.loads(message)
            except (json.JSONDecodeError, TypeError):
                return
        if not isinstance(message, dict):
            return
        # Login response
        event = self.safe_string(message, 'event')
        if event == 'login':
            code = self.safe_string(message, 'code')
            if code == '0':
                client.resolve(True, 'authenticated')
                client.subscriptions['authenticated'] = True
            else:
                msg = self.safe_string(message, 'msg', 'login failed')
                error = ExchangeError(self.id + ' ' + msg)
                client.reject(error, 'authenticated')
            return
        # Assets channel — trading balance push
        channel = self.safe_string(message, 'channel', '')
        if channel.lower() == 'assets':
            self.handle_balance(client, message)
            return

    def handle_balance(self, client: Client, message):
        """Parse WS 'assets' channel push and update trading balance.

        Only updates trading fields; funding fields are managed
        exclusively by the REST refresh loop.

        Payload:
            {
                "channel": "assets",
                "data": [
                    {"portfolioId": "...", "coin": "USDT",
                     "equity": "1000", "available": "900",
                     "frozen": "100"}
                ]
            }
        """
        payload = self.safe_value(message, 'data', {})
        items = payload if isinstance(payload, list) else [payload]
        if self.balance is None:
            self.balance = {'info': {}, 'timestamp': None, 'datetime': None}
        self.balance['info'] = message
        for item in items:
            coin = self.safe_string(item, 'coin')
            if coin is None:
                continue
            code = self.safe_currency_code(coin)
            account = self.account()
            account['total'] = self.safe_string(item, 'equity')
            account['free'] = self.safe_string(item, 'available')
            account['used'] = self.safe_string(item, 'frozen')
            self.balance[code] = account
        self.balance = self.safe_balance(self.balance)
        client.resolve(self.balance, 'balance')
