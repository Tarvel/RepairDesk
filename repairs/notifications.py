"""
RepairDesk - Notification Hooks

Placeholder functions for WhatsApp, SMS, and Email notifications.
These will be implemented with actual service integrations later.
"""
import logging

logger = logging.getLogger(__name__)


def send_whatsapp_notification(phone: str, message: str) -> bool:
    """
    Send WhatsApp notification to customer.
    
    TODO: Integrate with WhatsApp Business API or Twilio.
    
    Args:
        phone: Customer phone number (e.g., "08012345678")
        message: Message content
        
    Returns:
        True if sent successfully, False otherwise
    """
    logger.info(f"[PLACEHOLDER] WhatsApp to {phone}: {message}")
    # TODO: Implement actual WhatsApp integration
    # Example with Twilio:
    # from twilio.rest import Client
    # client = Client(account_sid, auth_token)
    # client.messages.create(
    #     body=message,
    #     from_='whatsapp:+14155238886',
    #     to=f'whatsapp:+234{phone[1:]}'
    # )
    return True


def send_sms_notification(phone: str, message: str) -> bool:
    """
    Send SMS notification to customer.
    
    TODO: Integrate with SMS gateway (e.g., Twilio, Africa's Talking).
    
    Args:
        phone: Customer phone number
        message: Message content
        
    Returns:
        True if sent successfully, False otherwise
    """
    logger.info(f"[PLACEHOLDER] SMS to {phone}: {message}")
    # TODO: Implement actual SMS integration
    return True


def send_email_notification(email: str, subject: str, body: str) -> bool:
    """
    Send email notification to customer.
    
    Uses Django's built-in email functionality.
    
    Args:
        email: Customer email address
        subject: Email subject
        body: Email body content
        
    Returns:
        True if sent successfully, False otherwise
    """
    if not email:
        logger.warning("No email address provided, skipping email notification")
        return False
        
    logger.info(f"[PLACEHOLDER] Email to {email}: {subject}")
    # TODO: Configure Django EMAIL settings and uncomment:
    # from django.core.mail import send_mail
    # send_mail(
    #     subject=subject,
    #     message=body,
    #     from_email='noreply@repairdesk.ng',
    #     recipient_list=[email],
    # )
    return True


def notify_status_change(ticket, status_message: str):
    """
    Generic notification for any status change.
    
    Args:
        ticket: RepairTicket instance
        status_message: Human-readable status message
    """
    customer = ticket.device.customer
    message = (
        f"RepairDesk Update\n\n"
        f"Ticket: #{ticket.ticket_number}\n"
        f"Device: {ticket.device.brand} {ticket.device.model_name}\n"
        f"Status: {status_message}\n\n"
        f"Thank you for choosing RepairDesk."
    )
    
    # Send via all available channels
    send_whatsapp_notification(customer.phone, message)
    send_sms_notification(customer.phone, message)
    if customer.email:
        send_email_notification(
            customer.email,
            f"Ticket #{ticket.ticket_number} - {status_message}",
            message
        )


def notify_customer_awaiting_approval(ticket):
    """
    Notify customer that quote is ready for approval.
    
    Sent when technician completes diagnosis and generates invoice.
    """
    customer = ticket.device.customer
    
    message = (
        f"RepairDesk Quote Ready\n\n"
        f"Ticket: #{ticket.ticket_number}\n"
        f"Device: {ticket.device.brand} {ticket.device.model_name}\n\n"
        f"Estimated Cost:\n"
        f"  Parts: ₦{ticket.parts_cost:,.2f}\n"
        f"  Labor: ₦{ticket.labor_cost:,.2f}\n"
        f"  Total: ₦{ticket.total_cost:,.2f}\n\n"
        f"Please approve or reject this quote to proceed.\n"
        f"Reply 'APPROVE' to proceed or 'REJECT' to cancel."
    )
    
    send_whatsapp_notification(customer.phone, message)
    send_sms_notification(customer.phone, message)
    if customer.email:
        send_email_notification(
            customer.email,
            f"Quote Ready - Ticket #{ticket.ticket_number}",
            message
        )


def notify_customer_ready(ticket, cancelled: bool = False):
    """
    Notify customer that device is ready for pickup.
    
    Args:
        ticket: RepairTicket instance
        cancelled: True if repair was rejected/cancelled
    """
    customer = ticket.device.customer
    
    if cancelled:
        message = (
            f"RepairDesk - Device Ready for Pickup\n\n"
            f"Ticket: #{ticket.ticket_number}\n"
            f"Device: {ticket.device.brand} {ticket.device.model_name}\n\n"
            f"Your device is ready for collection.\n"
            f"Note: Repair was not performed as per your request.\n\n"
            f"Please visit our shop to collect your device."
        )
    else:
        message = (
            f"RepairDesk - Repair Complete!\n\n"
            f"Ticket: #{ticket.ticket_number}\n"
            f"Device: {ticket.device.brand} {ticket.device.model_name}\n\n"
            f"Great news! Your device repair is complete and has passed our quality check.\n\n"
            f"Balance Due: ₦{ticket.balance_due:,.2f}\n\n"
            f"Please visit our shop to collect your device.\n"
            f"90-day warranty will be activated upon collection."
        )
    
    send_whatsapp_notification(customer.phone, message)
    send_sms_notification(customer.phone, message)
    if customer.email:
        send_email_notification(
            customer.email,
            f"Device Ready - Ticket #{ticket.ticket_number}",
            message
        )
