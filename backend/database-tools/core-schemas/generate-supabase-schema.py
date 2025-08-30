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
Generate PostgreSQL schema for Supabase with column descriptions from CSV files
This script reads the CSV description files and creates PostgreSQL SQL with COMMENT ON COLUMN statements
"""

import csv
import os
from typing import Dict, Optional

# Paths
DESCRIPTIONS_DIR = "/Users/mp/thoth_data/dev_databases/california_schools/database_description"
OUTPUT_FILE = "/Users/mp/DjangoExperimental/Thoth/supabase-init/01-create-schema.sql"

def read_column_descriptions(csv_file: str) -> Dict[str, str]:
    """Read column descriptions from CSV file"""
    descriptions = {}
    csv_path = os.path.join(DESCRIPTIONS_DIR, csv_file)
    
    if not os.path.exists(csv_path):
        print(f"Warning: CSV file not found: {csv_path}")
        return descriptions
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as file:  # utf-8-sig handles BOM
            reader = csv.DictReader(file)
            
            for row in reader:
                original_column_name = row.get('original_column_name', '').strip()
                column_description = row.get('column_description', '').strip()
                
                if original_column_name and column_description:
                    # Escape single quotes for SQL
                    escaped_description = column_description.replace("'", "''")
                    descriptions[original_column_name] = escaped_description
                    
    except Exception as e:
        print(f"Error reading {csv_file}: {e}")
    
    return descriptions

def generate_column_comments(table_name: str, descriptions: Dict[str, str]) -> str:
    """Generate PostgreSQL COMMENT ON COLUMN statements"""
    comments = []
    for column_name, description in descriptions.items():
        # PostgreSQL column names with spaces need to be quoted
        if ' ' in column_name or '(' in column_name or ')' in column_name or '%' in column_name:
            quoted_column = f'"{column_name}"'
        else:
            # For regular column names, quote them to preserve case
            quoted_column = f'"{column_name}"'
        comments.append(f"COMMENT ON COLUMN {table_name}.{quoted_column} IS '{description}';")
    return '\n'.join(comments)

def generate_schema():
    """Generate the PostgreSQL schema with column comments"""
    
    # Read descriptions for each table
    schools_desc = read_column_descriptions('schools.csv')
    frpm_desc = read_column_descriptions('frpm.csv')
    satscores_desc = read_column_descriptions('satscores.csv')
    
    print(f"Loaded descriptions: Schools={len(schools_desc)}, FRPM={len(frpm_desc)}, SAT={len(satscores_desc)}")
    
    # Generate column comments
    schools_comments = generate_column_comments('schools', schools_desc)
    frpm_comments = generate_column_comments('frpm', frpm_desc)
    satscores_comments = generate_column_comments('satscores', satscores_desc)
    
    schema_sql = f"""-- Supabase PostgreSQL schema for California Schools database with column comments
-- Generated from SQLite schema with descriptions from CSV files

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
{schools_comments}

-- Add column comments for frpm table
{frpm_comments}

-- Add column comments for satscores table
{satscores_comments}
"""
    
    # Write the schema to file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(schema_sql)
    
    print(f"PostgreSQL/Supabase schema with column comments generated: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_schema()