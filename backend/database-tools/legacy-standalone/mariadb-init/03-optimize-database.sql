-- Optimization and final setup for California Schools MariaDB database

USE california_schools;

-- Update table statistics for better query planning
ANALYZE TABLE schools;
ANALYZE TABLE frpm;
ANALYZE TABLE satscores;

-- Create additional indexes for common query patterns
CREATE INDEX idx_schools_county_district ON schools(County, District);
CREATE INDEX idx_schools_charter_status ON schools(Charter, StatusType);
CREATE INDEX idx_frpm_enrollment_range ON frpm(`Enrollment (K-12)`, `Percent (%) Eligible FRPM (K-12)`);
CREATE INDEX idx_satscores_composite ON satscores(AvgScrRead, AvgScrMath, AvgScrWrite);

-- Create a user specifically for Thoth application
CREATE USER IF NOT EXISTS 'thoth_app'@'%' IDENTIFIED BY 'thoth_app_password';
GRANT SELECT, INSERT, UPDATE, DELETE ON california_schools.* TO 'thoth_app'@'%';
FLUSH PRIVILEGES;

-- Create some useful stored procedures for common queries

-- Procedure to get school statistics by county
DELIMITER //
CREATE PROCEDURE GetCountyStatistics(IN county_name VARCHAR(50))
BEGIN
    SELECT 
        COUNT(*) as total_schools,
        COUNT(CASE WHEN StatusType = 'Active' THEN 1 END) as active_schools,
        COUNT(CASE WHEN Charter = 1 THEN 1 END) as charter_schools,
        ROUND(AVG(f.`Enrollment (K-12)`), 0) as avg_enrollment,
        ROUND(AVG(f.`Percent (%) Eligible FRPM (K-12)`), 2) as avg_poverty_rate,
        ROUND(AVG((sat.AvgScrRead + sat.AvgScrMath + sat.AvgScrWrite) / 3), 0) as avg_sat_composite
    FROM schools s
    LEFT JOIN frpm f ON s.CDSCode = f.CDSCode
    LEFT JOIN satscores sat ON s.CDSCode = sat.cds
    WHERE s.County = county_name;
END //

-- Procedure to search schools by name or district
CREATE PROCEDURE SearchSchools(IN search_term VARCHAR(100))
BEGIN
    SELECT 
        s.CDSCode,
        s.School,
        s.District,
        s.County,
        s.StatusType,
        f.`Enrollment (K-12)` as enrollment,
        f.`Percent (%) Eligible FRPM (K-12)` as poverty_rate
    FROM schools s
    LEFT JOIN frpm f ON s.CDSCode = f.CDSCode
    WHERE (s.School LIKE CONCAT('%', search_term, '%') 
           OR s.District LIKE CONCAT('%', search_term, '%'))
      AND s.StatusType = 'Active'
    ORDER BY s.School
    LIMIT 50;
END //

-- Procedure to get top performing schools by SAT scores
CREATE PROCEDURE GetTopPerformingSchools(IN limit_count INT)
BEGIN
    SELECT 
        s.School,
        s.District,
        s.County,
        f.`Enrollment (K-12)` as enrollment,
        sat.NumTstTakr as test_takers,
        ROUND((sat.AvgScrRead + sat.AvgScrMath + sat.AvgScrWrite) / 3) as composite_score,
        sat.AvgScrRead as reading_score,
        sat.AvgScrMath as math_score,
        sat.AvgScrWrite as writing_score
    FROM schools s
    JOIN satscores sat ON s.CDSCode = sat.cds
    LEFT JOIN frpm f ON s.CDSCode = f.CDSCode
    WHERE s.StatusType = 'Active' 
      AND sat.AvgScrRead IS NOT NULL 
      AND sat.AvgScrMath IS NOT NULL 
      AND sat.AvgScrWrite IS NOT NULL
    ORDER BY (sat.AvgScrRead + sat.AvgScrMath + sat.AvgScrWrite) DESC
    LIMIT limit_count;
END //

DELIMITER ;

-- Create summary statistics table for quick reporting
CREATE TABLE database_stats AS
SELECT 
    'Total Schools' as metric,
    COUNT(*) as value,
    'All schools in database' as description
FROM schools
UNION ALL
SELECT 
    'Active Schools' as metric,
    COUNT(*) as value,
    'Currently operational schools' as description
FROM schools 
WHERE StatusType = 'Active'
UNION ALL
SELECT 
    'Charter Schools' as metric,
    COUNT(*) as value,
    'Charter schools (active only)' as description
FROM schools 
WHERE StatusType = 'Active' AND Charter = 1
UNION ALL
SELECT 
    'Counties' as metric,
    COUNT(DISTINCT County) as value,
    'Number of counties represented' as description
FROM schools 
WHERE StatusType = 'Active'
UNION ALL
SELECT 
    'Schools with SAT Data' as metric,
    COUNT(*) as value,
    'Schools with SAT score data' as description
FROM schools s
JOIN satscores sat ON s.CDSCode = sat.cds
WHERE s.StatusType = 'Active'
UNION ALL
SELECT 
    'Schools with Enrollment Data' as metric,
    COUNT(*) as value,
    'Schools with enrollment/FRPM data' as description
FROM schools s
JOIN frpm f ON s.CDSCode = f.CDSCode
WHERE s.StatusType = 'Active';

-- Final verification and summary
SELECT 'Database setup completed successfully!' as status;
SELECT * FROM database_stats ORDER BY metric;