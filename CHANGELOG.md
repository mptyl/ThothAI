# Changelog

All notable changes to ThothAI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

#### Library Updates
- **thoth-dbmanager 0.7.4**: Updated from 0.7.3 to 0.7.4 with Informix FK detection fix
  - Fixed foreign key detection for older Informix versions (10.x and earlier)
  - Uses `sysindexes.part1` instead of unsupported array syntax
  - Verified with 210 FK relationships in olimpix database
  - Removed temporary patch from ThothAI codebase (now fixed upstream)

### Added

#### Database Support & Connectivity
- **Informix Database Support**: Full support for IBM Informix databases with SSH tunnel capability
  - Auto-detection when paramiko is installed
  - Comprehensive documentation and migration files
  - Updated to thoth-dbmanager 0.7.4 with Informix FK detection fix
- **SSH Tunnel Support**: Connect to databases via bastion hosts
  - Support for SSH key-based and password authentication
  - SSH agent forwarding support
  - Configurable SSH authentication methods
  - Python 3.13 compatibility with upstream fixes in thoth-dbmanager 0.6.1
  - Comprehensive test suite for SSH tunnel configurations
- **SQL Server ODBC Drivers**: Added ODBC drivers for SQL Server support in Docker images

#### SQL Generation & Testing
- **RelevanceGuard**: Evidence-based test classification and gating system
  - Language-aware relevance scoring with stopwords filtering
  - Unicode normalization for multilingual support
  - Evidence relevance diagnostics and tracking
  - Configurable relevance thresholds
- **Semantic Test Reducer**: Collapse near-duplicate tests without LLM
  - Conditional activation only when multiple test generators are configured
  - Reduces redundant test execution
  - No additional LLM calls required
- **Model Retry Tracking**: Track and log model retry attempts during SQL generation
  - Detailed retry event logging
  - Integration with ThothLog for diagnostics

#### Database Management
- **SQL Comment Script Download**: Generate and download SQL scripts for database documentation
  - Available for entire databases or individual tables
  - Supports multiple database dialects
  - Admin interface integration
- **Async Database Elements Creation**: Background task processing for database schema analysis
  - Task status tracking with start/end times
  - Progress monitoring through admin interface
  - Dedicated logging system for async operations
  - Task validation framework

#### Visualization & Reporting
- **Local Mermaid Service**: Self-hosted diagram generation replacing mermaid.ink
  - Docker-based service with configurable ports
  - Improved reliability and performance
  - Support for ER diagrams and flowcharts
  - Comprehensive test suite
- **GDPR Compliance CSV Export**: Export GDPR compliance reports to CSV format
  - Full data export for compliance auditing
  - Integration with existing GDPR report views

#### Configuration & Logging
- **Enhanced Logging Configuration**: Simplified dependency management and logging setup
  - Dedicated logging setup module
  - Configurable log levels per service
  - Improved async operation logging
- **Mermaid Service Configuration**: Installer support for mermaid service port and URL configuration

### Changed

#### Dependencies & Compatibility
- **Python 3.13 Support**: Full compatibility with Python 3.13
  - Updated to thoth-dbmanager 0.6.1+ (Python 3.13 compatible)
  - Removed SSH tunnel monkey patches (fixed upstream)
  - Version constraint: requires-python = '>=3.13,<3.14'
- **Docker Base Image**: Updated to support latest ODBC drivers and dependencies

#### Code Quality & Refactoring
- **Evidence-Critical Test Handling**: Migrated to dedicated functions with improved relevance tracking
  - Better separation of concerns
  - Enhanced diagnostic capabilities
- **Template Path Management**: Updated to use direct filename references for better maintainability
- **Task Validation**: Improved validation for comment generation across admin models

### Fixed
- **DISTINCT Keyword Handling**: Properly handle DISTINCT keyword in column names
  - Support for tuple results in query execution
  - Improved SQL parsing robustness

### Removed
- **Deprecated Documentation**: Cleaned up obsolete planning and documentation files
  - Removed WARP.md
  - Removed async database elements planning docs
  - Removed SSH tunnel workaround documentation (fixed upstream)
  - Removed temporary SSH tunnel patch files

### Documentation
- **SSH Tunnel Documentation**: Comprehensive guide for SSH tunnel configuration and troubleshooting
- **Informix Documentation**: Complete setup and usage guide for Informix databases
- **Semantic Test Reducer**: Documentation for test deduplication feature
- **Implementation Guides**: Added guides for async database elements and logging configuration
- **Video Tutorial**: Added video tutorial documentation

### Technical Details

#### Database Dependency Management
- Added scripts for managing database-specific dependencies
- Automatic dependency resolution based on configured databases
- Support for MariaDB, SQL Server, and Informix extras

#### Logging System
- Centralized logging configuration
- Per-service log level control
- Async operation tracking
- Enhanced diagnostic capabilities

#### Testing
- Comprehensive test suite for SSH tunnel configurations
- Integration tests for CSV export functionality
- Mermaid service rendering tests
- Evidence relevance guard tests

---

## Notes

### Breaking Changes
- Python version requirement updated to 3.13+
- SSH tunnel configuration requires new model fields (migration included)

### Migration Guide
- Run Django migrations to add SSH tunnel and async task tracking fields
- Update configuration files to include mermaid service settings
- Review and update database connection settings for SSH tunnel support

### Upgrade Path
1. Update Python to 3.13 if not already installed
2. Run `./install.sh` (Docker) or update dependencies with `uv sync` (local)
3. Apply Django migrations: `python manage.py migrate`
4. Update configuration files from templates
5. Restart all services

---

**Full Changelog**: https://github.com/mptyl/ThothAI/compare/11171d6...HEAD
