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
Generate enhanced MariaDB schema with column descriptions from CSV files
This script reads the CSV description files and creates a schema with COMMENT attributes
"""

import csv
import os
from typing import Dict

# Paths
DESCRIPTIONS_DIR = (
    "/Users/mp/thoth_data/dev_databases/california_schools/database_description"
)
OUTPUT_FILE = (
    "/Users/mp/DjangoExperimental/Thoth/mariadb-init/01-create-schema-with-comments.sql"
)


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
                    escaped_description = column_description.replace("'", "\\'")
                    descriptions[original_column_name] = escaped_description

    except Exception as e:
        print(f"Error reading {csv_file}: {e}")

    return descriptions


def format_comment(description: str) -> str:
    """Format description as SQL COMMENT"""
    if not description:
        return ""
    return f" COMMENT '{description}'"


def generate_schema():
    """Generate the enhanced schema with column comments"""

    # Read descriptions for each table
    schools_desc = read_column_descriptions("schools.csv")
    frpm_desc = read_column_descriptions("frpm.csv")
    satscores_desc = read_column_descriptions("satscores.csv")

    print(
        f"Loaded descriptions: Schools={len(schools_desc)}, FRPM={len(frpm_desc)}, SAT={len(satscores_desc)}"
    )

    schema_sql = """-- Enhanced MariaDB schema for California Schools database with column comments
-- Generated from SQLite schema with descriptions from CSV files

USE california_schools;

-- Schools table (main reference table)
CREATE TABLE schools (
    CDSCode VARCHAR(15) NOT NULL PRIMARY KEY{cds_comment},
    NCESDist VARCHAR(20) NULL{ncesdist_comment},
    NCESSchool VARCHAR(20) NULL{ncesschool_comment},
    StatusType VARCHAR(20) NOT NULL{statustype_comment},
    County VARCHAR(50) NOT NULL{county_comment},
    District VARCHAR(100) NOT NULL{district_comment},
    School VARCHAR(100) NULL{school_comment},
    Street VARCHAR(100) NULL{street_comment},
    StreetAbr VARCHAR(100) NULL{streetabr_comment},
    City VARCHAR(50) NULL{city_comment},
    Zip VARCHAR(10) NULL{zip_comment},
    State VARCHAR(2) NULL{state_comment},
    MailStreet VARCHAR(100) NULL{mailstreet_comment},
    MailStrAbr VARCHAR(100) NULL{mailstrabr_comment},
    MailCity VARCHAR(50) NULL{mailcity_comment},
    MailZip VARCHAR(10) NULL{mailzip_comment},
    MailState VARCHAR(2) NULL{mailstate_comment},
    Phone VARCHAR(20) NULL{phone_comment},
    Ext VARCHAR(10) NULL{ext_comment},
    Website VARCHAR(255) NULL{website_comment},
    OpenDate DATE NULL{opendate_comment},
    ClosedDate DATE NULL{closeddate_comment},
    Charter TINYINT NULL{charter_comment},
    CharterNum VARCHAR(10) NULL{charternum_comment},
    FundingType VARCHAR(50) NULL{fundingtype_comment},
    DOC VARCHAR(5) NOT NULL{doc_comment},
    DOCType VARCHAR(100) NOT NULL{doctype_comment},
    SOC VARCHAR(5) NULL{soc_comment},
    SOCType VARCHAR(100) NULL{soctype_comment},
    EdOpsCode VARCHAR(10) NULL{edopscode_comment},
    EdOpsName VARCHAR(100) NULL{edopsname_comment},
    EILCode VARCHAR(10) NULL{eilcode_comment},
    EILName VARCHAR(100) NULL{eilname_comment},
    GSoffered VARCHAR(20) NULL{gsoffered_comment},
    GSserved VARCHAR(20) NULL{gsserved_comment},
    Virtual VARCHAR(5) NULL{virtual_comment},
    Magnet TINYINT NULL{magnet_comment},
    Latitude DECIMAL(10, 6) NULL{latitude_comment},
    Longitude DECIMAL(10, 6) NULL{longitude_comment},
    AdmFName1 VARCHAR(50) NULL{admfname1_comment},
    AdmLName1 VARCHAR(50) NULL{admlname1_comment},
    AdmEmail1 VARCHAR(100) NULL{admemail1_comment},
    AdmFName2 VARCHAR(50) NULL{admfname2_comment},
    AdmLName2 VARCHAR(50) NULL{admlname2_comment},
    AdmEmail2 VARCHAR(100) NULL{admemail2_comment},
    AdmFName3 VARCHAR(50) NULL{admfname3_comment},
    AdmLName3 VARCHAR(50) NULL{admlname3_comment},
    AdmEmail3 VARCHAR(100) NULL{admemail3_comment},
    LastUpdate DATE NOT NULL{lastupdate_comment},
    INDEX idx_county (County),
    INDEX idx_district (District),
    INDEX idx_school (School),
    INDEX idx_status (StatusType),
    INDEX idx_charter (Charter),
    INDEX idx_location (Latitude, Longitude)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- FRPM (Free/Reduced Price Meal) table
CREATE TABLE frpm (
    CDSCode VARCHAR(15) NOT NULL PRIMARY KEY{frpm_cdscode_comment},
    `Academic Year` VARCHAR(10) NULL{academic_year_comment},
    `County Code` VARCHAR(5) NULL{county_code_comment},
    `District Code` INT NULL{district_code_comment},
    `School Code` VARCHAR(10) NULL{school_code_comment},
    `County Name` VARCHAR(50) NULL{county_name_comment},
    `District Name` VARCHAR(100) NULL{district_name_comment},
    `School Name` VARCHAR(100) NULL{school_name_comment},
    `District Type` VARCHAR(50) NULL{district_type_comment},
    `School Type` VARCHAR(50) NULL{school_type_comment},
    `Educational Option Type` VARCHAR(50) NULL{educational_option_type_comment},
    `NSLP Provision Status` VARCHAR(50) NULL{nslp_provision_status_comment},
    `Charter School (Y/N)` TINYINT NULL{charter_school_yn_comment},
    `Charter School Number` VARCHAR(10) NULL{charter_school_number_comment},
    `Charter Funding Type` VARCHAR(50) NULL{charter_funding_type_comment},
    IRC TINYINT NULL{irc_comment},
    `Low Grade` VARCHAR(20) NULL{low_grade_comment},
    `High Grade` VARCHAR(20) NULL{high_grade_comment},
    `Enrollment (K-12)` DECIMAL(10, 2) NULL{enrollment_k12_comment},
    `Free Meal Count (K-12)` DECIMAL(10, 2) NULL{free_meal_count_k12_comment},
    `Percent (%) Eligible Free (K-12)` DECIMAL(5, 2) NULL{percent_eligible_free_k12_comment},
    `FRPM Count (K-12)` DECIMAL(10, 2) NULL{frpm_count_k12_comment},
    `Percent (%) Eligible FRPM (K-12)` DECIMAL(5, 2) NULL{percent_eligible_frpm_k12_comment},
    `Enrollment (Ages 5-17)` DECIMAL(10, 2) NULL{enrollment_ages_5_17_comment},
    `Free Meal Count (Ages 5-17)` DECIMAL(10, 2) NULL{free_meal_count_ages_5_17_comment},
    `Percent (%) Eligible Free (Ages 5-17)` DECIMAL(5, 2) NULL{percent_eligible_free_ages_5_17_comment},
    `FRPM Count (Ages 5-17)` DECIMAL(10, 2) NULL{frpm_count_ages_5_17_comment},
    `Percent (%) Eligible FRPM (Ages 5-17)` DECIMAL(5, 2) NULL{percent_eligible_frpm_ages_5_17_comment},
    `2013-14 CALPADS Fall 1 Certification Status` TINYINT NULL{calpads_certification_comment},
    FOREIGN KEY (CDSCode) REFERENCES schools(CDSCode) ON DELETE CASCADE,
    INDEX idx_county_name (`County Name`),
    INDEX idx_district_name (`District Name`),
    INDEX idx_school_name (`School Name`),
    INDEX idx_enrollment (`Enrollment (K-12)`),
    INDEX idx_frpm_percentage (`Percent (%) Eligible FRPM (K-12)`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- SAT Scores table
CREATE TABLE satscores (
    cds VARCHAR(15) NOT NULL PRIMARY KEY{sat_cds_comment},
    rtype VARCHAR(5) NOT NULL{rtype_comment},
    sname VARCHAR(100) NULL{sname_comment},
    dname VARCHAR(100) NULL{dname_comment},
    cname VARCHAR(50) NULL{cname_comment},
    enroll12 INT NOT NULL{enroll12_comment},
    NumTstTakr INT NOT NULL{numtsttakr_comment},
    AvgScrRead INT NULL{avgscrread_comment},
    AvgScrMath INT NULL{avgscrmath_comment},
    AvgScrWrite INT NULL{avgscrwrite_comment},
    NumGE1500 INT NULL{numge1500_comment},
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
""".format(
        # Schools table comments
        cds_comment=format_comment(schools_desc.get("CDSCode", "")),
        ncesdist_comment=format_comment(schools_desc.get("NCESDist", "")),
        ncesschool_comment=format_comment(schools_desc.get("NCESSchool", "")),
        statustype_comment=format_comment(schools_desc.get("StatusType", "")),
        county_comment=format_comment(schools_desc.get("County", "")),
        district_comment=format_comment(schools_desc.get("District", "")),
        school_comment=format_comment(schools_desc.get("School", "")),
        street_comment=format_comment(schools_desc.get("Street", "")),
        streetabr_comment=format_comment(schools_desc.get("StreetAbr", "")),
        city_comment=format_comment(schools_desc.get("City", "")),
        zip_comment=format_comment(schools_desc.get("Zip", "")),
        state_comment=format_comment(schools_desc.get("State", "")),
        mailstreet_comment=format_comment(schools_desc.get("MailStreet", "")),
        mailstrabr_comment=format_comment(schools_desc.get("MailStrAbr", "")),
        mailcity_comment=format_comment(schools_desc.get("MailCity", "")),
        mailzip_comment=format_comment(schools_desc.get("MailZip", "")),
        mailstate_comment=format_comment(schools_desc.get("MailState", "")),
        phone_comment=format_comment(schools_desc.get("Phone", "")),
        ext_comment=format_comment(schools_desc.get("Ext", "")),
        website_comment=format_comment(schools_desc.get("Website", "")),
        opendate_comment=format_comment(schools_desc.get("OpenDate", "")),
        closeddate_comment=format_comment(schools_desc.get("ClosedDate", "")),
        charter_comment=format_comment(schools_desc.get("Charter", "")),
        charternum_comment=format_comment(schools_desc.get("CharterNum", "")),
        fundingtype_comment=format_comment(schools_desc.get("FundingType", "")),
        doc_comment=format_comment(schools_desc.get("DOC", "")),
        doctype_comment=format_comment(schools_desc.get("DOCType", "")),
        soc_comment=format_comment(schools_desc.get("SOC", "")),
        soctype_comment=format_comment(schools_desc.get("SOCType", "")),
        edopscode_comment=format_comment(schools_desc.get("EdOpsCode", "")),
        edopsname_comment=format_comment(schools_desc.get("EdOpsName", "")),
        eilcode_comment=format_comment(schools_desc.get("EILCode", "")),
        eilname_comment=format_comment(schools_desc.get("EILName", "")),
        gsoffered_comment=format_comment(schools_desc.get("GSoffered", "")),
        gsserved_comment=format_comment(schools_desc.get("GSserved", "")),
        virtual_comment=format_comment(schools_desc.get("Virtual", "")),
        magnet_comment=format_comment(schools_desc.get("Magnet", "")),
        latitude_comment=format_comment(schools_desc.get("Latitude", "")),
        longitude_comment=format_comment(schools_desc.get("Longitude", "")),
        admfname1_comment=format_comment(schools_desc.get("AdmFName1", "")),
        admlname1_comment=format_comment(schools_desc.get("AdmLName1", "")),
        admemail1_comment=format_comment(schools_desc.get("AdmEmail1", "")),
        admfname2_comment=format_comment(schools_desc.get("AdmFName2", "")),
        admlname2_comment=format_comment(schools_desc.get("AdmLName2", "")),
        admemail2_comment=format_comment(schools_desc.get("AdmEmail2", "")),
        admfname3_comment=format_comment(schools_desc.get("AdmFName3", "")),
        admlname3_comment=format_comment(schools_desc.get("AdmLName3", "")),
        admemail3_comment=format_comment(schools_desc.get("AdmEmail3", "")),
        lastupdate_comment=format_comment(schools_desc.get("LastUpdate", "")),
        # FRPM table comments
        frpm_cdscode_comment=format_comment(frpm_desc.get("CDSCode", "")),
        academic_year_comment=format_comment(frpm_desc.get("Academic Year", "")),
        county_code_comment=format_comment(frpm_desc.get("County Code", "")),
        district_code_comment=format_comment(frpm_desc.get("District Code", "")),
        school_code_comment=format_comment(frpm_desc.get("School Code ", "")),
        county_name_comment=format_comment(frpm_desc.get("County Name", "")),
        district_name_comment=format_comment(frpm_desc.get("District Name ", "")),
        school_name_comment=format_comment(frpm_desc.get("School Name", "")),
        district_type_comment=format_comment(frpm_desc.get("District Type", "")),
        school_type_comment=format_comment(frpm_desc.get("School Type ", "")),
        educational_option_type_comment=format_comment(
            frpm_desc.get("Educational Option Type", "")
        ),
        nslp_provision_status_comment=format_comment(
            frpm_desc.get("NSLP Provision Status", "")
        ),
        charter_school_yn_comment=format_comment(
            frpm_desc.get("Charter School (Y/N)", "")
        ),
        charter_school_number_comment=format_comment(
            frpm_desc.get("Charter School Number", "")
        ),
        charter_funding_type_comment=format_comment(
            frpm_desc.get("Charter Funding Type", "")
        ),
        irc_comment=format_comment(frpm_desc.get("IRC", "")),
        low_grade_comment=format_comment(frpm_desc.get("Low Grade", "")),
        high_grade_comment=format_comment(frpm_desc.get("High Grade", "")),
        enrollment_k12_comment=format_comment(frpm_desc.get("Enrollment (K-12)", "")),
        free_meal_count_k12_comment=format_comment(
            frpm_desc.get("Free Meal Count (K-12)", "")
        ),
        percent_eligible_free_k12_comment=format_comment(
            frpm_desc.get("Percent (%) Eligible Free (K-12)", "")
        ),
        frpm_count_k12_comment=format_comment(frpm_desc.get("FRPM Count (K-12)", "")),
        percent_eligible_frpm_k12_comment=format_comment(
            frpm_desc.get("Percent (%) Eligible FRPM (K-12)", "")
        ),
        enrollment_ages_5_17_comment=format_comment(
            frpm_desc.get("Enrollment (Ages 5-17)", "")
        ),
        free_meal_count_ages_5_17_comment=format_comment(
            frpm_desc.get("Free Meal Count (Ages 5-17)", "")
        ),
        percent_eligible_free_ages_5_17_comment=format_comment(
            frpm_desc.get(" Percent (%) Eligible Free (Ages 5-17)", "")
        ),
        frpm_count_ages_5_17_comment=format_comment(
            frpm_desc.get("FRPM Count (Ages 5-17)", "")
        ),
        percent_eligible_frpm_ages_5_17_comment=format_comment(
            frpm_desc.get("Percent (%) Eligible FRPM (Ages 5-17)", "")
        ),
        calpads_certification_comment=format_comment(
            frpm_desc.get("2013-14 CALPADS Fall 1 Certification Status", "")
        ),
        # SAT Scores table comments
        sat_cds_comment=format_comment(satscores_desc.get("cds", "")),
        rtype_comment=format_comment(satscores_desc.get("rtype", "")),
        sname_comment=format_comment(satscores_desc.get("sname", "")),
        dname_comment=format_comment(satscores_desc.get("dname", "")),
        cname_comment=format_comment(satscores_desc.get("cname", "")),
        enroll12_comment=format_comment(satscores_desc.get("enroll12", "")),
        numtsttakr_comment=format_comment(satscores_desc.get("NumTstTakr", "")),
        avgscrread_comment=format_comment(satscores_desc.get("AvgScrRead", "")),
        avgscrmath_comment=format_comment(satscores_desc.get("AvgScrMath", "")),
        avgscrwrite_comment=format_comment(satscores_desc.get("AvgScrWrite", "")),
        numge1500_comment=format_comment(satscores_desc.get("NumGE1500", "")),
    )

    # Write the schema to file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(schema_sql)

    print(f"Enhanced schema with comments generated: {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_schema()
