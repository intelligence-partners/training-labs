import json
import os

ORDERS = {
    "A-1042": {"orderId": "A-1042", "status": "expédiée", "carrier": "Colissimo", "totalCents": 18990},
    "A-1043": {"orderId": "A-1043", "status": "en préparation", "carrier": None, "totalCents": 2450},
    "B2B-77": {"orderId": "B2B-77", "status": "livrée", "carrier": "DB Schenker", "totalCents": 128000},
}


def _resp(code, body):
    return {"statusCode": code, "headers": {"content-type": "application/json"},
            "body": json.dumps(body, ensure_ascii=False)}


def handler(event, context):
    headers = event.get("headers") or {}
    if headers.get("x-api-key") != os.environ["API_KEY"]:
        return _resp(401, {"message": "clé API absente ou invalide"})
    method = event["requestContext"]["http"]["method"]
    path = event.get("rawPath", "")
    q = event.get("queryStringParameters") or {}
    if method == "GET" and path.startswith("/orders/"):
        order = ORDERS.get(path.rsplit("/", 1)[-1])
        return _resp(200, order) if order else _resp(404, {"message": "commande inconnue"})
    if method == "POST" and path == "/tickets":
        return _resp(201, {"ticketId": "T-" + q.get("orderId", "0000"), "status": "ouvert",
                           "summary": q.get("summary", "")})
    if method == "POST" and path == "/refunds":
        return _resp(201, {"refundId": "R-" + q.get("orderId", "0000"),
                           "amountCents": int(q.get("amountCents", "0")), "status": "accepté"})
    return _resp(404, {"message": "route inconnue"})
