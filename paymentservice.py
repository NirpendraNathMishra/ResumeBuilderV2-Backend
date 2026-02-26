"""
Razorpay Payment Service V2 — same as V1.
"""
import razorpay
import uuid
from fastapi import HTTPException
from config import RAZORPAY_KEY, RAZORPAY_SECRET

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY, RAZORPAY_SECRET))


async def create_order(amount: int, currency="INR", receipt: str = None):
    try:
        order_data = {
            "amount": amount * 100,
            "currency": currency,
            "receipt": receipt or str(uuid.uuid4()),
            "payment_capture": 1,
        }
        order = razorpay_client.order.create(data=order_data)
        return order
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment order creation failed: {str(e)}")


async def verify_payment(payment_id: str, order_id: str, signature: str):
    try:
        params_dict = {
            "razorpay_payment_id": payment_id,
            "razorpay_order_id": order_id,
            "razorpay_signature": signature,
        }
        razorpay_client.utility.verify_payment_signature(params_dict)
        return True
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Payment verification failed: {str(e)}")
