import os
import stripe
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()
stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")

if stripe_secret_key:
    stripe.api_key = stripe_secret_key

async def create_payment(amount: int, currency: str = "usd", description: str = ""):
    if not stripe_secret_key:
        raise HTTPException(status_code=500, detail="Stripe secret key not configured")
    
    try:
        payment_intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency, 
            description=description
        )
        return payment_intent
        
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")

