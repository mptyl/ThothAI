-- Enhanced MariaDB schema for California Schools database with column comments
-- Generated from SQLite schema with descriptions from CSV files

USE california_schools;

-- Schools table (main reference table)
CREATE TABLE schools (
    CDSCode VARCHAR(15) NOT NULL PRIMARY KEY COMMENT 'CDSCode',
    NCESDist VARCHAR(20) NULL COMMENT 'This field represents the 7-digit National Center for Educational Statistics (NCES) school district identification number. The first 2 digits identify the state and the last 5 digits identify the school district. Combined, they make a unique 7-digit ID for each school district.',
    NCESSchool VARCHAR(20) NULL COMMENT 'This field represents the 5-digit NCES school identification number. The NCESSchool combined with the NCESDist form a unique 12-digit ID for each school.',
    StatusType VARCHAR(20) NOT NULL COMMENT 'This field identifies the status of the district.',
    County VARCHAR(50) NOT NULL COMMENT 'County name',
    District VARCHAR(100) NOT NULL COMMENT 'District',
    School VARCHAR(100) NULL COMMENT 'School',
    Street VARCHAR(100) NULL COMMENT 'Street',
    StreetAbr VARCHAR(100) NULL COMMENT 'The abbreviated street address of the school, district, or administrative authority’s physical location.',
    City VARCHAR(50) NULL COMMENT 'City',
    Zip VARCHAR(10) NULL COMMENT 'Zip',
    State VARCHAR(2) NULL COMMENT 'State',
    MailStreet VARCHAR(100) NULL COMMENT 'MailStreet',
    MailStrAbr VARCHAR(100) NULL,
    MailCity VARCHAR(50) NULL,
    MailZip VARCHAR(10) NULL,
    MailState VARCHAR(2) NULL,
    Phone VARCHAR(20) NULL COMMENT 'Phone',
    Ext VARCHAR(10) NULL COMMENT 'The phone number extension of the school, district, or administrative authority.',
    Website VARCHAR(255) NULL COMMENT 'The website address of the school, district, or administrative authority.',
    OpenDate DATE NULL COMMENT 'The date the school opened.',
    ClosedDate DATE NULL COMMENT 'The date the school closed.',
    Charter TINYINT NULL COMMENT 'This field identifies a charter school.',
    CharterNum VARCHAR(10) NULL COMMENT 'The charter school number,',
    FundingType VARCHAR(50) NULL COMMENT 'Indicates the charter school funding type',
    DOC VARCHAR(5) NOT NULL COMMENT 'District Ownership Code',
    DOCType VARCHAR(100) NOT NULL COMMENT 'The District Ownership Code Type is the text description of the DOC category.',
    SOC VARCHAR(5) NULL COMMENT 'The School Ownership Code is a numeric code used to identify the type of school.',
    SOCType VARCHAR(100) NULL COMMENT 'The School Ownership Code Type is the text description of the type of school.',
    EdOpsCode VARCHAR(10) NULL COMMENT 'The Education Option Code is a short text description of the type of education offered.',
    EdOpsName VARCHAR(100) NULL COMMENT 'Educational Option Name',
    EILCode VARCHAR(10) NULL COMMENT 'The Educational Instruction Level Code is a short text description of the institution\'s type relative to the grade range served.',
    EILName VARCHAR(100) NULL COMMENT 'The Educational Instruction Level Name is the long text description of the institution’s type relative to the grade range served.',
    GSoffered VARCHAR(20) NULL COMMENT 'The grade span offered is the lowest grade and the highest grade offered or supported by the school, district, or administrative authority. This field might differ from the grade span served as reported in the most recent certified California Longitudinal Pupil Achievement (CALPADS) Fall 1 data collection.',
    GSserved VARCHAR(20) NULL COMMENT 'It is the lowest grade and the highest grade of student enrollment as reported in the most recent certified CALPADS Fall 1 data collection. Only K–12 enrollment is reported through CALPADS. This field may differ from the grade span offered.',
    Virtual VARCHAR(5) NULL COMMENT 'This field identifies the type of virtual instruction offered by the school. Virtual instruction is instruction in which students and teachers are separated by time and/or location, and interaction occurs via computers and/or telecommunications technologies.',
    Magnet TINYINT NULL COMMENT 'This field identifies whether a school is a magnet school and/or provides a magnet program.',
    Latitude DECIMAL(10, 6) NULL COMMENT 'The angular distance (expressed in degrees) between the location of the school, district, or administrative authority and the equator measured north to south.',
    Longitude DECIMAL(10, 6) NULL COMMENT 'The angular distance (expressed in degrees) between the location of the school, district, or administrative authority and the prime meridian (Greenwich, England) measured from west to east.',
    AdmFName1 VARCHAR(50) NULL COMMENT 'administrator\'s first name',
    AdmLName1 VARCHAR(50) NULL COMMENT 'administrator\'s last name',
    AdmEmail1 VARCHAR(100) NULL COMMENT 'administrator\'s email address',
    AdmFName2 VARCHAR(50) NULL,
    AdmLName2 VARCHAR(50) NULL,
    AdmEmail2 VARCHAR(100) NULL,
    AdmFName3 VARCHAR(50) NULL,
    AdmLName3 VARCHAR(50) NULL,
    AdmEmail3 VARCHAR(100) NULL,
    LastUpdate DATE NOT NULL,
    INDEX idx_county (County),
    INDEX idx_district (District),
    INDEX idx_school (School),
    INDEX idx_status (StatusType),
    INDEX idx_charter (Charter),
    INDEX idx_location (Latitude, Longitude)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- FRPM (Free/Reduced Price Meal) table
CREATE TABLE frpm (
    CDSCode VARCHAR(15) NOT NULL PRIMARY KEY COMMENT 'Code of column_description',
    `Academic Year` VARCHAR(10) NULL COMMENT 'Description of Academic Year',
    `County Code` VARCHAR(5) NULL COMMENT 'County Code',
    `District Code` INT NULL COMMENT 'District Code',
    `School Code` VARCHAR(10) NULL,
    `County Name` VARCHAR(50) NULL COMMENT 'County Code',
    `District Name` VARCHAR(100) NULL,
    `School Name` VARCHAR(100) NULL COMMENT 'School Name',
    `District Type` VARCHAR(50) NULL COMMENT 'District Type',
    `School Type` VARCHAR(50) NULL,
    `Educational Option Type` VARCHAR(50) NULL COMMENT 'Educational Option Type',
    `NSLP Provision Status` VARCHAR(50) NULL COMMENT 'NSLP Provision Status',
    `Charter School (Y/N)` TINYINT NULL COMMENT 'Charter School (Y/N)',
    `Charter School Number` VARCHAR(10) NULL COMMENT 'Charter School Number',
    `Charter Funding Type` VARCHAR(50) NULL COMMENT 'Charter Funding Type',
    IRC TINYINT NULL,
    `Low Grade` VARCHAR(20) NULL COMMENT 'Low Grade',
    `High Grade` VARCHAR(20) NULL COMMENT 'High Grade',
    `Enrollment (K-12)` DECIMAL(10, 2) NULL COMMENT 'Enrollment (K-12)',
    `Free Meal Count (K-12)` DECIMAL(10, 2) NULL COMMENT 'Free Meal Count (K-12)',
    `Percent (%) Eligible Free (K-12)` DECIMAL(5, 2) NULL,
    `FRPM Count (K-12)` DECIMAL(10, 2) NULL COMMENT 'Free or Reduced Price Meal Count (K-12)',
    `Percent (%) Eligible FRPM (K-12)` DECIMAL(5, 2) NULL,
    `Enrollment (Ages 5-17)` DECIMAL(10, 2) NULL COMMENT 'Enrollment (Ages 5-17)',
    `Free Meal Count (Ages 5-17)` DECIMAL(10, 2) NULL COMMENT 'Free Meal Count (Ages 5-17)',
    `Percent (%) Eligible Free (Ages 5-17)` DECIMAL(5, 2) NULL,
    `FRPM Count (Ages 5-17)` DECIMAL(10, 2) NULL,
    `Percent (%) Eligible FRPM (Ages 5-17)` DECIMAL(5, 2) NULL,
    `2013-14 CALPADS Fall 1 Certification Status` TINYINT NULL COMMENT '2013-14 CALPADS Fall 1 Certification Status',
    FOREIGN KEY (CDSCode) REFERENCES schools(CDSCode) ON DELETE CASCADE,
    INDEX idx_county_name (`County Name`),
    INDEX idx_district_name (`District Name`),
    INDEX idx_school_name (`School Name`),
    INDEX idx_enrollment (`Enrollment (K-12)`),
    INDEX idx_frpm_percentage (`Percent (%) Eligible FRPM (K-12)`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- SAT Scores table
CREATE TABLE satscores (
    cds VARCHAR(15) NOT NULL PRIMARY KEY COMMENT 'California Department Schools',
    rtype VARCHAR(5) NOT NULL COMMENT 'rtype',
    sname VARCHAR(100) NULL COMMENT 'school name',
    dname VARCHAR(100) NULL COMMENT 'district segment',
    cname VARCHAR(50) NULL COMMENT 'county name',
    enroll12 INT NOT NULL COMMENT 'enrollment (1st-12nd grade)',
    NumTstTakr INT NOT NULL COMMENT 'Number of Test Takers in this school',
    AvgScrRead INT NULL COMMENT 'average scores in Reading',
    AvgScrMath INT NULL COMMENT 'average scores in Math',
    AvgScrWrite INT NULL COMMENT 'average scores in writing',
    NumGE1500 INT NULL COMMENT 'Number of Test Takers Whose Total SAT Scores Are Greater or Equal to 1500',
    FOREIGN KEY (cds) REFERENCES schools(CDSCode) ON DELETE CASCADE,
    INDEX idx_district_name (dname),
    INDEX idx_school_name (sname),
    INDEX idx_enrollment (enroll12),
    INDEX idx_test_takers (NumTstTakr),
    INDEX idx_avg_scores (AvgScrRead, AvgScrMath, AvgScrWrite)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create performance view for analysis
CREATE VIEW school_performance_analysis AS
SELECT 
    s.CDSCode,
    s.School,
    s.District,
    s.County,
    f.`Enrollment (K-12)` AS enrollment,
    f.`Percent (%) Eligible FRPM (K-12)` AS poverty_rate,
    sat.NumTstTakr AS sat_participants,
    ROUND((sat.AvgScrRead + sat.AvgScrMath + sat.AvgScrWrite) / 3) AS sat_composite,
    ROUND((sat.NumGE1500 / NULLIF(sat.NumTstTakr, 0)) * 100, 2) AS excellence_rate,
    CASE 
        WHEN f.`Percent (%) Eligible FRPM (K-12)` < 25 THEN 'Low Poverty'
        WHEN f.`Percent (%) Eligible FRPM (K-12)` < 50 THEN 'Medium Poverty'
        WHEN f.`Percent (%) Eligible FRPM (K-12)` < 75 THEN 'High Poverty'
        ELSE 'Very High Poverty'
    END AS poverty_level
FROM schools s
LEFT JOIN frpm f ON s.CDSCode = f.CDSCode
LEFT JOIN satscores sat ON s.CDSCode = sat.cds
WHERE s.StatusType = 'Active' 
  AND f.`Enrollment (K-12)` IS NOT NULL
  AND f.`Enrollment (K-12)` > 0;
