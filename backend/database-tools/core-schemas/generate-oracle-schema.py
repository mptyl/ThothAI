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
Generate Oracle schema with column descriptions from CSV files
This script reads the CSV description files and creates Oracle SQL with COMMENT ON COLUMN statements
"""

import csv
import os
from typing import Dict

# Paths
DESCRIPTIONS_DIR = (
    "/Users/mp/thoth_data/dev_databases/california_schools/database_description"
)
OUTPUT_FILE = "/Users/mp/DjangoExperimental/Thoth/oracle-init/01-create-schema.sql"


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


def generate_column_comments(table_name: str, descriptions: Dict[str, str]) -> str:
    """Generate Oracle COMMENT ON COLUMN statements"""
    comments = []
    for column_name, description in descriptions.items():
        # Oracle column names with spaces need to be quoted
        if (
            " " in column_name
            or "(" in column_name
            or ")" in column_name
            or "%" in column_name
        ):
            quoted_column = f'"{column_name}"'
        else:
            quoted_column = column_name
        comments.append(
            f"COMMENT ON COLUMN {table_name}.{quoted_column} IS '{description}';"
        )
    return "\n".join(comments)


def generate_schema():
    """Generate the Oracle schema with column comments"""

    # Read descriptions for each table
    schools_desc = read_column_descriptions("schools.csv")
    frpm_desc = read_column_descriptions("frpm.csv")
    satscores_desc = read_column_descriptions("satscores.csv")

    print(
        f"Loaded descriptions: Schools={len(schools_desc)}, FRPM={len(frpm_desc)}, SAT={len(satscores_desc)}"
    )

    # Generate column comments
    schools_comments = generate_column_comments("schools", schools_desc)
    frpm_comments = generate_column_comments("frpm", frpm_desc)
    satscores_comments = generate_column_comments("satscores", satscores_desc)

    schema_sql = f"""-- Oracle schema for California Schools database with column comments
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
{schools_comments}

-- Add column comments for frpm table
{frpm_comments}

-- Add column comments for satscores table
{satscores_comments}

-- Commit the changes
COMMIT;
"""

    # Write the schema to file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(schema_sql)

    print(f"Oracle schema with column comments generated: {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_schema()
