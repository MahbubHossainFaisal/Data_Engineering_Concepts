



-- ============================================================
-- Snowflake DDL for Airbnb Project
-- Database: AIRBNB_DWH
-- Schema: STAGING
-- ============================================================

-- Create Database
CREATE DATABASE AIRBNB_DWH;

-- Use Database
USE DATABASE AIRBNB_DWH;

-- Create Schema
CREATE SCHEMA IF NOT EXISTS AIRBNB_DWH.STAGING;;

-- ============================================================
-- HOSTS TABLE
-- ============================================================
CREATE OR REPLACE TABLE STAGING.HOSTS (
    HOST_ID INT PRIMARY KEY,
    HOST_NAME VARCHAR(255) NOT NULL,
    HOST_SINCE DATE NOT NULL,
    IS_SUPERHOST BOOLEAN DEFAULT FALSE,
    RESPONSE_RATE INT,
    CREATED_AT TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP()
);

-- ============================================================
-- LISTINGS TABLE
-- ============================================================
CREATE OR REPLACE TABLE STAGING.LISTINGS (
    LISTING_ID INT PRIMARY KEY,
    HOST_ID INT NOT NULL,
    PROPERTY_TYPE VARCHAR(100) NOT NULL,
    ROOM_TYPE VARCHAR(100) NOT NULL,
    CITY VARCHAR(255) NOT NULL,
    COUNTRY VARCHAR(100) NOT NULL,
    ACCOMMODATES INT,
    BEDROOMS INT,
    BATHROOMS INT,
    PRICE_PER_NIGHT DECIMAL(10, 2) NOT NULL,
    CREATED_AT TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP()
);

-- ============================================================
-- BOOKINGS TABLE
-- ============================================================
CREATE OR REPLACE TABLE STAGING.BOOKINGS (
    BOOKING_ID VARCHAR(255) PRIMARY KEY,
    LISTING_ID INT NOT NULL,
    BOOKING_DATE DATE NOT NULL,
    NIGHTS_BOOKED INT NOT NULL,
    BOOKING_AMOUNT DECIMAL(10, 2) NOT NULL,
    CLEANING_FEE DECIMAL(10, 2),
    SERVICE_FEE DECIMAL(10, 2),
    BOOKING_STATUS VARCHAR(50) NOT NULL,
    CREATED_AT TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP()
);

-- ============================================================
-- INDEXES (Optional - Improve Query Performance)
-- ============================================================
CREATE INDEX IF NOT EXISTS IDX_BOOKINGS_LISTING_ID ON STAGING.BOOKINGS(LISTING_ID);
CREATE INDEX IF NOT EXISTS IDX_BOOKINGS_BOOKING_DATE ON STAGING.BOOKINGS(BOOKING_DATE);
CREATE INDEX IF NOT EXISTS IDX_BOOKINGS_STATUS ON STAGING.BOOKINGS(BOOKING_STATUS);
CREATE INDEX IF NOT EXISTS IDX_LISTINGS_HOST_ID ON STAGING.LISTINGS(HOST_ID);
CREATE INDEX IF NOT EXISTS IDX_LISTINGS_CITY ON STAGING.LISTINGS(CITY);

-- ============================================================
-- VERIFY TABLE CREATION
-- ============================================================
DESCRIBE TABLE STAGING.HOSTS;
DESCRIBE TABLE STAGING.LISTINGS;
DESCRIBE TABLE STAGING.BOOKINGS;
