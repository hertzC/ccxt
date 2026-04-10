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
