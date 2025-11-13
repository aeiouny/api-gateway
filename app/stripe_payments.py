# ============================================================================
# STRIPE PAYMENT INTEGRATION
# ============================================================================
# This module handles Stripe payment processing
# Stripe is a payment processing platform that handles credit card transactions
# ============================================================================

import os
import stripe
from fastapi import HTTPException
from dotenv import load_dotenv

# Load environment variables from .env file
# This is where we store the Stripe secret key (should never be in code)
load_dotenv()

# Get Stripe secret key from environment variables
# Secret keys start with "sk_" and authenticate our API calls to Stripe
# In production, use environment variables or secret management services
stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")

# Configure Stripe SDK with the secret key
# This sets the API key for all Stripe API calls in this module
if stripe_secret_key:
    stripe.api_key = stripe_secret_key

async def create_payment(amount: int, currency: str = "usd", description: str = ""):
    """
    Create a Stripe payment intent.
    
    Payment Intent: A Stripe object that represents your intention to collect payment
    - Created before the customer enters payment details
    - Returns a client_secret that frontend uses to complete payment with Stripe.js
    - Amount is in smallest currency unit (cents for USD, e.g., 2000 = $20.00)
    
    Parameters:
    - amount: Payment amount in cents (integer, required)
    - currency: Currency code (default: "usd")
    - description: Optional description of the payment
    
    Returns:
    - PaymentIntent object with id, client_secret, status, amount, etc.
    
    Raises:
    - HTTPException 500: If Stripe key not configured
    - HTTPException 400: If Stripe API returns an error (invalid card, declined, etc.)
    """
    # Check if Stripe is configured
    # If no secret key, we can't process payments - return server error
    if not stripe_secret_key:
        raise HTTPException(status_code=500, detail="Stripe secret key not configured")
    
    try:
        # Call Stripe API to create a payment intent
        # PaymentIntent.create() makes HTTP request to Stripe's API
        # This creates a payment intent on Stripe's servers
        payment_intent = stripe.PaymentIntent.create(
            amount=amount,           # Amount in cents (e.g., 2000 = $20.00)
            currency=currency,       # Currency code (usd, eur, gbp, etc.)
            description=description  # Optional description shown to customer
        )
        
        # Return the payment intent object
        # Contains: id, client_secret, status, amount, currency, etc.
        # The client_secret is used by frontend to confirm payment with Stripe.js
        return payment_intent
        
    except stripe.error.StripeError as e:
        # Handle Stripe-specific errors
        # Examples: invalid card number, declined payment, network error, etc.
        # Convert to HTTP 400 (Bad Request) so client knows the request was invalid
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")

