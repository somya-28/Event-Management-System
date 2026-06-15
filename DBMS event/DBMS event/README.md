# Nexus Event - Event Management System

A comprehensive web-based Event Planning and Management System built with Flask and MySQL.

## Features

- **Event Management**: Create, read, update, and delete events with full details
- **Guest Management**: Track guest lists with RSVP status
- **Booking Management**: Manage venue, catering, and other service bookings
- **Dashboard**: Overview with statistics and recent activities
- **Budget Tracking**: Monitor event budgets and expenses
- **Modern UI**: Clean, responsive interface using Bootstrap 5

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: MySQL with SQLAlchemy ORM
- **Frontend**: HTML, CSS, Bootstrap 5, Bootstrap Icons
- **Environment**: Python-dotenv for configuration

## Installation

### Prerequisites
- Python 3.8+
- MySQL Server
- pip (Python package manager)

### Setup Instructions

1. **Clone or navigate to the project directory**

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure MySQL Database**
   - Start MySQL server
   - Create the database and tables:
   ```bash
   mysql -u root -p < database.sql
   ```

4. **Configure Environment Variables**
   - Copy `.env.example` to `.env`
   - Update database credentials:
   ```
   DB_HOST=localhost
   DB_USER=root
   DB_PASSWORD=your_password
   DB_NAME=event_management
   SECRET_KEY=your_secret_key
   ```

5. **Run the Application**
   ```bash
   python app.py
   ```

6. **Access the Application**
   - Open your browser and go to: `http://localhost:5000`

## Project Structure

```
Nexus event/
├── app.py                  # Main Flask application
├── models.py               # Database models
├── config.py               # Configuration settings
├── database.sql            # Database schema and sample data
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── templates/             # HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── events/
│   ├── guests/
│   └── bookings/
└── README.md
```

## Usage

### Dashboard
View overview statistics including total events, guests, bookings, and RSVP status.

### Events
- Create new events with date, time, location, and budget
- Edit existing events
- View detailed event information
- Track guests and bookings per event
- Delete events (cascades to related guests and bookings)

### Guests
- Add guests to events
- Track RSVP status (Pending, Accepted, Declined)
- Manage guest count and dietary requirements
- Update guest information

### Bookings
- Create bookings for venues, catering, photography, etc.
- Track booking costs and status
- Manage vendor contact information
- Add notes for each booking

## Database Schema

- **events**: Core event information
- **guests**: Guest details and RSVP status
- **bookings**: Service bookings linked to events

## Future Enhancements

- Email notifications for RSVP
- Payment integration
- Calendar view for events
- Export functionality (PDF/Excel)
- User authentication and authorization
- Multi-user support with roles

## License

This project is created for educational purposes as part of a DBMS project demonstration.
