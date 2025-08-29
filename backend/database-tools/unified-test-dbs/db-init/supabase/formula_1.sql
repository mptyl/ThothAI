-- Supabase PostgreSQL schema for formula_1 database
CREATE DATABASE formula_1;
\c formula_1;

-- Enable Supabase extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pgjwt";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create auth schema for Supabase compatibility
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS realtime;
CREATE SCHEMA IF NOT EXISTS storage;

-- Supabase auth functions
CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid AS $$
  SELECT uuid_generate_v4()
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION auth.role() RETURNS text AS $$
  SELECT COALESCE(current_setting('request.jwt.claims', true)::json->>'role', 'anon')
$$ LANGUAGE sql STABLE;

CREATE TABLE circuits (
circuitId INTEGER,
circuitRef TEXT NOT NULL,
name TEXT NOT NULL,
location TEXT,
country TEXT,
lat DECIMAL(10,2),
lng DECIMAL(10,2),
alt INTEGER,
url TEXT NOT NULL,
    PRIMARY KEY (circuitId)
);

ALTER TABLE circuits ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow read access to circuits" ON circuits FOR SELECT USING (true);

COMMENT ON COLUMN circuits.circuitId IS 'unique identification number of the circuit';
COMMENT ON COLUMN circuits.circuitRef IS 'circuit reference name';
COMMENT ON COLUMN circuits.name IS 'full name of circuit';
COMMENT ON COLUMN circuits.location IS 'location of circuit';
COMMENT ON COLUMN circuits.country IS 'country of circuit';
COMMENT ON COLUMN circuits.lat IS 'latitude of location of circuit';
COMMENT ON COLUMN circuits.lng IS 'longitude of location of circuit';
COMMENT ON COLUMN circuits.url IS 'url';

CREATE TABLE constructors (
constructorId INTEGER,
constructorRef TEXT NOT NULL,
name TEXT NOT NULL,
nationality TEXT,
url TEXT NOT NULL,
    PRIMARY KEY (constructorId)
);

ALTER TABLE constructors ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow read access to constructors" ON constructors FOR SELECT USING (true);

COMMENT ON COLUMN constructors.constructorId IS 'the unique identification number identifying constructors';
COMMENT ON COLUMN constructors.constructorRef IS 'Constructor Reference name';
COMMENT ON COLUMN constructors.name IS 'full name of the constructor';
COMMENT ON COLUMN constructors.nationality IS 'nationality of the constructor';
COMMENT ON COLUMN constructors.url IS 'the introduction website of the constructor';

CREATE TABLE drivers (
driverId INTEGER,
driverRef TEXT NOT NULL,
number INTEGER,
code TEXT,
forename TEXT NOT NULL,
surname TEXT NOT NULL,
dob DATE,
nationality TEXT,
url TEXT NOT NULL,
    PRIMARY KEY (driverId)
);

ALTER TABLE drivers ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow read access to drivers" ON drivers FOR SELECT USING (true);

COMMENT ON COLUMN drivers.driverId IS 'the unique identification number identifying each driver';
COMMENT ON COLUMN drivers.driverRef IS 'driver reference name';
COMMENT ON COLUMN drivers.number IS 'number';
COMMENT ON COLUMN drivers.code IS 'abbreviated code for drivers';
COMMENT ON COLUMN drivers.forename IS 'forename';
COMMENT ON COLUMN drivers.surname IS 'surname';
COMMENT ON COLUMN drivers.dob IS 'date of birth';
COMMENT ON COLUMN drivers.nationality IS 'nationality of drivers';
COMMENT ON COLUMN drivers.url IS 'the introduction website of the drivers';

CREATE TABLE seasons (
year INTEGER NOT NULL,
url TEXT NOT NULL,
    PRIMARY KEY (year)
);

ALTER TABLE seasons ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow read access to seasons" ON seasons FOR SELECT USING (true);

COMMENT ON COLUMN seasons.year IS 'the unique identification number identifying the race';
COMMENT ON COLUMN seasons.url IS 'website link of season race introduction';

CREATE TABLE races (
raceId INTEGER,
year INTEGER NOT NULL,
round INTEGER NOT NULL,
circuitId INTEGER NOT NULL,
name TEXT NOT NULL,
date DATE NOT NULL,
time TEXT,
url TEXT,
    PRIMARY KEY (raceId)
);

ALTER TABLE races ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow read access to races" ON races FOR SELECT USING (true);

COMMENT ON COLUMN races.raceId IS 'the unique identification number identifying the race';
COMMENT ON COLUMN races.year IS 'year';
COMMENT ON COLUMN races.round IS 'round';
COMMENT ON COLUMN races.circuitId IS 'circuit Id';
COMMENT ON COLUMN races.name IS 'name of the race';
COMMENT ON COLUMN races.date IS 'duration time';
COMMENT ON COLUMN races.time IS 'time of the location';
COMMENT ON COLUMN races.url IS 'introduction of races';

CREATE TABLE constructorResults (
constructorResultsId INTEGER,
raceId INTEGER NOT NULL,
constructorId INTEGER NOT NULL,
points DECIMAL(10,2),
status TEXT,
    PRIMARY KEY (constructorResultsId)
);

ALTER TABLE constructorResults ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow read access to constructorResults" ON constructorResults FOR SELECT USING (true);

COMMENT ON COLUMN constructorResults.constructorResultsId IS 'constructor Results Id';
COMMENT ON COLUMN constructorResults.raceId IS 'race id';
COMMENT ON COLUMN constructorResults.constructorId IS 'constructor id';
COMMENT ON COLUMN constructorResults.points IS 'points';
COMMENT ON COLUMN constructorResults.status IS 'status';

CREATE TABLE constructorStandings (
constructorStandingsId INTEGER,
raceId INTEGER NOT NULL,
constructorId INTEGER NOT NULL,
points DECIMAL(10,2) NOT NULL,
position INTEGER,
positionText TEXT,
wins INTEGER NOT NULL,
    PRIMARY KEY (constructorStandingsId)
);

ALTER TABLE constructorStandings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow read access to constructorStandings" ON constructorStandings FOR SELECT USING (true);

COMMENT ON COLUMN constructorStandings.constructorStandingsId IS 'unique identification of the constructor standing records';
COMMENT ON COLUMN constructorStandings.raceId IS 'id number identifying which races';
COMMENT ON COLUMN constructorStandings.constructorId IS 'id number identifying which id';
COMMENT ON COLUMN constructorStandings.points IS 'how many points acquired in each race';
COMMENT ON COLUMN constructorStandings.position IS 'position or track of circuits';
COMMENT ON COLUMN constructorStandings.wins IS 'wins';

CREATE TABLE driverStandings (
driverStandingsId INTEGER,
raceId INTEGER NOT NULL,
driverId INTEGER NOT NULL,
points DECIMAL(10,2) NOT NULL,
position INTEGER,
positionText TEXT,
wins INTEGER NOT NULL,
    PRIMARY KEY (driverStandingsId)
);

ALTER TABLE driverStandings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow read access to driverStandings" ON driverStandings FOR SELECT USING (true);

COMMENT ON COLUMN driverStandings.driverStandingsId IS 'the unique identification number identifying driver standing records';
COMMENT ON COLUMN driverStandings.raceId IS 'id number identifying which races';
COMMENT ON COLUMN driverStandings.driverId IS 'id number identifying which drivers';
COMMENT ON COLUMN driverStandings.points IS 'how many points acquired in each race';
COMMENT ON COLUMN driverStandings.position IS 'position or track of circuits';
COMMENT ON COLUMN driverStandings.wins IS 'wins';

CREATE TABLE lapTimes (
raceId INTEGER NOT NULL,
driverId INTEGER NOT NULL,
lap INTEGER NOT NULL,
position INTEGER,
time TEXT,
milliseconds INTEGER,
    PRIMARY KEY (raceId, driverId, lap)
);

ALTER TABLE lapTimes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow read access to lapTimes" ON lapTimes FOR SELECT USING (true);

COMMENT ON COLUMN lapTimes.raceId IS 'the identification number identifying race';
COMMENT ON COLUMN lapTimes.driverId IS 'the identification number identifying each driver';
COMMENT ON COLUMN lapTimes.lap IS 'lap number';
COMMENT ON COLUMN lapTimes.position IS 'position or track of circuits';
COMMENT ON COLUMN lapTimes.time IS 'lap time';
COMMENT ON COLUMN lapTimes.milliseconds IS 'milliseconds';

CREATE TABLE pitStops (
raceId INTEGER NOT NULL,
driverId INTEGER NOT NULL,
stop INTEGER NOT NULL,
lap INTEGER NOT NULL,
time TEXT NOT NULL,
duration TEXT,
milliseconds INTEGER,
    PRIMARY KEY (raceId, driverId, stop)
);

ALTER TABLE pitStops ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow read access to pitStops" ON pitStops FOR SELECT USING (true);

COMMENT ON COLUMN pitStops.raceId IS 'the identification number identifying race';
COMMENT ON COLUMN pitStops.driverId IS 'the identification number identifying each driver';
COMMENT ON COLUMN pitStops.stop IS 'stop number';
COMMENT ON COLUMN pitStops.lap IS 'lap number';
COMMENT ON COLUMN pitStops.time IS 'time';
COMMENT ON COLUMN pitStops.duration IS 'duration time';
COMMENT ON COLUMN pitStops.milliseconds IS 'milliseconds';

CREATE TABLE qualifying (
qualifyId INTEGER,
raceId INTEGER NOT NULL,
driverId INTEGER NOT NULL,
constructorId INTEGER NOT NULL,
number INTEGER NOT NULL,
position INTEGER,
q1 TEXT,
q2 TEXT,
q3 TEXT,
    PRIMARY KEY (qualifyId)
);

ALTER TABLE qualifying ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow read access to qualifying" ON qualifying FOR SELECT USING (true);

COMMENT ON COLUMN qualifying.qualifyId IS 'the unique identification number identifying qualifying';
COMMENT ON COLUMN qualifying.raceId IS 'the identification number identifying each race';
COMMENT ON COLUMN qualifying.driverId IS 'the identification number identifying each driver';
COMMENT ON COLUMN qualifying.constructorId IS 'constructor Id';
COMMENT ON COLUMN qualifying.number IS 'number';
COMMENT ON COLUMN qualifying.position IS 'position or track of circuit';
COMMENT ON COLUMN qualifying.q1 IS 'time in qualifying 1';
COMMENT ON COLUMN qualifying.q2 IS 'time in qualifying 2';
COMMENT ON COLUMN qualifying.q3 IS 'time in qualifying 3';

CREATE TABLE status (
statusId INTEGER,
status TEXT NOT NULL,
    PRIMARY KEY (statusId)
);

ALTER TABLE status ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow read access to status" ON status FOR SELECT USING (true);

COMMENT ON COLUMN status.statusId IS 'the unique identification number identifying status';
COMMENT ON COLUMN status.status IS 'full name of status';

CREATE TABLE results (
resultId INTEGER,
raceId INTEGER NOT NULL,
driverId INTEGER NOT NULL,
constructorId INTEGER NOT NULL,
number INTEGER,
grid INTEGER NOT NULL,
position INTEGER,
positionText TEXT NOT NULL,
positionOrder INTEGER NOT NULL,
points DECIMAL(10,2) NOT NULL,
laps INTEGER NOT NULL,
time TEXT,
milliseconds INTEGER,
fastestLap INTEGER,
rank INTEGER,
fastestLapTime TEXT,
fastestLapSpeed TEXT,
statusId INTEGER NOT NULL,
    PRIMARY KEY (resultId)
);

ALTER TABLE results ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow read access to results" ON results FOR SELECT USING (true);

COMMENT ON COLUMN results.resultId IS 'the unique identification number identifying race result';
COMMENT ON COLUMN results.raceId IS 'the identification number identifying the race';
COMMENT ON COLUMN results.driverId IS 'the identification number identifying the driver';
COMMENT ON COLUMN results.constructorId IS 'the identification number identifying which constructors';
COMMENT ON COLUMN results.number IS 'number';
COMMENT ON COLUMN results.grid IS 'the number identifying the area where cars are set into a grid formation in order to start the race.';
COMMENT ON COLUMN results.position IS 'The finishing position or track of circuits';
COMMENT ON COLUMN results.positionOrder IS 'the finishing order of positions';
COMMENT ON COLUMN results.points IS 'points';
COMMENT ON COLUMN results.laps IS 'lap number';
COMMENT ON COLUMN results.time IS 'finish time';
COMMENT ON COLUMN results.milliseconds IS 'the actual finishing time of drivers in milliseconds';
COMMENT ON COLUMN results.fastestLap IS 'fastest lap number';
COMMENT ON COLUMN results.rank IS 'starting rank positioned by fastest lap speed';
COMMENT ON COLUMN results.fastestLapTime IS 'fastest Lap Time';
COMMENT ON COLUMN results.fastestLapSpeed IS 'fastest Lap Speed';
COMMENT ON COLUMN results.statusId IS 'status ID';

