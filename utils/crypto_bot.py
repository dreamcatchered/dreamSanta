import requests

class CryptoBotAPI:
    def __init__(self, token):
        self.token = token
        self.base_url = "https://testnet-pay.crypt.bot/api/"
        self.headers = {"Crypto-Pay-API-Token": token}

    def create_invoice(self, amount_usdt, description="", user_id=None):
        endpoint = f"{self.base_url}createInvoice"
        payload = {
            "asset": "USDT",
            "amount": str(round(amount_usdt, 2)),
            "description": description,
            "allow_anonymous": False,
            "expires_in": 3600
        }
        if user_id:
            payload["payload"] = str(user_id)
            
        try:
            response = requests.post(endpoint, json=payload, headers=self.headers)
            return response.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_invoices(self, invoice_ids=None):
        endpoint = f"{self.base_url}getInvoices"
        params = {}
        if invoice_ids:
            params["invoice_ids"] = ",".join(map(str, invoice_ids))
        try:
            response = requests.get(endpoint, params=params, headers=self.headers)
            return response.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def check_invoice_status(self, invoice_id):
        res = self.get_invoices(invoice_ids=[invoice_id])
        if res.get("ok") and res["result"]["items"]:
            return res["result"]["items"][0]["status"]
        return "not_found"

