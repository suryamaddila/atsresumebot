import logging
import json
import hashlib
import hmac
import time
from typing import Dict, Any, Optional
import requests
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CashfreePayment:
    """Cashfree Payment Gateway Integration"""
    
    def __init__(self, config):
        self.config = config
        self.client_id = config.CASHFREE_CLIENT_ID
        self.client_secret = config.CASHFREE_CLIENT_SECRET
        self.app_id = config.CASHFREE_APP_ID
        
        # Set base URL based on environment
        if config.PAYMENT_GATEWAY_MODE == "production":
            self.base_url = "https://api.cashfree.com/pg"
            self.upi_base_url = "https://api.cashfree.com/pg/orders"
        else:
            self.base_url = "https://sandbox.cashfree.com/pg"
            self.upi_base_url = "https://sandbox.cashfree.com/pg/orders"
        
        self.headers = {
            "Content-Type": "application/json",
            "x-client-id": self.client_id,
            "x-client-secret": self.client_secret,
            "x-api-version": "2023-08-01"
        }
    
    async def create_payment_order(self, user_id: int, payment_id: str, amount: float = None) -> Dict[str, Any]:
        """Create a payment order with Cashfree"""
        try:
            amount = amount or self.config.PAYMENT_AMOUNT
            
            order_data = {
                "order_id": payment_id,
                "order_amount": amount,
                "order_currency": "INR",
                "customer_details": {
                    "customer_id": str(user_id),
                    "customer_name": f"User_{user_id}",
                    "customer_email": f"user_{user_id}@suryaatsresume.com",
                    "customer_phone": "9999999999"  # Placeholder
                },
                "order_meta": {
                    "return_url": f"https://ats-resume-bot.onrender.com/payment/callback/{payment_id}",
                    "notify_url": f"https://ats-resume-bot.onrender.com/payment/webhook/{payment_id}"
                },
                "order_expiry_time": (datetime.now() + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "order_note": "ATS Resume Optimization Payment"
            }
            
            response = requests.post(
                f"{self.base_url}/orders",
                headers=self.headers,
                json=order_data,
                timeout=30
            )
            
            if response.status_code == 200:
                order_response = response.json()
                logger.info(f"Payment order created successfully: {payment_id}")
                return {
                    "success": True,
                    "order_id": order_response.get("order_id"),
                    "payment_session_id": order_response.get("payment_session_id"),
                    "order_token": order_response.get("order_token"),
                    "order_amount": order_response.get("order_amount"),
                    "order_currency": order_response.get("order_currency"),
                    "order_status": order_response.get("order_status")
                }
            else:
                logger.error(f"Cashfree order creation failed: {response.text}")
                return {
                    "success": False,
                    "error": response.json().get("message", "Order creation failed")
                }
                
        except Exception as e:
            logger.error(f"Error creating Cashfree order: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_upi_payment_link(self, payment_id: str, amount: float, user_id: int) -> Dict[str, Any]:
        """Create UPI payment link specifically"""
        try:
            # First create the order
            order_result = await self.create_payment_order(user_id, payment_id, amount)
            
            if not order_result.get("success"):
                return order_result
            
            # Create UPI payment link
            upi_data = {
                "payment_method": "upi",
                "upi": {
                    "channel": "link"
                }
            }
            
            payment_response = requests.post(
                f"{self.upi_base_url}/{payment_id}/payments",
                headers=self.headers,
                json=upi_data,
                timeout=30
            )
            
            if payment_response.status_code == 200:
                payment_data = payment_response.json()
                return {
                    "success": True,
                    "payment_url": payment_data.get("data", {}).get("payment_url"),
                    "upi_id": self.config.UPI_ID,  # Your UPI ID for direct payments
                    "order_id": payment_id,
                    "amount": amount,
                    "qr_code": payment_data.get("data", {}).get("qr_code"),
                    "payment_link": payment_data.get("data", {}).get("payment_url")
                }
            else:
                # Fallback to manual UPI instructions
                return {
                    "success": True,
                    "manual_upi": True,
                    "upi_id": self.config.UPI_ID,
                    "order_id": payment_id,
                    "amount": amount,
                    "payment_url": None
                }
                
        except Exception as e:
            logger.error(f"Error creating UPI payment link: {e}")
            # Return manual UPI as fallback
            return {
                "success": True,
                "manual_upi": True,
                "upi_id": self.config.UPI_ID,
                "order_id": payment_id,
                "amount": amount,
                "error_fallback": str(e)
            }
    
    async def verify_payment_status(self, order_id: str) -> Dict[str, Any]:
        """Verify payment status with Cashfree"""
        try:
            response = requests.get(
                f"{self.base_url}/orders/{order_id}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                order_data = response.json()
                return {
                    "success": True,
                    "order_id": order_data.get("order_id"),
                    "order_status": order_data.get("order_status"),
                    "payment_status": order_data.get("order_status"),
                    "order_amount": order_data.get("order_amount"),
                    "paid_amount": order_data.get("paid_amount", 0),
                    "cf_payment_id": order_data.get("cf_payment_id"),
                    "payment_time": order_data.get("payment_time"),
                    "is_paid": order_data.get("order_status") == "PAID"
                }
            else:
                logger.error(f"Payment status check failed: {response.text}")
                return {
                    "success": False,
                    "error": "Status check failed"
                }
                
        except Exception as e:
            logger.error(f"Error checking payment status: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_payment_details(self, order_id: str, cf_payment_id: str = None) -> Dict[str, Any]:
        """Get detailed payment information"""
        try:
            if cf_payment_id:
                url = f"{self.base_url}/orders/{order_id}/payments/{cf_payment_id}"
            else:
                url = f"{self.base_url}/orders/{order_id}/payments"
            
            response = requests.get(
                url,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json()
                }
            else:
                return {
                    "success": False,
                    "error": response.text
                }
                
        except Exception as e:
            logger.error(f"Error getting payment details: {e}")
            return {"success": False, "error": str(e)}
    
    def verify_webhook_signature(self, payload: str, signature: str, timestamp: str) -> bool:
        """Verify Cashfree webhook signature"""
        try:
            # Create the signing string
            signing_string = f"{timestamp}.{payload}"
            
            # Generate signature
            expected_signature = hmac.new(
                self.client_secret.encode('utf-8'),
                signing_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            return hmac.compare_digest(expected_signature, signature)
            
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False
    
    async def refund_payment(self, order_id: str, refund_amount: float = None, reason: str = "User request") -> Dict[str, Any]:
        """Refund a payment (if needed)"""
        try:
            refund_id = f"refund_{order_id}_{int(time.time())}"
            
            refund_data = {
                "refund_id": refund_id,
                "refund_amount": refund_amount or self.config.PAYMENT_AMOUNT,
                "refund_note": reason
            }
            
            response = requests.post(
                f"{self.base_url}/orders/{order_id}/refunds",
                headers=self.headers,
                json=refund_data,
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "refund_id": refund_id,
                    "data": response.json()
                }
            else:
                return {
                    "success": False,
                    "error": response.text
                }
                
        except Exception as e:
            logger.error(f"Error processing refund: {e}")
            return {"success": False, "error": str(e)}