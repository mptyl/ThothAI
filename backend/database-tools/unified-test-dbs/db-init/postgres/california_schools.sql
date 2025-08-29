-- PostgreSQL schema for california_schools database
CREATE DATABASE california_schools;
\c california_schools;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE frpm (
CDSCode TEXT NOT NULL,
"Academic Year" TEXT,
"County Code" TEXT,
"District Code" INTEGER,
"School Code" TEXT,
"County Name" TEXT,
"District Name" TEXT,
"School Name" TEXT,
"District Type" TEXT,
"School Type" TEXT,
"Educational Option Type" TEXT,
"NSLP Provision Status" TEXT,
"Charter School (Y/N)" INTEGER,
"Charter School Number" TEXT,
"Charter Funding Type" TEXT,
IRC INTEGER,
"Low Grade" TEXT,
"High Grade" TEXT,
"Enrollment (K-12)" DECIMAL(10,2),
"Free Meal Count (K-12)" DECIMAL(10,2),
"Percent (%) Eligible Free (K-12)" DECIMAL(10,2),
"FRPM Count (K-12)" DECIMAL(10,2),
"Percent (%) Eligible FRPM (K-12)" DECIMAL(10,2),
"Enrollment (Ages 5-17)" DECIMAL(10,2),
"Free Meal Count (Ages 5-17)" DECIMAL(10,2),
"Percent (%) Eligible Free (Ages 5-17)" DECIMAL(10,2),
"FRPM Count (Ages 5-17)" DECIMAL(10,2),
"Percent (%) Eligible FRPM (Ages 5-17)" DECIMAL(10,2),
"2013-14 CALPADS Fall 1 Certification Status" INTEGER,
    PRIMARY KEY (CDSCode)
);

COMMENT ON COLUMN frpm.CDSCode IS 'CDSCode';
COMMENT ON COLUMN frpm."Academic Year" IS 'Academic Year';
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

CREATE TABLE satscores (
cds TEXT NOT NULL,
rtype TEXT NOT NULL,
sname TEXT,
dname TEXT,
cname TEXT,
enroll12 INTEGER NOT NULL,
NumTstTakr INTEGER NOT NULL,
AvgScrRead INTEGER,
AvgScrMath INTEGER,
AvgScrWrite INTEGER,
NumGE1500 INTEGER,
    PRIMARY KEY (cds)
);

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

CREATE TABLE schools (
CDSCode TEXT NOT NULL,
NCESDist TEXT,
NCESSchool TEXT,
StatusType TEXT NOT NULL,
County TEXT NOT NULL,
District TEXT NOT NULL,
School TEXT,
Street TEXT,
StreetAbr TEXT,
City TEXT,
Zip TEXT,
State TEXT,
MailStreet TEXT,
MailStrAbr TEXT,
MailCity TEXT,
MailZip TEXT,
MailState TEXT,
Phone TEXT,
Ext TEXT,
Website TEXT,
OpenDate DATE,
ClosedDate DATE,
Charter INTEGER,
CharterNum TEXT,
FundingType TEXT,
DOC TEXT NOT NULL,
DOCType TEXT NOT NULL,
SOC TEXT,
SOCType TEXT,
EdOpsCode TEXT,
EdOpsName TEXT,
EILCode TEXT,
EILName TEXT,
GSoffered TEXT,
GSserved TEXT,
Virtual TEXT,
Magnet INTEGER,
Latitude DECIMAL(10,2),
Longitude DECIMAL(10,2),
AdmFName1 TEXT,
AdmLName1 TEXT,
AdmEmail1 TEXT,
AdmFName2 TEXT,
AdmLName2 TEXT,
AdmEmail2 TEXT,
AdmFName3 TEXT,
AdmLName3 TEXT,
AdmEmail3 TEXT,
LastUpdate DATE NOT NULL,
    PRIMARY KEY (CDSCode)
);

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

