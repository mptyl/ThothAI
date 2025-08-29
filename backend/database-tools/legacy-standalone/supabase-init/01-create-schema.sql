-- Supabase PostgreSQL schema for California Schools database with column comments
-- Generated from SQLite schema with descriptions from CSV files
--
-- AUTHENTICATION SETUP FOR EXTERNAL DATABASE CLIENTS (DBeaver, pgAdmin, etc.)
-- ========================================================================
--
-- This script creates the necessary user authentication for external database clients.
-- Supabase containers initially only have 'supabase_admin' user, but external clients
-- typically expect a 'thoth_user' for consistency with other database setups.
--
-- Connection Parameters for DBeaver/pgAdmin:
-- - Host: localhost
-- - Port: 5435 (Supabase container)
-- - Username: thoth_user
-- - Password: thoth_password
-- - Database: california_schools (or european_football_2, formula_1)
--
-- Alternative Admin Connection:
-- - Username: supabase_admin
-- - Password: thoth_password
--
-- Authentication Notes:
-- - External connections use SCRAM-SHA-256 authentication
-- - Local container connections use trust authentication
-- - Row Level Security (RLS) is enabled on all tables
-- - Mixed-case column names require double quotes in queries

-- STEP 1: Create thoth_user for external database client connections
-- This user provides compatibility with standard PostgreSQL client expectations
-- Run this in the 'postgres' database as supabase_admin:
-- CREATE USER thoth_user WITH PASSWORD 'thoth_password' CREATEDB LOGIN;

-- STEP 2: Grant database connection permissions
-- Run these in the 'postgres' database as supabase_admin:
-- GRANT CONNECT ON DATABASE california_schools TO thoth_user;
-- GRANT CONNECT ON DATABASE european_football_2 TO thoth_user;
-- GRANT CONNECT ON DATABASE formula_1 TO thoth_user;

-- Enable Supabase-like extensions (available in standard PostgreSQL)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create auth schema for Supabase compatibility
CREATE SCHEMA IF NOT EXISTS auth;

-- Add some Supabase-style functions for compatibility
CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid AS $$
  SELECT uuid_generate_v4()
$$ LANGUAGE sql STABLE;

-- Schools table (main reference table)
CREATE TABLE schools (
    "CDSCode" VARCHAR(15) NOT NULL PRIMARY KEY,
    "NCESDist" VARCHAR(20),
    "NCESSchool" VARCHAR(20),
    "StatusType" VARCHAR(20) NOT NULL,
    "County" VARCHAR(50) NOT NULL,
    "District" VARCHAR(100) NOT NULL,
    "School" VARCHAR(100),
    "Street" VARCHAR(100),
    "StreetAbr" VARCHAR(100),
    "City" VARCHAR(50),
    "Zip" VARCHAR(10),
    "State" VARCHAR(2),
    "MailStreet" VARCHAR(100),
    "MailStrAbr" VARCHAR(100),
    "MailCity" VARCHAR(50),
    "MailZip" VARCHAR(10),
    "MailState" VARCHAR(2),
    "Phone" VARCHAR(20),
    "Ext" VARCHAR(10),
    "Website" VARCHAR(255),
    "OpenDate" DATE,
    "ClosedDate" DATE,
    "Charter" SMALLINT,
    "CharterNum" VARCHAR(10),
    "FundingType" VARCHAR(50),
    "DOC" VARCHAR(5) NOT NULL,
    "DOCType" VARCHAR(100) NOT NULL,
    "SOC" VARCHAR(5),
    "SOCType" VARCHAR(100),
    "EdOpsCode" VARCHAR(10),
    "EdOpsName" VARCHAR(100),
    "EILCode" VARCHAR(10),
    "EILName" VARCHAR(100),
    "GSoffered" VARCHAR(20),
    "GSserved" VARCHAR(20),
    "Virtual" VARCHAR(5),
    "Magnet" SMALLINT,
    "Latitude" DECIMAL(10, 6),
    "Longitude" DECIMAL(10, 6),
    "AdmFName1" VARCHAR(50),
    "AdmLName1" VARCHAR(50),
    "AdmEmail1" VARCHAR(100),
    "AdmFName2" VARCHAR(50),
    "AdmLName2" VARCHAR(50),
    "AdmEmail2" VARCHAR(100),
    "AdmFName3" VARCHAR(50),
    "AdmLName3" VARCHAR(50),
    "AdmEmail3" VARCHAR(100),
    "LastUpdate" DATE NOT NULL
);

-- Create indexes for schools table
CREATE INDEX idx_schools_county ON schools("County");
CREATE INDEX idx_schools_district ON schools("District");
CREATE INDEX idx_schools_school ON schools("School");
CREATE INDEX idx_schools_status ON schools("StatusType");
CREATE INDEX idx_schools_charter ON schools("Charter");
CREATE INDEX idx_schools_location ON schools("Latitude", "Longitude");

-- FRPM (Free/Reduced Price Meal) table
CREATE TABLE frpm (
    "CDSCode" VARCHAR(15) NOT NULL PRIMARY KEY,
    "Academic Year" VARCHAR(10),
    "County Code" VARCHAR(5),
    "District Code" INTEGER,
    "School Code" VARCHAR(10),
    "County Name" VARCHAR(50),
    "District Name" VARCHAR(100),
    "School Name" VARCHAR(100),
    "District Type" VARCHAR(50),
    "School Type" VARCHAR(50),
    "Educational Option Type" VARCHAR(50),
    "NSLP Provision Status" VARCHAR(50),
    "Charter School (Y/N)" SMALLINT,
    "Charter School Number" VARCHAR(10),
    "Charter Funding Type" VARCHAR(50),
    "IRC" SMALLINT,
    "Low Grade" VARCHAR(20),
    "High Grade" VARCHAR(20),
    "Enrollment (K-12)" DECIMAL(10, 2),
    "Free Meal Count (K-12)" DECIMAL(10, 2),
    "Percent (%) Eligible Free (K-12)" DECIMAL(5, 2),
    "FRPM Count (K-12)" DECIMAL(10, 2),
    "Percent (%) Eligible FRPM (K-12)" DECIMAL(5, 2),
    "Enrollment (Ages 5-17)" DECIMAL(10, 2),
    "Free Meal Count (Ages 5-17)" DECIMAL(10, 2),
    "Percent (%) Eligible Free (Ages 5-17)" DECIMAL(5, 2),
    "FRPM Count (Ages 5-17)" DECIMAL(10, 2),
    "Percent (%) Eligible FRPM (Ages 5-17)" DECIMAL(5, 2),
    "2013-14 CALPADS Fall 1 Certification Status" SMALLINT,
    FOREIGN KEY ("CDSCode") REFERENCES schools("CDSCode") ON DELETE CASCADE
);

-- Create indexes for frpm table
CREATE INDEX idx_frpm_county_name ON frpm("County Name");
CREATE INDEX idx_frpm_district_name ON frpm("District Name");
CREATE INDEX idx_frpm_school_name ON frpm("School Name");
CREATE INDEX idx_frpm_enrollment ON frpm("Enrollment (K-12)");
CREATE INDEX idx_frpm_percentage ON frpm("Percent (%) Eligible FRPM (K-12)");

-- SAT Scores table
CREATE TABLE satscores (
    "cds" VARCHAR(15) NOT NULL PRIMARY KEY,
    "rtype" VARCHAR(5) NOT NULL,
    "sname" VARCHAR(100),
    "dname" VARCHAR(100),
    "cname" VARCHAR(50),
    "enroll12" INTEGER NOT NULL,
    "NumTstTakr" INTEGER NOT NULL,
    "AvgScrRead" INTEGER,
    "AvgScrMath" INTEGER,
    "AvgScrWrite" INTEGER,
    "NumGE1500" INTEGER,
    FOREIGN KEY ("cds") REFERENCES schools("CDSCode") ON DELETE CASCADE
);

-- Create indexes for satscores table
CREATE INDEX idx_satscores_district_name ON satscores("dname");
CREATE INDEX idx_satscores_school_name ON satscores("sname");
CREATE INDEX idx_satscores_enrollment ON satscores("enroll12");
CREATE INDEX idx_satscores_test_takers ON satscores("NumTstTakr");
CREATE INDEX idx_satscores_avg_scores ON satscores("AvgScrRead", "AvgScrMath", "AvgScrWrite");

-- Create performance view for analysis
CREATE VIEW school_performance_analysis AS
SELECT 
    s."CDSCode",
    s."School",
    s."District",
    s."County",
    f."Enrollment (K-12)" AS enrollment,
    f."Percent (%) Eligible FRPM (K-12)" AS poverty_rate,
    sat."NumTstTakr" AS sat_participants,
    ROUND((sat."AvgScrRead" + sat."AvgScrMath" + sat."AvgScrWrite") / 3.0)::INTEGER AS sat_composite,
    ROUND(((sat."NumGE1500"::FLOAT / NULLIF(sat."NumTstTakr", 0)) * 100)::NUMERIC, 2) AS excellence_rate,
    CASE 
        WHEN f."Percent (%) Eligible FRPM (K-12)" < 25 THEN 'Low Poverty'
        WHEN f."Percent (%) Eligible FRPM (K-12)" < 50 THEN 'Medium Poverty'
        WHEN f."Percent (%) Eligible FRPM (K-12)" < 75 THEN 'High Poverty'
        ELSE 'Very High Poverty'
    END AS poverty_level
FROM schools s
LEFT JOIN frpm f ON s."CDSCode" = f."CDSCode"
LEFT JOIN satscores sat ON s."CDSCode" = sat."cds"
WHERE s."StatusType" = 'Active' 
  AND f."Enrollment (K-12)" IS NOT NULL
  AND f."Enrollment (K-12)" > 0;

-- Enable Row Level Security for Supabase
ALTER TABLE schools ENABLE ROW LEVEL SECURITY;
ALTER TABLE frpm ENABLE ROW LEVEL SECURITY;
ALTER TABLE satscores ENABLE ROW LEVEL SECURITY;

-- Create policies to allow read access to all users
CREATE POLICY "Allow read access to schools" ON schools FOR SELECT USING (true);
CREATE POLICY "Allow read access to frpm" ON frpm FOR SELECT USING (true);
CREATE POLICY "Allow read access to satscores" ON satscores FOR SELECT USING (true);

-- Add column comments for schools table
COMMENT ON COLUMN schools."CDSCode" IS 'CDSCode';
COMMENT ON COLUMN schools."NCESDist" IS 'This field represents the 7-digit National Center for Educational Statistics (NCES) school district identification number. The first 2 digits identify the state and the last 5 digits identify the school district. Combined, they make a unique 7-digit ID for each school district.';
COMMENT ON COLUMN schools."NCESSchool" IS 'This field represents the 5-digit NCES school identification number. The NCESSchool combined with the NCESDist form a unique 12-digit ID for each school.';
COMMENT ON COLUMN schools."StatusType" IS 'This field identifies the status of the district.';
COMMENT ON COLUMN schools."County" IS 'County name';
COMMENT ON COLUMN schools."District" IS 'District';
COMMENT ON COLUMN schools."School" IS 'School';
COMMENT ON COLUMN schools."Street" IS 'Street';
COMMENT ON COLUMN schools."StreetAbr" IS 'The abbreviated street address of the school, district, or administrative authority’s physical location.';
COMMENT ON COLUMN schools."City" IS 'City';
COMMENT ON COLUMN schools."Zip" IS 'Zip';
COMMENT ON COLUMN schools."State" IS 'State';
COMMENT ON COLUMN schools."MailStreet" IS 'MailStreet';
COMMENT ON COLUMN schools."Phone" IS 'Phone';
COMMENT ON COLUMN schools."Ext" IS 'The phone number extension of the school, district, or administrative authority.';
COMMENT ON COLUMN schools."Website" IS 'The website address of the school, district, or administrative authority.';
COMMENT ON COLUMN schools."OpenDate" IS 'The date the school opened.';
COMMENT ON COLUMN schools."ClosedDate" IS 'The date the school closed.';
COMMENT ON COLUMN schools."Charter" IS 'This field identifies a charter school.';
COMMENT ON COLUMN schools."CharterNum" IS 'The charter school number,';
COMMENT ON COLUMN schools."FundingType" IS 'Indicates the charter school funding type';
COMMENT ON COLUMN schools."DOC" IS 'District Ownership Code';
COMMENT ON COLUMN schools."DOCType" IS 'The District Ownership Code Type is the text description of the DOC category.';
COMMENT ON COLUMN schools."SOC" IS 'The School Ownership Code is a numeric code used to identify the type of school.';
COMMENT ON COLUMN schools."SOCType" IS 'The School Ownership Code Type is the text description of the type of school.';
COMMENT ON COLUMN schools."EdOpsCode" IS 'The Education Option Code is a short text description of the type of education offered.';
COMMENT ON COLUMN schools."EdOpsName" IS 'Educational Option Name';
COMMENT ON COLUMN schools."EILCode" IS 'The Educational Instruction Level Code is a short text description of the institution''s type relative to the grade range served.';
COMMENT ON COLUMN schools."EILName" IS 'The Educational Instruction Level Name is the long text description of the institution’s type relative to the grade range served.';
COMMENT ON COLUMN schools."GSoffered" IS 'The grade span offered is the lowest grade and the highest grade offered or supported by the school, district, or administrative authority. This field might differ from the grade span served as reported in the most recent certified California Longitudinal Pupil Achievement (CALPADS) Fall 1 data collection.';
COMMENT ON COLUMN schools."GSserved" IS 'It is the lowest grade and the highest grade of student enrollment as reported in the most recent certified CALPADS Fall 1 data collection. Only K–12 enrollment is reported through CALPADS. This field may differ from the grade span offered.';
COMMENT ON COLUMN schools."Virtual" IS 'This field identifies the type of virtual instruction offered by the school. Virtual instruction is instruction in which students and teachers are separated by time and/or location, and interaction occurs via computers and/or telecommunications technologies.';
COMMENT ON COLUMN schools."Magnet" IS 'This field identifies whether a school is a magnet school and/or provides a magnet program.';
COMMENT ON COLUMN schools."Latitude" IS 'The angular distance (expressed in degrees) between the location of the school, district, or administrative authority and the equator measured north to south.';
COMMENT ON COLUMN schools."Longitude" IS 'The angular distance (expressed in degrees) between the location of the school, district, or administrative authority and the prime meridian (Greenwich, England) measured from west to east.';
COMMENT ON COLUMN schools."AdmFName1" IS 'administrator''s first name';
COMMENT ON COLUMN schools."AdmLName1" IS 'administrator''s last name';
COMMENT ON COLUMN schools."AdmEmail1" IS 'administrator''s email address';

-- Add column comments for frpm table
COMMENT ON COLUMN frpm."CDSCode" IS 'Code of column_description';
COMMENT ON COLUMN frpm."Academic Year" IS 'Description of Academic Year';
COMMENT ON COLUMN frpm."County Code" IS 'County Code';
COMMENT ON COLUMN frpm."District Code" IS 'District Code';
COMMENT ON COLUMN frpm."School Code" IS 'School Code';
COMMENT ON COLUMN frpm."County Name" IS 'County Code';
COMMENT ON COLUMN frpm."District Name" IS 'District Name';
COMMENT ON COLUMN frpm."School Name" IS 'School Name';
COMMENT ON COLUMN frpm."District Type" IS 'District Type';
COMMENT ON COLUMN frpm."School Type" IS 'School Type';
COMMENT ON COLUMN frpm."Educational Option Type" IS 'Educational Option Type';
COMMENT ON COLUMN frpm."NSLP Provision Status" IS 'NSLP Provision Status';
COMMENT ON COLUMN frpm."Charter School (Y/N)" IS 'Charter School (Y/N)';
COMMENT ON COLUMN frpm."Charter School Number" IS 'Charter School Number';
COMMENT ON COLUMN frpm."Charter Funding Type" IS 'Charter Funding Type';
COMMENT ON COLUMN frpm."Low Grade" IS 'Low Grade';
COMMENT ON COLUMN frpm."High Grade" IS 'High Grade';
COMMENT ON COLUMN frpm."Enrollment (K-12)" IS 'Enrollment (K-12)';
COMMENT ON COLUMN frpm."Free Meal Count (K-12)" IS 'Free Meal Count (K-12)';
COMMENT ON COLUMN frpm."FRPM Count (K-12)" IS 'Free or Reduced Price Meal Count (K-12)';
COMMENT ON COLUMN frpm."Enrollment (Ages 5-17)" IS 'Enrollment (Ages 5-17)';
COMMENT ON COLUMN frpm."Free Meal Count (Ages 5-17)" IS 'Free Meal Count (Ages 5-17)';
COMMENT ON COLUMN frpm."2013-14 CALPADS Fall 1 Certification Status" IS '2013-14 CALPADS Fall 1 Certification Status';

-- Add column comments for satscores table
COMMENT ON COLUMN satscores."cds" IS 'California Department Schools';
COMMENT ON COLUMN satscores."rtype" IS 'rtype';
COMMENT ON COLUMN satscores."sname" IS 'school name';
COMMENT ON COLUMN satscores."dname" IS 'district segment';
COMMENT ON COLUMN satscores."cname" IS 'county name';
COMMENT ON COLUMN satscores."enroll12" IS 'enrollment (1st-12nd grade)';
COMMENT ON COLUMN satscores."NumTstTakr" IS 'Number of Test Takers in this school';
COMMENT ON COLUMN satscores."AvgScrRead" IS 'average scores in Reading';
COMMENT ON COLUMN satscores."AvgScrMath" IS 'average scores in Math';
COMMENT ON COLUMN satscores."AvgScrWrite" IS 'average scores in writing';
COMMENT ON COLUMN satscores."NumGE1500" IS 'Number of Test Takers Whose Total SAT Scores Are Greater or Equal to 1500';

-- STEP 3: Grant schema and table permissions to thoth_user
-- Run these commands in each database (california_schools, european_football_2, formula_1)
-- as supabase_admin after creating the tables:

-- Grant schema usage permissions
GRANT USAGE ON SCHEMA public TO thoth_user;

-- Grant table permissions (SELECT, INSERT, UPDATE, DELETE)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO thoth_user;

-- Grant sequence permissions for auto-increment columns
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO thoth_user;

-- Grant permissions on future tables (for tables created later)
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO thoth_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO thoth_user;

-- AUTHENTICATION TROUBLESHOOTING NOTES:
-- =====================================
--
-- If you encounter "password authentication failed for user 'thoth_user'":
-- 1. Verify the user exists: SELECT rolname FROM pg_roles WHERE rolname = 'thoth_user';
-- 2. Check authentication method in pg_hba.conf (should be scram-sha-256 for external connections)
-- 3. Ensure the password is correct: 'thoth_password'
-- 4. For DBeaver connections, use host 'localhost', port 5435
--
-- If you encounter permission denied errors:
-- 1. Verify database connection grants: SELECT has_database_privilege('thoth_user', 'california_schools', 'CONNECT');
-- 2. Check table permissions: SELECT has_table_privilege('thoth_user', 'frpm', 'SELECT');
-- 3. Ensure schema usage: SELECT has_schema_privilege('thoth_user', 'public', 'USAGE');
--
-- Mixed-case column names (like "Academic Year") must be quoted in queries:
-- SELECT "Academic Year", "County Name" FROM frpm WHERE "School Name" LIKE '%Elementary%';
--
-- Row Level Security (RLS) is enabled on all tables with permissive policies for immediate access.
-- You can customize these policies later for more granular security control.
