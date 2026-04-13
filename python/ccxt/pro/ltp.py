# -*- coding: utf-8 -*-

import ccxt.async_support
from ccxt.base.types import Any, Balances
from ccxt.async_support.base.ws.client import Client
from ccxt.base.errors import ExchangeError
import hashlib
import json


class ltp(ccxt.async_support.ltp):

    def describe(self) -> dict[str, Any]:
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

    async def watch_balance(self, params: dict = {}) -> Balances:
        """Watch balance updates via LTP private WebSocket.

        LTP auto-pushes the ``assets`` channel after login for trading
        balance changes.  Funding wallet is NOT pushed, so this method
        internally runs a periodic REST poll to keep funding balances
        current.  Callers get a unified view without knowing about the
        limitation.
        """
        await self.load_markets()
        url: str = self.urls['api']['ws']
        message_hash: str = 'balance'
        subscribe_hash: str = 'balance:login'
        # Build a fresh login message each time (timestamp must be current).
        # watch() sends this after establishing the WS connection.
        self.check_required_credentials()
        timestamp: str = str(int(self.seconds()))
        sign_string: str = timestamp + 'GET' + '/users/self/verify'
        signature: str = self.hmac(
            self.encode(sign_string),
            self.encode(self.secret),
            hashlib.sha256,
        )
        login_request: dict = {
            'action': 'login',
            'args': {
                'apiKey': self.apiKey,
                'timestamp': timestamp,
                'sign': signature,
            },
        }
        client: Client = self.client(url)
        # First call: seed balance from REST and spawn background loops
        if 'balance:seeded' not in client.subscriptions:
            client.subscriptions['balance:seeded'] = True
            # Seed both funding and trading via REST
            try:
                funding: Balances = await self.fetch_balance({'type': 'funding'})
                self.merge_funding_balance(funding)
            except Exception:
                pass  # Subaccount keys may lack funding permission
            try:
                trading: Balances = await self.fetch_balance({'type': 'trading'})
                self.merge_trading_balance(trading)
            except Exception:
                pass
            # Spawn periodic background tasks
            self.spawn(self.funding_refresh_loop, url)
            self.spawn(self.heartbeat_loop, url)
        # watch() establishes the WS connection, then sends login_request.
        # LTP auto-pushes 'assets' channel after successful login — no
        # explicit subscribe needed.
        return await self.watch(url, message_hash, login_request, subscribe_hash)

    async def heartbeat_loop(self, url: str) -> None:
        """Send raw 'ping' string every heartbeatInterval ms."""
        client: Client = self.client(url)
        ws_options: dict = self.safe_dict(self.options, 'ws', {})
        interval: int = self.safe_integer(ws_options, 'heartbeatInterval', 20000)
        try:
            while True:
                await self.sleep(interval)
                if not client.connected:
                    break
                await client.send('ping')
        except Exception:
            pass  # CancelledError on close is expected

    async def funding_refresh_loop(self, url: str) -> None:
        """Periodically fetch funding balance via REST and merge.

        LTP WebSocket does NOT push funding wallet updates (deposits,
        withdrawals, transfers).  This loop ensures funding balances
        stay current within fundingRefreshInterval.
        """
        client: Client = self.client(url)
        ws_options: dict = self.safe_dict(self.options, 'ws', {})
        interval: int = self.safe_integer(ws_options, 'fundingRefreshInterval', 60000)
        try:
            while True:
                await self.sleep(interval)
                if not client.connected:
                    break
                funding: Balances = await self.fetch_balance({'type': 'funding'})
                self.merge_funding_balance(funding)
                client.resolve(self.balance, 'balance')
        except Exception:
            pass  # CancelledError on close is expected

    def merge_funding_balance(self, funding: Balances) -> None:
        """Merge REST funding balance into self.balance without
        touching trading keys (WS owns those)."""
        if self.balance is None:
            self.balance = {'info': {}, 'timestamp': None, 'datetime': None}
        skip_keys: set[str] = {'info', 'timestamp', 'datetime', 'free', 'used', 'total'}
        for key in funding:
            if key not in skip_keys:
                self.balance[key] = funding[key]
        self.balance = self.safe_balance(self.balance)

    def merge_trading_balance(self, trading: Balances) -> None:
        """Merge REST trading balance into self.balance."""
        if self.balance is None:
            self.balance = {'info': {}, 'timestamp': None, 'datetime': None}
        skip_keys: set[str] = {'info', 'timestamp', 'datetime', 'free', 'used', 'total'}
        for key in trading:
            if key not in skip_keys:
                self.balance[key] = trading[key]
        self.balance = self.safe_balance(self.balance)

    def handle_message(self, client: Client, message: Any) -> None:
        # Raw pong response (LTP sends 'pong' as plain text)
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
        event: str | None = self.safe_string(message, 'event')
        if event == 'login':
            code: str = self.safe_string(message, 'code')
            if code == '0':
                # Login succeeded — resolve the balance future with
                # the seeded balance so the first await returns immediately.
                if self.balance is not None:
                    client.resolve(self.balance, 'balance')
            else:
                msg: str = self.safe_string(message, 'msg', 'login failed')
                error: ExchangeError = ExchangeError(self.id + ' ' + msg)
                client.reject(error, 'balance')
            return
        # Assets channel — trading balance push
        channel: str = self.safe_string(message, 'channel', '')
        if channel.lower() == 'assets':
            self.handle_balance(client, message)
            return

    def handle_balance(self, client: Client, message: dict) -> None:
        """Parse WS 'assets' channel push and update trading balance.

        Only updates trading fields; funding fields are managed
        exclusively by the REST refresh loop.
        """
        payload: Any = self.safe_value(message, 'data', {})
        items: list = payload if isinstance(payload, list) else [payload]
        if self.balance is None:
            self.balance = {'info': {}, 'timestamp': None, 'datetime': None}
        self.balance['info'] = message
        for item in items:
            coin: str | None = self.safe_string(item, 'coin')
            if coin is None:
                continue
            code: str = self.safe_currency_code(coin)
            account: dict = self.account()
            account['total'] = self.safe_string(item, 'equity')
            account['free'] = self.safe_string(item, 'available')
            account['used'] = self.safe_string(item, 'frozen')
            self.balance[code] = account
        self.balance = self.safe_balance(self.balance)
        client.resolve(self.balance, 'balance')
