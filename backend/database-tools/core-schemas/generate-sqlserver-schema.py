#!/usr/bin/env python3

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Generate SQL Server schema with column descriptions from CSV files
This script reads the CSV description files and creates a T-SQL schema with extended properties
"""

import csv
import os
from typing import Dict

# Paths
DESCRIPTIONS_DIR = (
    "/Users/mp/thoth_data/dev_databases/california_schools/database_description"
)
OUTPUT_FILE = "/Users/mp/DjangoExperimental/Thoth/sqlserver-init/01-create-schema.sql"


def read_column_descriptions(csv_file: str) -> Dict[str, str]:
    """Read column descriptions from CSV file"""
    descriptions = {}
    csv_path = os.path.join(DESCRIPTIONS_DIR, csv_file)

    if not os.path.exists(csv_path):
        print(f"Warning: CSV file not found: {csv_path}")
        return descriptions

    try:
        with open(csv_path, "r", encoding="utf-8-sig") as file:  # utf-8-sig handles BOM
            reader = csv.DictReader(file)

            for row in reader:
                original_column_name = row.get("original_column_name", "").strip()
                column_description = row.get("column_description", "").strip()

                if original_column_name and column_description:
                    # Escape single quotes for SQL
                    escaped_description = column_description.replace("'", "''")
                    descriptions[original_column_name] = escaped_description

    except Exception as e:
        print(f"Error reading {csv_file}: {e}")

    return descriptions


def generate_extended_properties(table_name: str, descriptions: Dict[str, str]) -> str:
    """Generate SQL Server extended properties for column descriptions"""
    properties = []
    for column_name, description in descriptions.items():
        properties.append(f"""
EXEC sp_addextendedproperty 
    @name = N'MS_Description', 
    @value = N'{description}', 
    @level0type = N'SCHEMA', @level0name = N'dbo', 
    @level1type = N'TABLE', @level1name = N'{table_name}', 
    @level2type = N'COLUMN', @level2name = N'{column_name}';""")
    return "\n".join(properties)


def generate_schema():
    """Generate the SQL Server schema with extended properties"""

    # Read descriptions for each table
    schools_desc = read_column_descriptions("schools.csv")
    frpm_desc = read_column_descriptions("frpm.csv")
    satscores_desc = read_column_descriptions("satscores.csv")

    print(
        f"Loaded descriptions: Schools={len(schools_desc)}, FRPM={len(frpm_desc)}, SAT={len(satscores_desc)}"
    )

    # Generate extended properties
    schools_properties = generate_extended_properties("schools", schools_desc)
    frpm_properties = generate_extended_properties("frpm", frpm_desc)
    satscores_properties = generate_extended_properties("satscores", satscores_desc)

    schema_sql = f"""-- SQL Server schema for California Schools database with extended properties
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
{schools_properties}

-- Add extended properties for frpm table columns
{frpm_properties}

-- Add extended properties for satscores table columns
{satscores_properties}
""".format(
        schools_properties=generate_extended_properties("schools", schools_desc),
        frpm_properties=generate_extended_properties("frpm", frpm_desc),
        satscores_properties=generate_extended_properties("satscores", satscores_desc),
    )

    # Write the schema to file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(schema_sql)

    print(f"SQL Server schema with extended properties generated: {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_schema()
