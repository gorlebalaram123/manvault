from .models import Notification
from django.core.mail import send_mail
from django.conf import settings

def notify(user, title, message, notif_type='system', link=''):
    Notification.objects.create(user=user, title=title, message=message, notif_type=notif_type, link=link)

def send_otp_email(user, otp_code, purpose="verification"):
    subject = f"ManVault OTP: {otp_code}"
    body = f"""Hi {user.first_name or user.username},

Your ManVault OTP for {purpose} is:

  ━━━━━━━━━━━━━━━
       {otp_code}
  ━━━━━━━━━━━━━━━

This OTP expires in 10 minutes. Do not share it with anyone.

— Team ManVault
"""
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
    except Exception:
        pass

def send_order_email(user, order, event):
    events = {
        'placed': ('Order Placed 🎉', f'Your order #{order.order_number} has been placed! Total: ₹{order.total}'),
        'shipped': ('Order Shipped 🚚', f'Your order #{order.order_number} is on its way! Tracking: {order.tracking_number}'),
        'out_for_delivery': ('Out for Delivery 📦', f'Your order #{order.order_number} will be delivered today. OTP: {order.delivery_otp}'),
        'delivered': ('Delivered ✅', f'Your order #{order.order_number} has been delivered!'),
        'cancelled': ('Order Cancelled', f'Your order #{order.order_number} has been cancelled.'),
    }
    if event in events:
        subject, body = events[event]
        try:
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
        except Exception:
            pass
        notify(user, subject, body, notif_type='order', link=f'/orders/{order.order_number}/')
