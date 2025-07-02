from bit import PrivateKey

def send_ltc(wif_key, recipient_address, amount_btc):
    """
    Sends LTC using a WIF private key
    :param wif_key: Your Guarda WIF key
    :param recipient_address: LTC address to send to
    :param amount_btc: Amount in BTC format (e.g., 0.0001 BTC = ~$0.10)
    :return: TXID
    """
    key = PrivateKey.from_wif(wif_key)
    tx_hash = key.send([(recipient_address, amount_btc, 'btc')])
    return tx_hash
