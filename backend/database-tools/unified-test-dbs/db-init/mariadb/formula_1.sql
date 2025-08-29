-- MariaDB schema for formula_1 database
CREATE DATABASE IF NOT EXISTS formula_1;
USE formula_1;

CREATE TABLE circuits (
circuitId INT PRIMARY KEY  COMMENT 'unique identification number of the circuit',
circuitRef TEXT NOT NULL COMMENT 'circuit reference name',
name TEXT NOT NULL COMMENT 'full name of circuit',
location TEXT  COMMENT 'location of circuit',
country TEXT  COMMENT 'country of circuit',
lat DECIMAL(10,2)  COMMENT 'latitude of location of circuit',
lng DECIMAL(10,2)  COMMENT 'longitude of location of circuit',
alt INT,
url TEXT NOT NULL COMMENT 'url'
);

CREATE TABLE constructors (
constructorId INT PRIMARY KEY  COMMENT 'the unique identification number identifying constructors',
constructorRef TEXT NOT NULL COMMENT 'Constructor Reference name',
name TEXT NOT NULL COMMENT 'full name of the constructor',
nationality TEXT  COMMENT 'nationality of the constructor',
url TEXT NOT NULL COMMENT 'the introduction website of the constructor'
);

CREATE TABLE drivers (
driverId INT PRIMARY KEY  COMMENT 'the unique identification number identifying each driver',
driverRef TEXT NOT NULL COMMENT 'driver reference name',
number INT  COMMENT 'number',
code TEXT  COMMENT 'abbreviated code for drivers',
forename TEXT NOT NULL COMMENT 'forename',
surname TEXT NOT NULL COMMENT 'surname',
dob DATE  COMMENT 'date of birth',
nationality TEXT  COMMENT 'nationality of drivers',
url TEXT NOT NULL COMMENT 'the introduction website of the drivers'
);

CREATE TABLE seasons (
year INT PRIMARY KEY NOT NULL COMMENT 'the unique identification number identifying the race',
url TEXT NOT NULL COMMENT 'website link of season race introduction'
);

CREATE TABLE races (
raceId INT PRIMARY KEY  COMMENT 'the unique identification number identifying the race',
year INT NOT NULL COMMENT 'year',
round INT NOT NULL COMMENT 'round',
circuitId INT NOT NULL COMMENT 'circuit Id',
name TEXT NOT NULL COMMENT 'name of the race',
date DATE NOT NULL COMMENT 'duration time',
time TEXT  COMMENT 'time of the location',
url TEXT  COMMENT 'introduction of races'
);

CREATE TABLE constructorResults (
constructorResultsId INT PRIMARY KEY  COMMENT 'constructor Results Id',
raceId INT NOT NULL COMMENT 'race id',
constructorId INT NOT NULL COMMENT 'constructor id',
points DECIMAL(10,2)  COMMENT 'points',
status TEXT  COMMENT 'status'
);

CREATE TABLE constructorStandings (
constructorStandingsId INT PRIMARY KEY  COMMENT 'unique identification of the constructor standing records',
raceId INT NOT NULL COMMENT 'id number identifying which races',
constructorId INT NOT NULL COMMENT 'id number identifying which id',
points DECIMAL(10,2) NOT NULL COMMENT 'how many points acquired in each race',
position INT  COMMENT 'position or track of circuits',
positionText TEXT,
wins INT NOT NULL COMMENT 'wins'
);

CREATE TABLE driverStandings (
driverStandingsId INT PRIMARY KEY  COMMENT 'the unique identification number identifying driver standing records',
raceId INT NOT NULL COMMENT 'id number identifying which races',
driverId INT NOT NULL COMMENT 'id number identifying which drivers',
points DECIMAL(10,2) NOT NULL COMMENT 'how many points acquired in each race',
position INT  COMMENT 'position or track of circuits',
positionText TEXT,
wins INT NOT NULL COMMENT 'wins'
);

CREATE TABLE lapTimes (
raceId INT NOT NULL COMMENT 'the identification number identifying race',
driverId INT NOT NULL COMMENT 'the identification number identifying each driver',
lap INT NOT NULL COMMENT 'lap number',
position INT  COMMENT 'position or track of circuits',
time TEXT  COMMENT 'lap time',
milliseconds INT  COMMENT 'milliseconds',
PRIMARY KEY (raceId, driverId, lap)
);

CREATE TABLE pitStops (
raceId INT NOT NULL COMMENT 'the identification number identifying race',
driverId INT NOT NULL COMMENT 'the identification number identifying each driver',
stop INT NOT NULL COMMENT 'stop number',
lap INT NOT NULL COMMENT 'lap number',
time TEXT NOT NULL COMMENT 'time',
duration TEXT  COMMENT 'duration time',
milliseconds INT  COMMENT 'milliseconds',
PRIMARY KEY (raceId, driverId, stop)
);

CREATE TABLE qualifying (
qualifyId INT PRIMARY KEY  COMMENT 'the unique identification number identifying qualifying',
raceId INT NOT NULL COMMENT 'the identification number identifying each race',
driverId INT NOT NULL COMMENT 'the identification number identifying each driver',
constructorId INT NOT NULL COMMENT 'constructor Id',
number INT NOT NULL COMMENT 'number',
position INT  COMMENT 'position or track of circuit',
q1 TEXT  COMMENT 'time in qualifying 1',
q2 TEXT  COMMENT 'time in qualifying 2',
q3 TEXT  COMMENT 'time in qualifying 3'
);

CREATE TABLE status (
statusId INT PRIMARY KEY  COMMENT 'the unique identification number identifying status',
status TEXT NOT NULL COMMENT 'full name of status'
);

CREATE TABLE results (
resultId INT PRIMARY KEY  COMMENT 'the unique identification number identifying race result',
raceId INT NOT NULL COMMENT 'the identification number identifying the race',
driverId INT NOT NULL COMMENT 'the identification number identifying the driver',
constructorId INT NOT NULL COMMENT 'the identification number identifying which constructors',
number INT  COMMENT 'number',
grid INT NOT NULL COMMENT 'the number identifying the area where cars are set into a grid formation in order to start the race.',
position INT  COMMENT 'The finishing position or track of circuits',
positionText TEXT NOT NULL,
positionOrder INT NOT NULL COMMENT 'the finishing order of positions',
points DECIMAL(10,2) NOT NULL COMMENT 'points',
laps INT NOT NULL COMMENT 'lap number',
time TEXT  COMMENT 'finish time',
milliseconds INT  COMMENT 'the actual finishing time of drivers in milliseconds',
fastestLap INT  COMMENT 'fastest lap number',
rank INT  COMMENT 'starting rank positioned by fastest lap speed',
fastestLapTime TEXT  COMMENT 'fastest Lap Time',
fastestLapSpeed TEXT  COMMENT 'fastest Lap Speed',
statusId INT NOT NULL COMMENT 'status ID'
);

