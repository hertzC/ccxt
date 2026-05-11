from ccxt.base.types import Entry


class ImplicitAPI:
    private_get_api_v1_tradeaccount_list = privateGetApiV1TradeaccountList = Entry('api/v1/tradeAccount/list', 'private', 'GET', {'cost': 1})
    private_get_api_v1_asset_getaccountcurrencyinfo = privateGetApiV1AssetGetaccountcurrencyinfo = Entry('api/v1/asset/getAccountCurrencyInfo', 'private', 'GET', {'cost': 1})
    private_get_api_v1_trading_account = privateGetApiV1TradingAccount = Entry('api/v1/trading/account', 'private', 'GET', {'cost': 1})
    private_get_api_v1_asset_currencies = privateGetApiV1AssetCurrencies = Entry('api/v1/asset/currencies', 'private', 'GET', {'cost': 1})
    private_get_api_v1_deposit_address = privateGetApiV1DepositAddress = Entry('api/v1/deposit/address', 'private', 'GET', {'cost': 1})
    private_get_api_v1_deposit_list = privateGetApiV1DepositList = Entry('api/v1/deposit/list', 'private', 'GET', {'cost': 1})
    private_get_api_v1_userwithdrawrecord_list = privateGetApiV1UserwithdrawrecordList = Entry('api/v1/userWithdrawRecord/list', 'private', 'GET', {'cost': 1})
    private_get_api_v1_transfer_list = privateGetApiV1TransferList = Entry('api/v1/transfer/list', 'private', 'GET', {'cost': 1})
    # Trading endpoints (patch 006)
    private_get_api_v1_trading_position = privateGetApiV1TradingPosition = Entry('api/v1/trading/position', 'private', 'GET', {'cost': 1})
    private_get_api_v1_trading_openorders = privateGetApiV1TradingOpenorders = Entry('api/v1/trading/openOrders', 'private', 'GET', {'cost': 1})
    private_get_api_v1_trading_history_orders = privateGetApiV1TradingHistoryOrders = Entry('api/v1/trading/history/orders', 'private', 'GET', {'cost': 1})
    private_get_api_v1_trading_history_position = privateGetApiV1TradingHistoryPosition = Entry('api/v1/trading/history/position', 'private', 'GET', {'cost': 1})
    private_get_api_v1_trading_transactions = privateGetApiV1TradingTransactions = Entry('api/v1/trading/transactions', 'private', 'GET', {'cost': 1})
    private_get_api_v1_trading_fundingfee_current = privateGetApiV1TradingFundingfeeCurrent = Entry('api/v1/trading/fundingFee/current', 'private', 'GET', {'cost': 1})
    private_get_api_v1_trading_portfolio_assets = privateGetApiV1TradingPortfolioAssets = Entry('api/v1/trading/portfolio/assets', 'private', 'GET', {'cost': 1})
    private_get_api_v1_sym_info = privateGetApiV1SymInfo = Entry('api/v1/sym/info', 'private', 'GET', {'cost': 1})
