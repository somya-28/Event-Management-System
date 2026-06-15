-- Create Database
CREATE DATABASE IF NOT EXISTS event_management;
USE event_management;

-- Events Table
CREATE TABLE IF NOT EXISTS events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    event_date DATE NOT NULL,
    event_time TIME,
    location VARCHAR(255),
    budget DECIMAL(10, 2) DEFAULT 0.00,
    status ENUM('Planning', 'Confirmed', 'Completed', 'Cancelled') DEFAULT 'Planning',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Guests Table
CREATE TABLE IF NOT EXISTS guests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    name VARCHAR(200) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    rsvp_status ENUM('Pending', 'Accepted', 'Declined') DEFAULT 'Pending',
    guest_count INT DEFAULT 1,
    dietary_requirements TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

-- Bookings Table
CREATE TABLE IF NOT EXISTS bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    booking_type ENUM('Venue', 'Catering', 'Photography', 'Music', 'Decoration', 'Other') NOT NULL,
    vendor_name VARCHAR(200) NOT NULL,
    description TEXT,
    cost DECIMAL(10, 2) DEFAULT 0.00,
    booking_date DATE,
    status ENUM('Pending', 'Confirmed', 'Paid', 'Cancelled') DEFAULT 'Pending',
    contact_info VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX idx_event_date ON events(event_date);
CREATE INDEX idx_event_status ON events(status);
CREATE INDEX idx_guest_event ON guests(event_id);
CREATE INDEX idx_guest_rsvp ON guests(rsvp_status);
CREATE INDEX idx_booking_event ON bookings(event_id);
CREATE INDEX idx_booking_status ON bookings(status);
