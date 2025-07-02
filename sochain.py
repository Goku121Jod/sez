import requests

async def check_ltc_transaction(address):
    url = f"https://sochain.com/api/v2/get_address_balance/LTC/mainnet/ {address}"

    try:
        response = requests.get(url)
        data = response.json()

        if float(data["data"]["received_value"]) > 0:
            txid = data["data"]["transactions"][0]
            return {"success": True, "txid": txid}

        return {"success": False}

    except Exception as e:
        return {"success": False, "error": str(e)}
