-- Oracle schema for California Schools database with column comments
-- Generated from SQLite schema with descriptions from CSV files

-- Schools table (main reference table)
CREATE TABLE schools (
    CDSCode VARCHAR2(15) NOT NULL PRIMARY KEY,
    NCESDist VARCHAR2(20),
    NCESSchool VARCHAR2(20),
    StatusType VARCHAR2(20) NOT NULL,
    County VARCHAR2(50) NOT NULL,
    District VARCHAR2(100) NOT NULL,
    School VARCHAR2(100),
    Street VARCHAR2(100),
    StreetAbr VARCHAR2(100),
    City VARCHAR2(50),
    Zip VARCHAR2(10),
    State VARCHAR2(2),
    MailStreet VARCHAR2(100),
    MailStrAbr VARCHAR2(100),
    MailCity VARCHAR2(50),
    MailZip VARCHAR2(10),
    MailState VARCHAR2(2),
    Phone VARCHAR2(20),
    Ext VARCHAR2(10),
    Website VARCHAR2(255),
    OpenDate DATE,
    ClosedDate DATE,
    Charter NUMBER(1),
    CharterNum VARCHAR2(10),
    FundingType VARCHAR2(50),
    DOC VARCHAR2(5) NOT NULL,
    DOCType VARCHAR2(100) NOT NULL,
    SOC VARCHAR2(5),
    SOCType VARCHAR2(100),
    EdOpsCode VARCHAR2(10),
    EdOpsName VARCHAR2(100),
    EILCode VARCHAR2(10),
    EILName VARCHAR2(100),
    GSoffered VARCHAR2(20),
    GSserved VARCHAR2(20),
    Virtual VARCHAR2(5),
    Magnet NUMBER(1),
    Latitude NUMBER(10, 6),
    Longitude NUMBER(10, 6),
    AdmFName1 VARCHAR2(50),
    AdmLName1 VARCHAR2(50),
    AdmEmail1 VARCHAR2(100),
    AdmFName2 VARCHAR2(50),
    AdmLName2 VARCHAR2(50),
    AdmEmail2 VARCHAR2(100),
    AdmFName3 VARCHAR2(50),
    AdmLName3 VARCHAR2(50),
    AdmEmail3 VARCHAR2(100),
    LastUpdate DATE NOT NULL
);

-- Create indexes for schools table
CREATE INDEX IX_schools_county ON schools(County);
CREATE INDEX IX_schools_district ON schools(District);
CREATE INDEX IX_schools_school ON schools(School);
CREATE INDEX IX_schools_status ON schools(StatusType);
CREATE INDEX IX_schools_charter ON schools(Charter);
CREATE INDEX IX_schools_location ON schools(Latitude, Longitude);

-- FRPM (Free/Reduced Price Meal) table
CREATE TABLE frpm (
    CDSCode VARCHAR2(15) NOT NULL PRIMARY KEY,
    "Academic Year" VARCHAR2(10),
    "County Code" VARCHAR2(5),
    "District Code" NUMBER,
    "School Code" VARCHAR2(10),
    "County Name" VARCHAR2(50),
    "District Name" VARCHAR2(100),
    "School Name" VARCHAR2(100),
    "District Type" VARCHAR2(50),
    "School Type" VARCHAR2(50),
    "Educational Option Type" VARCHAR2(50),
    "NSLP Provision Status" VARCHAR2(50),
    "Charter School (Y/N)" NUMBER(1),
    "Charter School Number" VARCHAR2(10),
    "Charter Funding Type" VARCHAR2(50),
    IRC NUMBER(1),
    "Low Grade" VARCHAR2(20),
    "High Grade" VARCHAR2(20),
    "Enrollment (K-12)" NUMBER(10, 2),
    "Free Meal Count (K-12)" NUMBER(10, 2),
    "Percent (%) Eligible Free (K-12)" NUMBER(5, 2),
    "FRPM Count (K-12)" NUMBER(10, 2),
    "Percent (%) Eligible FRPM (K-12)" NUMBER(5, 2),
    "Enrollment (Ages 5-17)" NUMBER(10, 2),
    "Free Meal Count (Ages 5-17)" NUMBER(10, 2),
    "Percent (%) Eligible Free (Ages 5-17)" NUMBER(5, 2),
    "FRPM Count (Ages 5-17)" NUMBER(10, 2),
    "Percent (%) Eligible FRPM (Ages 5-17)" NUMBER(5, 2),
    "2013-14 CALPADS Fall 1 Certification Status" NUMBER(1),
    FOREIGN KEY (CDSCode) REFERENCES schools(CDSCode) ON DELETE CASCADE
);

-- Create indexes for frpm table
CREATE INDEX IX_frpm_county_name ON frpm("County Name");
CREATE INDEX IX_frpm_district_name ON frpm("District Name");
CREATE INDEX IX_frpm_school_name ON frpm("School Name");
CREATE INDEX IX_frpm_enrollment ON frpm("Enrollment (K-12)");
CREATE INDEX IX_frpm_percentage ON frpm("Percent (%) Eligible FRPM (K-12)");

-- SAT Scores table
CREATE TABLE satscores (
    cds VARCHAR2(15) NOT NULL PRIMARY KEY,
    rtype VARCHAR2(5) NOT NULL,
    sname VARCHAR2(100),
    dname VARCHAR2(100),
    cname VARCHAR2(50),
    enroll12 NUMBER NOT NULL,
    NumTstTakr NUMBER NOT NULL,
    AvgScrRead NUMBER,
    AvgScrMath NUMBER,
    AvgScrWrite NUMBER,
    NumGE1500 NUMBER,
    FOREIGN KEY (cds) REFERENCES schools(CDSCode) ON DELETE CASCADE
);

-- Create indexes for satscores table
CREATE INDEX IX_satscores_district_name ON satscores(dname);
CREATE INDEX IX_satscores_school_name ON satscores(sname);
CREATE INDEX IX_satscores_enrollment ON satscores(enroll12);
CREATE INDEX IX_satscores_test_takers ON satscores(NumTstTakr);
CREATE INDEX IX_satscores_avg_scores ON satscores(AvgScrRead, AvgScrMath, AvgScrWrite);

-- Create performance view for analysis
CREATE VIEW school_performance_analysis AS
SELECT 
    s.CDSCode,
    s.School,
    s.District,
    s.County,
    f."Enrollment (K-12)" AS enrollment,
    f."Percent (%) Eligible FRPM (K-12)" AS poverty_rate,
    sat.NumTstTakr AS sat_participants,
    ROUND((sat.AvgScrRead + sat.AvgScrMath + sat.AvgScrWrite) / 3, 0) AS sat_composite,
    ROUND((sat.NumGE1500 / NULLIF(sat.NumTstTakr, 0)) * 100, 2) AS excellence_rate,
    CASE 
        WHEN f."Percent (%) Eligible FRPM (K-12)" < 25 THEN 'Low Poverty'
        WHEN f."Percent (%) Eligible FRPM (K-12)" < 50 THEN 'Medium Poverty'
        WHEN f."Percent (%) Eligible FRPM (K-12)" < 75 THEN 'High Poverty'
        ELSE 'Very High Poverty'
    END AS poverty_level
FROM schools s
LEFT JOIN frpm f ON s.CDSCode = f.CDSCode
LEFT JOIN satscores sat ON s.CDSCode = sat.cds
WHERE s.StatusType = 'Active' 
  AND f."Enrollment (K-12)" IS NOT NULL
  AND f."Enrollment (K-12)" > 0;

-- Add column comments for schools table
COMMENT ON COLUMN schools.CDSCode IS 'CDSCode';
COMMENT ON COLUMN schools.NCESDist IS 'This field represents the 7-digit National Center for Educational Statistics (NCES) school district identification number. The first 2 digits identify the state and the last 5 digits identify the school district. Combined, they make a unique 7-digit ID for each school district.';
COMMENT ON COLUMN schools.NCESSchool IS 'This field represents the 5-digit NCES school identification number. The NCESSchool combined with the NCESDist form a unique 12-digit ID for each school.';
COMMENT ON COLUMN schools.StatusType IS 'This field identifies the status of the district.';
COMMENT ON COLUMN schools.County IS 'County name';
COMMENT ON COLUMN schools.District IS 'District';
COMMENT ON COLUMN schools.School IS 'School';
COMMENT ON COLUMN schools.Street IS 'Street';
COMMENT ON COLUMN schools.StreetAbr IS 'The abbreviated street address of the school, district, or administrative authority’s physical location.';
COMMENT ON COLUMN schools.City IS 'City';
COMMENT ON COLUMN schools.Zip IS 'Zip';
COMMENT ON COLUMN schools.State IS 'State';
COMMENT ON COLUMN schools.MailStreet IS 'MailStreet';
COMMENT ON COLUMN schools.Phone IS 'Phone';
COMMENT ON COLUMN schools.Ext IS 'The phone number extension of the school, district, or administrative authority.';
COMMENT ON COLUMN schools.Website IS 'The website address of the school, district, or administrative authority.';
COMMENT ON COLUMN schools.OpenDate IS 'The date the school opened.';
COMMENT ON COLUMN schools.ClosedDate IS 'The date the school closed.';
COMMENT ON COLUMN schools.Charter IS 'This field identifies a charter school.';
COMMENT ON COLUMN schools.CharterNum IS 'The charter school number,';
COMMENT ON COLUMN schools.FundingType IS 'Indicates the charter school funding type';
COMMENT ON COLUMN schools.DOC IS 'District Ownership Code';
COMMENT ON COLUMN schools.DOCType IS 'The District Ownership Code Type is the text description of the DOC category.';
COMMENT ON COLUMN schools.SOC IS 'The School Ownership Code is a numeric code used to identify the type of school.';
COMMENT ON COLUMN schools.SOCType IS 'The School Ownership Code Type is the text description of the type of school.';
COMMENT ON COLUMN schools.EdOpsCode IS 'The Education Option Code is a short text description of the type of education offered.';
COMMENT ON COLUMN schools.EdOpsName IS 'Educational Option Name';
COMMENT ON COLUMN schools.EILCode IS 'The Educational Instruction Level Code is a short text description of the institution''s type relative to the grade range served.';
COMMENT ON COLUMN schools.EILName IS 'The Educational Instruction Level Name is the long text description of the institution’s type relative to the grade range served.';
COMMENT ON COLUMN schools.GSoffered IS 'The grade span offered is the lowest grade and the highest grade offered or supported by the school, district, or administrative authority. This field might differ from the grade span served as reported in the most recent certified California Longitudinal Pupil Achievement (CALPADS) Fall 1 data collection.';
COMMENT ON COLUMN schools.GSserved IS 'It is the lowest grade and the highest grade of student enrollment as reported in the most recent certified CALPADS Fall 1 data collection. Only K–12 enrollment is reported through CALPADS. This field may differ from the grade span offered.';
COMMENT ON COLUMN schools.Virtual IS 'This field identifies the type of virtual instruction offered by the school. Virtual instruction is instruction in which students and teachers are separated by time and/or location, and interaction occurs via computers and/or telecommunications technologies.';
COMMENT ON COLUMN schools.Magnet IS 'This field identifies whether a school is a magnet school and/or provides a magnet program.';
COMMENT ON COLUMN schools.Latitude IS 'The angular distance (expressed in degrees) between the location of the school, district, or administrative authority and the equator measured north to south.';
COMMENT ON COLUMN schools.Longitude IS 'The angular distance (expressed in degrees) between the location of the school, district, or administrative authority and the prime meridian (Greenwich, England) measured from west to east.';
COMMENT ON COLUMN schools.AdmFName1 IS 'administrator''s first name';
COMMENT ON COLUMN schools.AdmLName1 IS 'administrator''s last name';
COMMENT ON COLUMN schools.AdmEmail1 IS 'administrator''s email address';

-- Add column comments for frpm table
COMMENT ON COLUMN frpm.CDSCode IS 'Code of column_description';
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
COMMENT ON COLUMN satscores.cds IS 'California Department Schools';
COMMENT ON COLUMN satscores.rtype IS 'rtype';
COMMENT ON COLUMN satscores.sname IS 'school name';
COMMENT ON COLUMN satscores.dname IS 'district segment';
COMMENT ON COLUMN satscores.cname IS 'county name';
COMMENT ON COLUMN satscores.enroll12 IS 'enrollment (1st-12nd grade)';
COMMENT ON COLUMN satscores.NumTstTakr IS 'Number of Test Takers in this school';
COMMENT ON COLUMN satscores.AvgScrRead IS 'average scores in Reading';
COMMENT ON COLUMN satscores.AvgScrMath IS 'average scores in Math';
COMMENT ON COLUMN satscores.AvgScrWrite IS 'average scores in writing';
COMMENT ON COLUMN satscores.NumGE1500 IS 'Number of Test Takers Whose Total SAT Scores Are Greater or Equal to 1500';

-- Commit the changes
COMMIT;
