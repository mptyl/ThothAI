-- Import data into California Schools MariaDB database
-- This script uses INSERT statements instead of LOAD DATA LOCAL INFILE
-- to work around container restrictions

USE california_schools;

-- Disable foreign key checks during import
SET FOREIGN_KEY_CHECKS = 0;

-- Note: Data will be imported using a separate script after container startup
-- This is because LOAD DATA LOCAL INFILE requires special MySQL settings
-- and file permissions that are complex to configure in Docker

-- For now, we'll create some sample data to verify the schema works
INSERT INTO schools (CDSCode, StatusType, County, District, School, DOC, DOCType, LastUpdate) VALUES
('01000000000000', 'Active', 'Alameda', 'Sample District', 'Sample School', '00', 'County Office', '2023-01-01'),
('02000000000000', 'Active', 'Alpine', 'Test District', 'Test School', '00', 'County Office', '2023-01-01');

INSERT INTO frpm (CDSCode, `Academic Year`, `County Name`, `District Name`, `School Name`, `Enrollment (K-12)`) VALUES
('01000000000000', '2022-23', 'Alameda', 'Sample District', 'Sample School', 500),
('02000000000000', '2022-23', 'Alpine', 'Test District', 'Test School', 300);

INSERT INTO satscores (cds, rtype, sname, dname, cname, enroll12, NumTstTakr) VALUES
('01000000000000', 'S', 'Sample School', 'Sample District', 'Alameda', 100, 50),
('02000000000000', 'S', 'Test School', 'Test District', 'Alpine', 80, 40);

-- Re-enable foreign key checks
SET FOREIGN_KEY_CHECKS = 1;

-- Verify data import
SELECT 'schools' AS table_name, COUNT(*) AS row_count FROM schools
UNION ALL
SELECT 'frpm' AS table_name, COUNT(*) AS row_count FROM frpm
UNION ALL
SELECT 'satscores' AS table_name, COUNT(*) AS row_count FROM satscores;

-- Basic data validation queries
SELECT 'Active schools with enrollment data' AS description, COUNT(*) AS count
FROM schools s
JOIN frpm f ON s.CDSCode = f.CDSCode
WHERE s.StatusType = 'Active' AND f.`Enrollment (K-12)` > 0;

SELECT 'Schools with SAT data' AS description, COUNT(*) AS count
FROM schools s
JOIN satscores sat ON s.CDSCode = sat.cds
WHERE s.StatusType = 'Active';

SELECT 'Counties represented' AS description, COUNT(DISTINCT County) AS count
FROM schools
WHERE StatusType = 'Active';

-- Show sample data
SELECT 'Sample school data' AS description;
SELECT 
    School,
    District,
    County,
    StatusType,
    Charter
FROM schools 
WHERE StatusType = 'Active' 
LIMIT 5;

SELECT 'Sample performance data' AS description;
SELECT 
    School,
    District,
    enrollment,
    poverty_rate,
    sat_composite
FROM school_performance 
WHERE sat_composite IS NOT NULL 
ORDER BY sat_composite DESC 
LIMIT 5;