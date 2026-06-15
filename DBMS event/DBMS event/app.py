from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from models import db, Event, Guest, Booking, User
from config import Config
from datetime import datetime
from sqlalchemy import func
from functools import wraps
import re
import random
import os
import json
from qr_service import qr_service
from email_service import email_service
from whatsapp_service import whatsapp_service

app = Flask(__name__)
app.config.from_object(Config) 

# Update configuration for development
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False,  # Set to True in production with HTTPS
    WTF_CSRF_ENABLED=False  # Disable CSRF for development
)

# Test route to verify server is running
@app.route('/test')
def test():
    return 'Server is running!', 200

# Initialize database
db.init_app(app)

# Create tables if they don't exist
with app.app_context():
    db.create_all()


# Validation helper functions
def validate_gmail(email):
    """Validate that email is a Gmail address"""
    if not email:
        return True  # Allow empty email
    pattern = r'^[a-zA-Z0-9._%+-]+@gmail\.com$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """Validate that phone is exactly 10 digits"""
    if not phone:
        return True  # Allow empty phone
    pattern = r'^[0-9]{10}$'
    return re.match(pattern, phone) is not None


def validate_future_date(date_str):
    """Validate that the date is today or in the future"""
    try:
        input_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        today = datetime.now().date()
        if input_date < today:
            return False, "Event date cannot be in the past. Please select today's date or a future date."
        return True, ""
    except ValueError as e:
        return False, "Invalid date format. Please use YYYY-MM-DD."


# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:  # Check if user is logged in
            # Check if it's an AJAX/JSON request
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': 'Please login to access this feature'
                }), 401
            flash('Please login to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ============= AUTHENTICATION ROUTES =============

@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('login'))


# ============= SIMPLE REGISTRATION =============

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register new user"""
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            full_name = request.form.get('full_name')
            phone = request.form.get('phone')
            
            # Validate email (must be Gmail)
            if email and not validate_gmail(email):
                flash('Email must be a Gmail address (@gmail.com)', 'error')
                return render_template('auth/register.html')
            
            # Validate phone
            if phone and not validate_phone(phone):
                flash('Phone must be exactly 10 digits', 'error')
                return render_template('auth/register.html')
            
            # Check if user exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists', 'error')
                return render_template('auth/register.html')
            
            if email and User.query.filter_by(email=email).first():
                flash('Email already registered', 'error')
                return render_template('auth/register.html')
            
            if phone and User.query.filter_by(phone=phone).first():
                flash('Phone already registered', 'error')
                return render_template('auth/register.html')
            
            # Create user
            user = User(
                username=username,
                email=email,
                phone=phone,
                full_name=full_name
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'error')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')


# ============= SIMPLE LOGIN =============

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            
            # Find user by username or email
            user = User.query.filter(
                (User.username == username) | (User.email == username)
            ).first()
            
            if user and user.check_password(password):
                # Login successful
                session['user_id'] = user.id
                session['username'] = user.username
                session['user_full_name'] = user.full_name or user.username
                
                flash(f'Welcome back, {user.full_name or user.username}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username/email or password', 'error')
                
        except Exception as e:
            flash(f'Login failed: {str(e)}', 'error')
    
    return render_template('auth/login.html')


# ============= PUBLIC PAGES =============
@app.route('/')
def index():
    return redirect(url_for('login'))

# Dashboard Route
@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard showing overview of user's events"""
    total_events = Event.query.filter_by(user_id=session['user_id']).count()
    upcoming_events = Event.query.filter(Event.user_id == session['user_id'], Event.event_date >= datetime.now().date()).count()
    total_guests = Guest.query.filter_by(user_id=session['user_id']).count()
    total_bookings = Booking.query.filter_by(user_id=session['user_id']).count()
    
    # Get recent events for current user
    recent_events = Event.query.filter_by(user_id=session['user_id']).order_by(Event.created_at.desc()).limit(5).all()
    
    # Calculate total budget for current user
    total_budget = db.session.query(func.sum(Event.budget)).filter_by(user_id=session['user_id']).scalar() or 0
    
    # RSVP statistics for current user
    rsvp_stats = {
        'accepted': Guest.query.filter_by(user_id=session['user_id'], rsvp_status='Accepted').count(),
        'pending': Guest.query.filter_by(user_id=session['user_id'], rsvp_status='Pending').count(),
        'declined': Guest.query.filter_by(user_id=session['user_id'], rsvp_status='Declined').count()
    }
    
    return render_template('dashboard.html', 
                         total_events=total_events,
                         upcoming_events=upcoming_events,
                         total_guests=total_guests,
                         total_bookings=total_bookings,
                         recent_events=recent_events,
                         total_budget=total_budget,
                         rsvp_stats=rsvp_stats)


# ============= EVENT ROUTES =============

@app.route('/events')
@login_required
def events_list():
    """List all events for current user"""
    events = Event.query.filter_by(user_id=session['user_id']).order_by(Event.event_date.desc()).all()
    return render_template('events/list.html', events=events)


def validate_future_date(date_str):
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        if date < datetime.now().date():
            return False, 'Error: Date must be in the future'
        return True, ''
    except ValueError:
        return False, 'Error: Invalid date format (YYYY-MM-DD)'


@app.route('/events/create', methods=['GET', 'POST'])
def event_create():
    """Create a new event"""
    if request.method == 'POST':
        # Validate date
        is_valid_date, date_error = validate_future_date(request.form['event_date'])
        if not is_valid_date:
            flash(date_error, 'error')
            return render_template('events/create.html', form_data=request.form)
            
        try:
            event = Event(
                user_id=session['user_id'],
                name=request.form['name'],
                description=request.form.get('description'),
                event_date=datetime.strptime(request.form['event_date'], '%Y-%m-%d').date(),
                event_time=datetime.strptime(request.form['event_time'], '%H:%M').time() if request.form.get('event_time') else None,
                location=request.form.get('location'),
                latitude=float(request.form.get('latitude')) if request.form.get('latitude') else None,
                longitude=float(request.form.get('longitude')) if request.form.get('longitude') else None,
                venue_capacity=int(request.form.get('venue_capacity')) if request.form.get('venue_capacity') else None,
                budget=float(request.form.get('budget', 0)),
                status=request.form.get('status', 'Planning')
            )
            db.session.add(event)
            db.session.commit()
            flash('Event created successfully!', 'success')
            return redirect(url_for('events_list'))
        except Exception as e:
            flash(f'Error creating event: {str(e)}', 'error')
            db.session.rollback()
    
    return render_template('events/create.html')


@app.route('/events/<int:id>')
def event_detail(id):
    """View event details"""
    event = Event.query.get_or_404(id)
    guests = Guest.query.filter_by(event_id=id).all()
    bookings = Booking.query.filter_by(event_id=id).all()
    
    # Calculate total booking cost
    total_booking_cost = sum([float(b.cost) for b in bookings])
    
    return render_template('events/detail.html', 
                         event=event, 
                         guests=guests, 
                         bookings=bookings,
                         total_booking_cost=total_booking_cost)


@app.route('/events/<int:id>/edit', methods=['GET', 'POST'])
def event_edit(id):
    """Edit an event"""
    event = Event.query.get_or_404(id)
    
    if request.method == 'POST':
        # Validate date
        is_valid_date, date_error = validate_future_date(request.form['event_date'])
        if not is_valid_date:
            flash(date_error, 'error')
            return render_template('events/edit.html', event=event, form_data=request.form)
            
        try:
            event.name = request.form['name']
            event.description = request.form.get('description')
            event.event_date = datetime.strptime(request.form['event_date'], '%Y-%m-%d').date()
            event.event_time = datetime.strptime(request.form['event_time'], '%H:%M').time() if request.form.get('event_time') else None
            event.location = request.form.get('location')
            event.latitude = float(request.form.get('latitude')) if request.form.get('latitude') else None
            event.longitude = float(request.form.get('longitude')) if request.form.get('longitude') else None
            event.venue_capacity = int(request.form.get('venue_capacity')) if request.form.get('venue_capacity') else None
            event.budget = float(request.form.get('budget', 0))
            event.status = request.form.get('status', 'Planning')
            
            db.session.commit()
            flash('Event updated successfully!', 'success')
            return redirect(url_for('event_detail', id=id))
        except Exception as e:
            flash(f'Error updating event: {str(e)}', 'error')
            db.session.rollback()
    
    return render_template('events/edit.html', event=event)


@app.route('/events/<int:id>/delete', methods=['POST'])
def event_delete(id):
    """Delete an event"""
    try:
        event = Event.query.get_or_404(id)
        db.session.delete(event)
        db.session.commit()
        flash('Event deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting event: {str(e)}', 'error')
        db.session.rollback()
    
    return redirect(url_for('events_list'))


# ============= GUEST ROUTES =============

@app.route('/guests')
@login_required
def guests_list():
    """List all guests for current user"""
    guests = Guest.query.filter_by(user_id=session['user_id']).order_by(Guest.created_at.desc()).all()
    return render_template('guests/list.html', guests=guests)


@app.route('/guests/<int:id>/qr')
@login_required
def view_guest_qr(id):
    """View guest QR code"""
    guest = Guest.query.get_or_404(id)
    return render_template('guests/qr_display.html', guest=guest)


@app.route('/guests/create', methods=['GET', 'POST'])
@login_required
def guest_create():
    """Create a new guest"""
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            phone = request.form.get('phone')
            event_id = int(request.form['event_id'])
            guest_count = int(request.form.get('guest_count', 1))
            
            # Validate Gmail
            if email and not validate_gmail(email):
                flash('Error: Only Gmail addresses are accepted (e.g., user@gmail.com)', 'error')
                events = Event.query.filter_by(user_id=session['user_id']).all()
                return render_template('guests/create.html', events=events)
            
            # Validate Phone
            if phone and not validate_phone(phone):
                flash('Error: Phone number must be exactly 10 digits', 'error')
                events = Event.query.filter_by(user_id=session['user_id']).all()
                return render_template('guests/create.html', events=events)
            
            # Check venue capacity
            event = Event.query.get(event_id)
            if event and event.venue_capacity:
                current_guests = db.session.query(func.sum(Guest.guest_count)).filter_by(event_id=event_id).scalar() or 0
                if current_guests + guest_count > event.venue_capacity:
                    flash(f'Error: Adding {guest_count} guests would exceed venue capacity of {event.venue_capacity}. Current guests: {current_guests}', 'error')
                    events = Event.query.filter_by(user_id=session['user_id']).all()
                    return render_template('guests/create.html', events=events)
            
            guest = Guest(
                event_id=event_id,
                user_id=session['user_id'],
                name=request.form['name'],
                email=email,
                phone=phone,
                rsvp_status=request.form.get('rsvp_status', 'Pending'),
                guest_count=guest_count,
                dietary_requirements=request.form.get('dietary_requirements')
            )
            db.session.add(guest)
            db.session.commit()
            
            # Generate QR token for the guest
            guest.qr_token = qr_service.generate_guest_token(guest.id, event_id)
            db.session.commit()
            
            # Send invitation email if email is provided
            if email:
                try:
                    host_name = session.get('user_full_name', 'Event Organizer')
                    success, message = email_service.send_guest_invitation(guest, event, host_name)
                    if success:
                        flash(f'Guest added successfully! Invitation email sent to {email}', 'success')
                    else:
                        flash(f'Guest added successfully! However, email failed to send: {message}', 'warning')
                except Exception as e:
                    flash(f'Guest added successfully! However, email failed to send: {str(e)}', 'warning')
            else:
                flash('Guest added successfully! (No email provided for invitation)', 'success')
            
            return redirect(url_for('guests_list'))
        except Exception as e:
            flash(f'Error creating guest: {str(e)}', 'error')
            db.session.rollback()
    
    # GET request - show form
    events = Event.query.filter_by(user_id=session['user_id']).all()
    return render_template('guests/create.html', events=events)


@app.route('/guests/<int:id>/edit', methods=['GET', 'POST'])
def guest_edit(id):
    """Edit a guest"""
    guest = Guest.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            phone = request.form.get('phone')
            
            # Validate Gmail
            if email and not validate_gmail(email):
                flash('Error: Only Gmail addresses are accepted (e.g., user@gmail.com)', 'error')
                events = Event.query.all()
                return render_template('guests/edit.html', guest=guest, events=events)
            
            # Validate Phone
            if phone and not validate_phone(phone):
                flash('Error: Phone number must be exactly 10 digits', 'error')
                events = Event.query.all()
                return render_template('guests/edit.html', guest=guest, events=events)
            
            guest.event_id = int(request.form['event_id'])
            guest.name = request.form['name']
            guest.email = email
            guest.phone = phone
            guest.rsvp_status = request.form.get('rsvp_status', 'Pending')
            guest.guest_count = int(request.form.get('guest_count', 1))
            guest.dietary_requirements = request.form.get('dietary_requirements')
            
            db.session.commit()
            flash('Guest updated successfully!', 'success')
            return redirect(url_for('guests_list'))
        except Exception as e:
            flash(f'Error updating guest: {str(e)}', 'error')
            db.session.rollback()
    
    events = Event.query.all()
    return render_template('guests/edit.html', guest=guest, events=events)


@app.route('/guests/<int:id>/delete', methods=['POST'])
def guest_delete(id):
    """Delete a guest"""
    try:
        guest = Guest.query.get_or_404(id)
        db.session.delete(guest)
        db.session.commit()
        flash('Guest deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting guest: {str(e)}', 'error')
        db.session.rollback()
    
    return redirect(url_for('guests_list'))


# ============= BOOKING ROUTES =============

@app.route('/bookings')
@login_required
def bookings_list():
    """List all bookings for current user"""
    bookings = Booking.query.filter_by(user_id=session['user_id']).order_by(Booking.created_at.desc()).all()
    return render_template('bookings/list.html', bookings=bookings)


@app.route('/bookings/create', methods=['GET', 'POST'])
def booking_create():
    """Create a new booking"""
    if request.method == 'POST':
        try:
            # Automatically set status to Confirmed instead of Pending
            booking = Booking(
                event_id=int(request.form['event_id']),
                user_id=session['user_id'],
                booking_type=request.form['booking_type'],
                vendor_name=request.form['vendor_name'],
                description=request.form.get('description'),
                cost=float(request.form.get('cost', 0)),
                booking_date=datetime.strptime(request.form['booking_date'], '%Y-%m-%d').date() if request.form.get('booking_date') else None,
                status='Confirmed',  # Auto-confirm bookings
                contact_info=request.form.get('contact_info'),
                notes=request.form.get('notes')
            )
            db.session.add(booking)
            db.session.commit()
            flash('Booking created and automatically confirmed!', 'success')
            return redirect(url_for('bookings_list'))
        except Exception as e:
            flash(f'Error creating booking: {str(e)}', 'error')
            db.session.rollback()
    
    events = Event.query.all()
    return render_template('bookings/create.html', events=events)


@app.route('/bookings/<int:id>/edit', methods=['GET', 'POST'])
def booking_edit(id):
    """Edit a booking"""
    booking = Booking.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            booking.event_id = int(request.form['event_id'])
            booking.booking_type = request.form['booking_type']
            booking.vendor_name = request.form['vendor_name']
            booking.description = request.form.get('description')
            booking.cost = float(request.form.get('cost', 0))
            booking.booking_date = datetime.strptime(request.form['booking_date'], '%Y-%m-%d').date() if request.form.get('booking_date') else None
            booking.status = request.form.get('status', 'Pending')
            booking.contact_info = request.form.get('contact_info')
            booking.notes = request.form.get('notes')
            
            db.session.commit()
            flash('Booking updated successfully!', 'success')
            return redirect(url_for('bookings_list'))
        except Exception as e:
            flash(f'Error updating booking: {str(e)}', 'error')
            db.session.rollback()
    
    events = Event.query.all()
    return render_template('bookings/edit.html', booking=booking, events=events)


@app.route('/bookings/<int:id>/delete', methods=['POST'])
def booking_delete(id):
    """Delete a booking"""
    try:
        booking = Booking.query.get_or_404(id)
        db.session.delete(booking)
        db.session.commit()
        flash('Booking deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting booking: {str(e)}', 'error')
        db.session.rollback()
    
    return redirect(url_for('bookings_list'))


# ============= GUEST COMMUNICATION ROUTES =============

@app.route('/send_whatsapp_invites/<int:event_id>', methods=['POST'])
@login_required
def send_whatsapp_invites(event_id):
    """Send WhatsApp invitations to all guests of an event"""
    event = Event.query.get_or_404(event_id)
    
    # Check if the user is authorized to send invites for this event
    if event.user_id != session.get('user_id'):
        flash('You do not have permission to perform this action.', 'error')
        return redirect(url_for('event_detail', id=event_id))
        
    guests = Guest.query.filter_by(event_id=event_id).all()
    
    if not guests:
        flash('No guests found for this event.', 'warning')
        return redirect(url_for('event_detail', id=event_id))
        
    sent_count = 0
    failed_count = 0
    skipped_count = 0
    
    for guest in guests:
        if not guest.phone:
            skipped_count += 1
            app.logger.warning(f"Skipped WhatsApp invite for {guest.name}: No phone number.")
            continue
            
        success, message = whatsapp_service.send_invitation(guest, event)
        if success:
            sent_count += 1
        else:
            failed_count += 1
            app.logger.error(f"Failed WhatsApp invite for {guest.name}: {message}")
            
    if sent_count > 0:
        flash(f'Successfully sent {sent_count} WhatsApp invitations.', 'success')
        
    if failed_count > 0:
        flash(f'Failed to send {failed_count} WhatsApp invitations. Check logs for details.', 'danger')
        
    if skipped_count > 0:
        flash(f'Skipped {skipped_count} guests due to missing phone numbers.', 'warning')
        
    if sent_count == 0 and failed_count == 0 and skipped_count == 0:
        flash('No invitations could be processed.', 'info')
        
    return redirect(url_for('event_detail', id=event_id))

# ============= FEATURE 1: QR CODE CHECK-IN SYSTEM =============

@app.route('/guests/<int:id>/generate-qr', methods=['GET'])
@login_required
def generate_guest_qr(id):
    """Generate QR code for guest"""
    try:
        guest = Guest.query.get_or_404(id)
        
        # Reuse the existing token if the guest already has one (e.g. sent via email).
        # Only generate a brand-new token if none exists yet.
        if not guest.qr_token:
            guest.qr_token = qr_service.generate_guest_token(guest.id, guest.event_id)
            db.session.commit()

        # Build the QR image from the *stored* token so it always matches the DB.
        qr_image, token = qr_service.generate_qr_code(
            guest_id=guest.id,
            event_id=guest.event_id,
            guest_name=guest.name,
            existing_token=guest.qr_token   # ← key fix: reuse stored token
        )

        if qr_image and token:
            
            return jsonify({
                'success': True,
                'qr_image': qr_image,
                'message': 'QR code generated successfully!'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to generate QR code'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/check-in', methods=['GET', 'POST'])
def check_in_page():
    """QR code scanner page for check-in"""
    if request.method == 'POST':
        try:
            qr_data = request.json.get('qr_data')
            
            # Verify QR code
            decoded_data = qr_service.verify_qr_code(qr_data)
            
            if not decoded_data:
                return jsonify({
                    'success': False,
                    'message': 'Invalid QR code'
                }), 400
            
            # Find guest
            guest = Guest.query.get(decoded_data['guest_id'])
            
            if not guest:
                return jsonify({
                    'success': False,
                    'message': 'Guest not found'
                }), 404
            
            # Verify token matches
            if guest.qr_token != decoded_data['token']:
                return jsonify({
                    'success': False,
                    'message': 'Invalid or expired QR code'
                }), 400
            
            # Check if already checked in
            if guest.checked_in:
                return jsonify({
                    'success': False,
                    'message': f'{guest.name} is already checked in at {guest.check_in_time.strftime("%I:%M %p")}',
                    'already_checked_in': True
                }), 400
            
            # Mark as checked in
            guest.checked_in = True
            guest.check_in_time = datetime.now()  # Local time (India timezone)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'✅ Welcome {guest.name}! Check-in successful!',
                'guest_name': guest.name,
                'event_name': guest.event.name,
                'check_in_time': guest.check_in_time.strftime('%I:%M %p')
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error: {str(e)}'
            }), 500
    
    # GET request - show scanner page
    return render_template('check_in/scanner.html')


@app.route('/guests/<int:id>/check-in-status', methods=['GET'])
@login_required
def guest_check_in_status(id):
    """Get guest check-in status"""
    try:
        guest = Guest.query.get_or_404(id)
        
        return jsonify({
            'success': True,
            'checked_in': guest.checked_in,
            'check_in_time': guest.check_in_time.strftime('%Y-%m-%d %H:%M:%S') if guest.check_in_time else None,
            'has_qr': bool(guest.qr_token)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/check-ins')
@login_required
def check_ins_list():
    """List of checked-in guests with times for the current user"""
    event_id = request.args.get('event_id', type=int)
    
    # Query user's events for the dropdown filter
    events = Event.query.filter_by(user_id=session['user_id']).all()
    
    # Base query for checked-in guests
    query = Guest.query.filter_by(user_id=session['user_id'], checked_in=True)
    
    if event_id:
        query = query.filter_by(event_id=event_id)
        total_guests = Guest.query.filter_by(user_id=session['user_id'], event_id=event_id).count()
    else:
        total_guests = Guest.query.filter_by(user_id=session['user_id']).count()
        
    checked_in_guests = query.order_by(Guest.check_in_time.desc()).all()
    total_checked_in = len(checked_in_guests)
    not_checked_in = total_guests - total_checked_in
    
    # Calculate attendance percentage
    attendance_rate = (total_checked_in / total_guests * 100) if total_guests > 0 else 0
    
    return render_template('check_in/history.html',
                           guests=checked_in_guests,
                           events=events,
                           selected_event_id=event_id,
                           total_checked_in=total_checked_in,
                           total_guests=total_guests,
                           not_checked_in=not_checked_in,
                           attendance_rate=attendance_rate)


# ============= FEATURE 3: ANALYTICS DASHBOARD =============

@app.route('/analytics')
@login_required
def analytics_dashboard():
    """Analytics dashboard with charts and statistics"""
    try:
        # Get data for current user only
        events = Event.query.filter_by(user_id=session['user_id']).all()
        guests = Guest.query.filter_by(user_id=session['user_id']).all()
        bookings = Booking.query.filter_by(user_id=session['user_id']).all()
        
        # Calculate statistics
        stats = {
            'total_events': len(events),
            'total_guests': len(guests),
            'total_bookings': len(bookings),
            'checked_in_count': len([g for g in guests if g.checked_in]),
            'rsvp_accepted': len([g for g in guests if g.rsvp_status == 'Accepted']),
            'rsvp_declined': len([g for g in guests if g.rsvp_status == 'Declined']),
            'rsvp_pending': len([g for g in guests if g.rsvp_status == 'Pending']),
            'total_budget': sum([float(e.budget) for e in events if e.budget]),
            'total_actual_cost': sum([float(b.cost) for b in bookings if b.cost])
        }
        
        # Budget breakdown by booking type
        budget_by_type = {}
        for booking in bookings:
            if booking.cost:
                booking_type = booking.booking_type or 'Other'
                budget_by_type[booking_type] = budget_by_type.get(booking_type, 0) + float(booking.cost)
        
        # Calculate remaining budget
        total_budget = stats['total_budget']
        total_spent = stats['total_actual_cost']
        remaining_budget = total_budget - total_spent
        
        # Event statistics
        event_stats = []
        for event in events:
            event_guests = [g for g in guests if g.event_id == event.id]
            event_bookings = [b for b in bookings if b.event_id == event.id]
            event_actual_cost = sum([float(b.cost) for b in event_bookings if b.cost])
            
            event_stats.append({
                'name': event.name,
                'guest_count': len(event_guests),
                'checked_in': len([g for g in event_guests if g.checked_in]),
                'accepted': len([g for g in event_guests if g.rsvp_status == 'Accepted']),
                'budget': float(event.budget) if event.budget else 0,
                'actual_cost': event_actual_cost
            })
        
        # Monthly event distribution
        from collections import defaultdict
        monthly_events = defaultdict(int)
        for event in events:
            if event.event_date:
                month_key = event.event_date.strftime('%Y-%m')
                monthly_events[month_key] += 1
        
        return render_template('analytics/dashboard.html', 
                             stats=stats, 
                             event_stats=event_stats,
                             monthly_events=dict(monthly_events),
                             budget_by_type=budget_by_type,
                             remaining_budget=remaining_budget)
        
    except Exception as e:
        flash(f'Error loading analytics: {str(e)}', 'error')
        return redirect(url_for('dashboard'))


@app.route('/analytics/api/data')
@login_required
def analytics_api():
    """API endpoint for analytics data (for AJAX updates)"""
    try:
        events = Event.query.all()
        guests = Guest.query.all()
        
        # RSVP Distribution
        rsvp_data = {
            'accepted': len([g for g in guests if g.rsvp_status == 'Accepted']),
            'declined': len([g for g in guests if g.rsvp_status == 'Declined']),
            'pending': len([g for g in guests if g.rsvp_status == 'Pending'])
        }
        
        # Check-in Rate
        checkin_data = {
            'checked_in': len([g for g in guests if g.checked_in]),
            'not_checked_in': len([g for g in guests if not g.checked_in])
        }
        
        # Guests per Event
        event_guest_data = []
        for event in events[:10]:  # Top 10 events
            guest_count = Guest.query.filter_by(event_id=event.id).count()
            event_guest_data.append({
                'event': event.name,
                'guests': guest_count
            })
        
        # Budget Analysis
        budget_data = []
        for event in events:
            if event.budget:
                budget_data.append({
                    'event': event.name,
                    'budget': float(event.budget or 0),
                    'actual': 0  # Actual cost tracking not implemented
                })
        
        return jsonify({
            'success': True,
            'rsvp': rsvp_data,
            'checkin': checkin_data,
            'event_guests': event_guest_data,
            'budget': budget_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


if __name__ == '__main__':
    app.run(debug=True, port=5001)
