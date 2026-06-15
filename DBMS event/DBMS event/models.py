from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(10), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

class Event(db.Model):
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    event_date = db.Column(db.Date, nullable=False)
    event_time = db.Column(db.Time)
    location = db.Column(db.String(255))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    venue_capacity = db.Column(db.Integer)
    budget = db.Column(db.Numeric(10, 2), default=0.00)
    status = db.Column(db.Enum('Planning', 'Confirmed', 'Completed', 'Cancelled'), default='Planning')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='events', lazy=True)
    guests = db.relationship('Guest', backref='event', lazy=True, cascade='all, delete-orphan')
    bookings = db.relationship('Booking', backref='event', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.full_name if self.user else None,
            'name': self.name,
            'description': self.description,
            'event_date': self.event_date.strftime('%Y-%m-%d') if self.event_date else None,
            'event_time': self.event_time.strftime('%H:%M') if self.event_time else None,
            'location': self.location,
            'budget': float(self.budget) if self.budget else 0.00,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'guest_count': len(self.guests),
            'booking_count': len(self.bookings)
        }


class Guest(db.Model):
    __tablename__ = 'guests'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    rsvp_status = db.Column(db.Enum('Pending', 'Accepted', 'Declined'), default='Pending')
    guest_count = db.Column(db.Integer, default=1)
    dietary_requirements = db.Column(db.Text)
    # QR Code Check-in fields
    qr_token = db.Column(db.String(100))
    checked_in = db.Column(db.Boolean, default=False)
    check_in_time = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='guests', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'user_id': self.user_id,
            'event_name': self.event.name if self.event else None,
            'user_name': self.user.full_name if self.user else None,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'rsvp_status': self.rsvp_status,
            'guest_count': self.guest_count,
            'dietary_requirements': self.dietary_requirements,
            'checked_in': self.checked_in,
            'check_in_time': self.check_in_time.strftime('%Y-%m-%d %H:%M:%S') if self.check_in_time else None,
            'qr_token': self.qr_token
        }


class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    booking_type = db.Column(db.Enum('Venue', 'Catering', 'Photography', 'Music', 'Decoration', 'Other'), nullable=False)
    vendor_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    cost = db.Column(db.Numeric(10, 2), default=0.00)
    booking_date = db.Column(db.Date)
    status = db.Column(db.Enum('Pending', 'Confirmed', 'Paid', 'Cancelled'), default='Pending')
    contact_info = db.Column(db.String(255))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='bookings', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'user_id': self.user_id,
            'event_name': self.event.name if self.event else None,
            'user_name': self.user.full_name if self.user else None,
            'booking_type': self.booking_type,
            'vendor_name': self.vendor_name,
            'description': self.description,
            'cost': float(self.cost) if self.cost else 0.00,
            'booking_date': self.booking_date.strftime('%Y-%m-%d') if self.booking_date else None,
            'status': self.status,
            'contact_info': self.contact_info,
            'notes': self.notes
        }
