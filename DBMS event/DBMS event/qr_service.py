"""
QR Code Service for Event Management System
Generate and manage QR codes for guest check-in
"""

import qrcode
import io
import base64
from datetime import datetime
import hashlib
import json


class QRCodeService:
    """QR Code generation and verification service"""
    
    def __init__(self):
        """Initialize QR code service"""
        print("✅ QR Code service initialized")
    
    def generate_guest_token(self, guest_id, event_id):
        """
        Generate a unique secure token for guest
        
        Args:
            guest_id (int): Guest ID
            event_id (int): Event ID
            
        Returns:
            str: Secure token
        """
        data = f"{guest_id}:{event_id}:{datetime.utcnow().isoformat()}"
        token = hashlib.sha256(data.encode()).hexdigest()
        return token[:32]  # 32 character token
    
    def generate_qr_code(self, guest_id, event_id, guest_name="Guest", existing_token=None):
        """
        Generate QR code for guest check-in
        
        Args:
            guest_id (int): Guest ID
            event_id (int): Event ID
            guest_name (str): Guest name
            existing_token (str): Reuse this token instead of generating a new one
            
        Returns:
            str: Base64 encoded QR code image
        """
        try:
            # Reuse the stored token if provided, otherwise create a new one
            token = existing_token if existing_token else self.generate_guest_token(guest_id, event_id)
            
            # Create QR data
            qr_data = {
                'guest_id': guest_id,
                'event_id': event_id,
                'token': token,
                'name': guest_name,
                'generated_at': datetime.utcnow().isoformat()
            }
            
            # Convert to JSON string
            qr_content = json.dumps(qr_data)
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_content)
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_base64}", token
            
        except Exception as e:
            print(f"❌ Error generating QR code: {str(e)}")
            return None, None
    
    def verify_qr_code(self, qr_data_json):
        """
        Verify and decode QR code data
        
        Args:
            qr_data_json (str): JSON string from QR code
            
        Returns:
            dict: Decoded QR data or None if invalid
        """
        try:
            qr_data = json.loads(qr_data_json)
            
            # Validate required fields
            required_fields = ['guest_id', 'event_id', 'token', 'name']
            if not all(field in qr_data for field in required_fields):
                return None
            
            return qr_data
            
        except Exception as e:
            print(f"❌ Error verifying QR code: {str(e)}")
            return None
    
    def download_qr_code(self, guest_id, event_id, guest_name="Guest", file_path=None):
        """
        Generate and save QR code as file
        
        Args:
            guest_id (int): Guest ID
            event_id (int): Event ID
            guest_name (str): Guest name
            file_path (str): Path to save file (optional)
            
        Returns:
            str: File path or None
        """
        try:
            # Create secure token
            token = self.generate_guest_token(guest_id, event_id)
            
            # Create QR data
            qr_data = {
                'guest_id': guest_id,
                'event_id': event_id,
                'token': token,
                'name': guest_name,
                'generated_at': datetime.utcnow().isoformat()
            }
            
            # Convert to JSON string
            qr_content = json.dumps(qr_data)
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_content)
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save to file
            if not file_path:
                file_path = f"static/qr_codes/guest_{guest_id}_event_{event_id}.png"
            
            img.save(file_path)
            
            return file_path
            
        except Exception as e:
            print(f"❌ Error saving QR code: {str(e)}")
            return None


# Initialize global service instance
qr_service = QRCodeService()


# Testing
if __name__ == '__main__':
    print("🔧 QR Code Service Testing")
    print("=" * 50)
    
    # Test QR generation
    qr_img, token = qr_service.generate_qr_code(
        guest_id=1,
        event_id=1,
        guest_name="John Doe"
    )
    
    if qr_img:
        print(f"✅ QR Code generated successfully")
        print(f"Token: {token}")
        print(f"Image length: {len(qr_img)} characters")
    else:
        print("❌ QR Code generation failed")
    
    print("\n✅ QR Code Service ready!")
