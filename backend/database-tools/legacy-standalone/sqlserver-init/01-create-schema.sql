-- SQL Server schema for California Schools database with extended properties
-- Generated from SQLite schema with descriptions from CSV files

USE california_schools;
GO

-- Schools table (main reference table)
CREATE TABLE schools (
    CDSCode NVARCHAR(15) NOT NULL PRIMARY KEY,
    NCESDist NVARCHAR(20) NULL,
    NCESSchool NVARCHAR(20) NULL,
    StatusType NVARCHAR(20) NOT NULL,
    County NVARCHAR(50) NOT NULL,
    District NVARCHAR(100) NOT NULL,
    School NVARCHAR(100) NULL,
    Street NVARCHAR(100) NULL,
    StreetAbr NVARCHAR(100) NULL,
    City NVARCHAR(50) NULL,
    Zip NVARCHAR(10) NULL,
    State NVARCHAR(2) NULL,
    MailStreet NVARCHAR(100) NULL,
    MailStrAbr NVARCHAR(100) NULL,
    MailCity NVARCHAR(50) NULL,
    MailZip NVARCHAR(10) NULL,
    MailState NVARCHAR(2) NULL,
    Phone NVARCHAR(20) NULL,
    Ext NVARCHAR(10) NULL,
    Website NVARCHAR(255) NULL,
    OpenDate DATE NULL,
    ClosedDate DATE NULL,
    Charter TINYINT NULL,
    CharterNum NVARCHAR(10) NULL,
    FundingType NVARCHAR(50) NULL,
    DOC NVARCHAR(5) NOT NULL,
    DOCType NVARCHAR(100) NOT NULL,
    SOC NVARCHAR(5) NULL,
    SOCType NVARCHAR(100) NULL,
    EdOpsCode NVARCHAR(10) NULL,
    EdOpsName NVARCHAR(100) NULL,
    EILCode NVARCHAR(10) NULL,
    EILName NVARCHAR(100) NULL,
    GSoffered NVARCHAR(20) NULL,
    GSserved NVARCHAR(20) NULL,
    Virtual NVARCHAR(5) NULL,
    Magnet TINYINT NULL,
    Latitude DECIMAL(10, 6) NULL,
    Longitude DECIMAL(10, 6) NULL,
    AdmFName1 NVARCHAR(50) NULL,
    AdmLName1 NVARCHAR(50) NULL,
    AdmEmail1 NVARCHAR(100) NULL,
    AdmFName2 NVARCHAR(50) NULL,
    AdmLName2 NVARCHAR(50) NULL,
    AdmEmail2 NVARCHAR(100) NULL,
    AdmFName3 NVARCHAR(50) NULL,
    AdmLName3 NVARCHAR(50) NULL,
    AdmEmail3 NVARCHAR(100) NULL,
    LastUpdate DATE NOT NULL
);
GO

-- Create indexes for schools table
CREATE INDEX IX_schools_county ON schools(County);
CREATE INDEX IX_schools_district ON schools(District);
CREATE INDEX IX_schools_school ON schools(School);
CREATE INDEX IX_schools_status ON schools(StatusType);
CREATE INDEX IX_schools_charter ON schools(Charter);
CREATE INDEX IX_schools_location ON schools(Latitude, Longitude);
GO

-- FRPM (Free/Reduced Price Meal) table
CREATE TABLE frpm (
    CDSCode NVARCHAR(15) NOT NULL PRIMARY KEY,
    [Academic Year] NVARCHAR(10) NULL,
    [County Code] NVARCHAR(5) NULL,
    [District Code] INT NULL,
    [School Code] NVARCHAR(10) NULL,
    [County Name] NVARCHAR(50) NULL,
    [District Name] NVARCHAR(100) NULL,
    [School Name] NVARCHAR(100) NULL,
    [District Type] NVARCHAR(50) NULL,
    [School Type] NVARCHAR(50) NULL,
    [Educational Option Type] NVARCHAR(50) NULL,
    [NSLP Provision Status] NVARCHAR(50) NULL,
    [Charter School (Y/N)] TINYINT NULL,
    [Charter School Number] NVARCHAR(10) NULL,
    [Charter Funding Type] NVARCHAR(50) NULL,
    IRC TINYINT NULL,
    [Low Grade] NVARCHAR(20) NULL,
    [High Grade] NVARCHAR(20) NULL,
    [Enrollment (K-12)] DECIMAL(10, 2) NULL,
    [Free Meal Count (K-12)] DECIMAL(10, 2) NULL,
    [Percent (%) Eligible Free (K-12)] DECIMAL(5, 2) NULL,
    [FRPM Count (K-12)] DECIMAL(10, 2) NULL,
    [Percent (%) Eligible FRPM (K-12)] DECIMAL(5, 2) NULL,
    [Enrollment (Ages 5-17)] DECIMAL(10, 2) NULL,
    [Free Meal Count (Ages 5-17)] DECIMAL(10, 2) NULL,
    [Percent (%) Eligible Free (Ages 5-17)] DECIMAL(5, 2) NULL,
    [FRPM Count (Ages 5-17)] DECIMAL(10, 2) NULL,
    [Percent (%) Eligible FRPM (Ages 5-17)] DECIMAL(5, 2) NULL,
    [2013-14 CALPADS Fall 1 Certification Status] TINYINT NULL,
    FOREIGN KEY (CDSCode) REFERENCES schools(CDSCode) ON DELETE CASCADE
);
GO

-- Create indexes for frpm table
CREATE INDEX IX_frpm_county_name ON frpm([County Name]);
CREATE INDEX IX_frpm_district_name ON frpm([District Name]);
CREATE INDEX IX_frpm_school_name ON frpm([School Name]);
CREATE INDEX IX_frpm_enrollment ON frpm([Enrollment (K-12)]);
CREATE INDEX IX_frpm_percentage ON frpm([Percent (%) Eligible FRPM (K-12)]);
GO

-- SAT Scores table
CREATE TABLE satscores (
    cds NVARCHAR(15) NOT NULL PRIMARY KEY,
    rtype NVARCHAR(5) NOT NULL,
    sname NVARCHAR(100) NULL,
    dname NVARCHAR(100) NULL,
    cname NVARCHAR(50) NULL,
    enroll12 INT NOT NULL,
    NumTstTakr INT NOT NULL,
    AvgScrRead INT NULL,
    AvgScrMath INT NULL,
    AvgScrWrite INT NULL,
    NumGE1500 INT NULL,
    FOREIGN KEY (cds) REFERENCES schools(CDSCode) ON DELETE CASCADE
);
GO

-- Create indexes for satscores table
CREATE INDEX IX_satscores_district_name ON satscores(dname);
CREATE INDEX IX_satscores_school_name ON satscores(sname);
CREATE INDEX IX_satscores_enrollment ON satscores(enroll12);
CREATE INDEX IX_satscores_test_takers ON satscores(NumTstTakr);
CREATE INDEX IX_satscores_avg_scores ON satscores(AvgScrRead, AvgScrMath, AvgScrWrite);
GO

-- Create performance view for analysis
CREATE VIEW school_performance_analysis AS
SELECT 
    s.CDSCode,
    s.School,
    s.District,
    s.County,
    f.[Enrollment (K-12)] AS enrollment,
    f.[Percent (%) Eligible FRPM (K-12)] AS poverty_rate,
    sat.NumTstTakr AS sat_participants,
    ROUND((sat.AvgScrRead + sat.AvgScrMath + sat.AvgScrWrite) / 3.0, 0) AS sat_composite,
    ROUND((CAST(sat.NumGE1500 AS FLOAT) / NULLIF(sat.NumTstTakr, 0)) * 100, 2) AS excellence_rate,
    CASE 
        WHEN f.[Percent (%) Eligible FRPM (K-12)] < 25 THEN 'Low Poverty'
        WHEN f.[Percent (%) Eligible FRPM (K-12)] < 50 THEN 'Medium Poverty'
        WHEN f.[Percent (%) Eligible FRPM (K-12)] < 75 THEN 'High Poverty'
        ELSE 'Very High Poverty'
    END AS poverty_level
FROM schools s
LEFT JOIN frpm f ON s.CDSCode = f.CDSCode
LEFT JOIN satscores sat ON s.CDSCode = sat.cds
WHERE s.StatusType = 'Active' 
  AND f.[Enrollment (K-12)] IS NOT NULL
  AND f.[Enrollment (K-12)] > 0;
GO

-- Add extended properties for schools table columns

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'CDSCode', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'CDSCode';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'This field represents the 7-digit National Center for Educational Statistics (NCES) school district identification number. The first 2 digits identify the state and the last 5 digits identify the school district. Combined, they make a unique 7-digit ID for each school district.', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'NCESDist';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'This field represents the 5-digit NCES school identification number. The NCESSchool combined with the NCESDist form a unique 12-digit ID for each school.', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'NCESSchool';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'This field identifies the status of the district.', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'StatusType';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'County name', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'County';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'District', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'District';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'School', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'School';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Street', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'Street';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'The abbreviated street address of the school, district, or administrative authority’s physical location.', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'StreetAbr';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'City', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'City';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Zip', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'Zip';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'State', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'State';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'MailStreet', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'MailStreet';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Phone', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'Phone';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'The phone number extension of the school, district, or administrative authority.', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'Ext';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'The website address of the school, district, or administrative authority.', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'Website';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'The date the school opened.', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'OpenDate';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'The date the school closed.', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'ClosedDate';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'This field identifies a charter school.', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'Charter';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'The charter school number,', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'CharterNum';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Indicates the charter school funding type', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'FundingType';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'District Ownership Code', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'DOC';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'The District Ownership Code Type is the text description of the DOC category.', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'DOCType';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'The School Ownership Code is a numeric code used to identify the type of school.', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'SOC';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'The School Ownership Code Type is the text description of the type of school.', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'SOCType';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'The Education Option Code is a short text description of the type of education offered.', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'EdOpsCode';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Educational Option Name', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'EdOpsName';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'The Educational Instruction Level Code is a short text description of the institution''s type relative to the grade range served.', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'EILCode';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'The Educational Instruction Level Name is the long text description of the institution’s type relative to the grade range served.', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'EILName';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'The grade span offered is the lowest grade and the highest grade offered or supported by the school, district, or administrative authority. This field might differ from the grade span served as reported in the most recent certified California Longitudinal Pupil Achievement (CALPADS) Fall 1 data collection.', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'GSoffered';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'It is the lowest grade and the highest grade of student enrollment as reported in the most recent certified CALPADS Fall 1 data collection. Only K–12 enrollment is reported through CALPADS. This field may differ from the grade span offered.', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'GSserved';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'This field identifies the type of virtual instruction offered by the school. Virtual instruction is instruction in which students and teachers are separated by time and/or location, and interaction occurs via computers and/or telecommunications technologies.', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'Virtual';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'This field identifies whether a school is a magnet school and/or provides a magnet program.', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'Magnet';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'The angular distance (expressed in degrees) between the location of the school, district, or administrative authority and the equator measured north to south.', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'Latitude';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'The angular distance (expressed in degrees) between the location of the school, district, or administrative authority and the prime meridian (Greenwich, England) measured from west to east.', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'Longitude';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'administrator''s first name', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'AdmFName1';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'administrator''s last name', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'AdmLName1';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'administrator''s email address', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'schools', 
    @level2type = N'COLUMN', @level2name = N'AdmEmail1';

-- Add extended properties for frpm table columns

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Code of column_description', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'frpm', 
    @level2type = N'COLUMN', @level2name = N'CDSCode';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Description of Academic Year', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'frpm', 
    @level2type = N'COLUMN', @level2name = N'Academic Year';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'County Code', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'frpm', 
    @level2type = N'COLUMN', @level2name = N'County Code';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'District Code', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'frpm', 
    @level2type = N'COLUMN', @level2name = N'District Code';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'School Code', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'frpm', 
    @level2type = N'COLUMN', @level2name = N'School Code';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'County Code', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'frpm', 
    @level2type = N'COLUMN', @level2name = N'County Name';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'District Name', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'frpm', 
    @level2type = N'COLUMN', @level2name = N'District Name';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'School Name', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'frpm', 
    @level2type = N'COLUMN', @level2name = N'School Name';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'District Type', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'frpm', 
    @level2type = N'COLUMN', @level2name = N'District Type';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'School Type', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'frpm', 
    @level2type = N'COLUMN', @level2name = N'School Type';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Educational Option Type', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'frpm', 
    @level2type = N'COLUMN', @level2name = N'Educational Option Type';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'NSLP Provision Status', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'frpm', 
    @level2type = N'COLUMN', @level2name = N'NSLP Provision Status';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Charter School (Y/N)', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'frpm', 
    @level2type = N'COLUMN', @level2name = N'Charter School (Y/N)';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Charter School Number', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'frpm', 
    @level2type = N'COLUMN', @level2name = N'Charter School Number';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Charter Funding Type', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'frpm', 
    @level2type = N'COLUMN', @level2name = N'Charter Funding Type';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Low Grade', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'frpm', 
    @level2type = N'COLUMN', @level2name = N'Low Grade';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'High Grade', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'frpm', 
    @level2type = N'COLUMN', @level2name = N'High Grade';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Enrollment (K-12)', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'frpm', 
    @level2type = N'COLUMN', @level2name = N'Enrollment (K-12)';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Free Meal Count (K-12)', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'frpm', 
    @level2type = N'COLUMN', @level2name = N'Free Meal Count (K-12)';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Free or Reduced Price Meal Count (K-12)', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'frpm', 
    @level2type = N'COLUMN', @level2name = N'FRPM Count (K-12)';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Enrollment (Ages 5-17)', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'frpm', 
    @level2type = N'COLUMN', @level2name = N'Enrollment (Ages 5-17)';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Free Meal Count (Ages 5-17)', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'frpm', 
    @level2type = N'COLUMN', @level2name = N'Free Meal Count (Ages 5-17)';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'2013-14 CALPADS Fall 1 Certification Status', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'frpm', 
    @level2type = N'COLUMN', @level2name = N'2013-14 CALPADS Fall 1 Certification Status';

-- Add extended properties for satscores table columns

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'California Department Schools', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'satscores', 
    @level2type = N'COLUMN', @level2name = N'cds';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'rtype', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'satscores', 
    @level2type = N'COLUMN', @level2name = N'rtype';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'school name', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'satscores', 
    @level2type = N'COLUMN', @level2name = N'sname';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'district segment', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'satscores', 
    @level2type = N'COLUMN', @level2name = N'dname';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'county name', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'satscores', 
    @level2type = N'COLUMN', @level2name = N'cname';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'enrollment (1st-12nd grade)', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'satscores', 
    @level2type = N'COLUMN', @level2name = N'enroll12';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Number of Test Takers in this school', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'satscores', 
    @level2type = N'COLUMN', @level2name = N'NumTstTakr';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'average scores in Reading', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'satscores', 
    @level2type = N'COLUMN', @level2name = N'AvgScrRead';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'average scores in Math', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'satscores', 
    @level2type = N'COLUMN', @level2name = N'AvgScrMath';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'average scores in writing', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'satscores', 
    @level2type = N'COLUMN', @level2name = N'AvgScrWrite';

EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'Number of Test Takers Whose Total SAT Scores Are Greater or Equal to 1500', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'satscores', 
    @level2type = N'COLUMN', @level2name = N'NumGE1500';
