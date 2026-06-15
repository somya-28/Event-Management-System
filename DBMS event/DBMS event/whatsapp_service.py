import os
import logging
from twilio.rest import Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WhatsAppService:
    """Service to handle sending WhatsApp messages using Twilio API"""
    
    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.from_number = os.getenv('TWILIO_WHATSAPP_NUMBER')
        self.client = None
        
        if self.account_sid and self.auth_token and self.from_number:
            try:
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("Twilio WhatsApp Client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio Client: {e}")
        else:
            logger.warning("Twilio API credentials missing. WhatsApp service will not function.")

    def send_invitation(self, guest, event):
        """
        Send a WhatsApp invitation to a guest
        
        Args:
            guest: Guest object
            event: Event object
            
        Returns:
            tuple: (success_boolean, message_or_error_string)
        """
        if not self.client:
            return False, "WhatsApp API is not configured properly."
            
        if not guest.phone:
            return False, "Guest does not have a phone number."
            
        try:
            # Format phone number for WhatsApp 
            # (assuming India country code +91 for 10-digit numbers)
            phone = str(guest.phone).strip()
            if len(phone) == 10 and phone.isdigit():
                phone = f"+91{phone}"
            elif not phone.startswith('+'):
                phone = f"+{phone}"
                
            to_whatsapp_number = f"whatsapp:{phone}"
            
            # Format Twilio From number
            from_whatsapp = self.from_number
            if not from_whatsapp.startswith('+'):
                from_whatsapp = f"+{from_whatsapp}"
            from_whatsapp_number = f"whatsapp:{from_whatsapp}"
            
            # Format Date and Time
            event_date = event.event_date.strftime('%d %b %Y') if event.event_date else 'TBD'
            event_time = event.event_time.strftime('%I:%M %p') if event.event_time else 'TBD'
            
            # Message Template
            message_body = (
                f"🎉 *You are Invited!* 🎉\n\n"
                f"Dear {guest.name},\n\n"
                f"You have been invited to *{event.name}*.\n\n"
                f"📅 *Date:* {event_date}\n"
                f"⏰ *Time:* {event_time}\n"
                f"📍 *Venue:* {event.location or 'TBD'}\n\n"
                f"🎫 *Invitation ID:* {guest.id}\n\n"
                f"We look forward to seeing you!"
            )
            
            message = self.client.messages.create(
                body=message_body,
                from_=from_whatsapp_number,
                to=to_whatsapp_number
            )
            
            logger.info(f"WhatsApp invitation sent to {guest.name} ({phone}) - SID: {message.sid}")
            return True, message.sid
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp message to {guest.name}: {e}")
            return False, str(e)

# Initialize global service instance
whatsapp_service = WhatsAppService()
