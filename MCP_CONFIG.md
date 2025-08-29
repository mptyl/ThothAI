# MCP Server Configuration for Thoth Projects

## Overview

This document describes the Model Context Protocol (MCP) server configuration implemented for the Thoth project ecosystem. The configuration provides enhanced context management and AI assistance capabilities across all four main Thoth projects through Claude Code in VSCode.

## Architecture

### Configuration Strategy
- **Project-specific MCP configurations**: Each project has its own `.mcp.json` file
- **Isolated server instances**: Each project runs dedicated MCP servers for security and performance
- **Consistent server stack**: All projects use the same three core MCP servers
- **Environment-specific context**: Each server receives project-specific environment variables

### Supported Projects
1. **thoth_be** - Backend services and APIs
2. **thoth_ui** - Frontend user interface
3. **thoth_sqldb2** - SQL database management
4. **thoth_vdb2** - Vector database operations

## MCP Servers

### 1. Context7 Server
**Purpose**: Enhanced context management and code understanding

**Configuration**:
```json
"context7-thoth-[project]": {
  "command": "npx",
  "args": ["-y", "@upstash/context7-mcp@latest"],
  "env": {
    "DEFAULT_MINIMUM_TOKENS": "10000",
    "PROJECT_ROOT": "/Users/mp/Thoth/[project]",
    "PROJECT_NAME": "[Project Display Name]",
    "PROJECT_DESCRIPTION": "[Project Description]"
  }
}
```

**Features**:
- Project-aware context management
- Minimum 10,000 tokens for comprehensive analysis
- Project-specific root directory awareness
- Descriptive metadata for better understanding

### 2. Filesystem Server
**Purpose**: Secure file system access limited to project scope

**Configuration**:
```json
"filesystem": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/mp/Thoth/[project]"],
  "env": {}
}
```

**Features**:
- Read/write access to project files
- Directory traversal within project boundaries
- File content analysis and modification
- Security isolation per project

### 3. Sequential Thinking Server
**Purpose**: Structured problem-solving and planning capabilities

**Configuration**:
```json
"sequential-thinking": {
  "command": "npx", 
  "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
  "env": {}
}
```

**Features**:
- Multi-step reasoning processes
- Complex problem decomposition
- Planning and strategy development
- Iterative solution refinement

## Project-Specific Configurations

### thoth_be (Backend)
**File**: `/Users/mp/Thoth/thoth_be/.mcp.json`
**Context**: Backend services, APIs, server-side logic
**Environment Variables**:
- `PROJECT_NAME`: "Thoth Backend"
- `PROJECT_DESCRIPTION`: "Backend services and APIs for the Thoth project"

### thoth_ui (Frontend)
**File**: `/Users/mp/Thoth/thoth_ui/.mcp.json`
**Context**: User interface, React components, frontend logic
**Environment Variables**:
- `PROJECT_NAME`: "Thoth UI"
- `PROJECT_DESCRIPTION`: "Frontend user interface for the Thoth project"

### thoth_sqldb2 (SQL Database)
**File**: `/Users/mp/Thoth/thoth_sqldb2/.mcp.json`
**Context**: Database schemas, SQL operations, data management
**Environment Variables**:
- `PROJECT_NAME`: "Thoth SQL Database"
- `PROJECT_DESCRIPTION`: "SQL database management and operations for the Thoth project"

### thoth_vdb2 (Vector Database)
**File**: `/Users/mp/Thoth/thoth_vdb2/.mcp.json`
**Context**: Vector operations, embeddings, similarity search
**Environment Variables**:
- `PROJECT_NAME`: "Thoth Vector Database"
- `PROJECT_DESCRIPTION`: "Vector database management and operations for the Thoth project"

## Usage with Claude Code

### Activation
1. Open a Thoth project folder in VSCode
2. Claude Code automatically detects the `.mcp.json` file
3. Approve MCP server activation when prompted
4. Servers initialize and become available

### Available Commands
- **Context7**: `@context7-thoth-[project]` - Project-specific context analysis
- **Filesystem**: `@filesystem` - File operations within project scope
- **Sequential Thinking**: `@sequential-thinking` - Structured problem solving

### Keyboard Shortcuts
- `Cmd + Escape` (Mac) / `Ctrl + Escape` (Windows/Linux) - Open Claude Code
- `Cmd + Alt + K` (Mac) / `Ctrl + Alt + K` (Windows/Linux) - Insert @-mention

## Security Features

### Project Isolation
- Each project's filesystem server is restricted to its directory
- No cross-project file access
- Independent server processes per project

### Permission Management
- Explicit approval required for each MCP server
- Granular control through VSCode settings
- Option to enable/disable servers per project

### Environment Separation
- Project-specific environment variables
- Isolated context boundaries
- No shared state between projects

## Performance Optimization

### Server Efficiency
- On-demand server initialization
- Project-scoped resource allocation
- Minimal memory footprint per server

### Context Management
- 10,000 minimum tokens for comprehensive analysis
- Project-aware context boundaries
- Efficient token utilization

### Caching Strategy
- NPX package caching for faster startup
- Server process reuse within sessions
- Optimized context retrieval

## Troubleshooting

### Common Issues
1. **Servers not loading**: Check internet connection and Node.js installation
2. **Permission denied**: Verify VSCode MCP server permissions
3. **Context7 errors**: Ensure project root paths are correct
4. **Filesystem access**: Confirm project directory permissions

### Log Locations
- VSCode Output panel: "Claude Code" channel
- MCP server logs: VSCode logs directory
- Error details: Claude Code extension logs

### Configuration Validation
- Verify `.mcp.json` syntax with JSON validator
- Check file paths exist and are accessible
- Confirm NPX and Node.js are available in PATH

## Maintenance

### Updates
- MCP servers auto-update via NPX latest tags
- Configuration files require manual updates
- VSCode extension updates automatically

### Monitoring
- Check server status in Claude Code interface
- Monitor performance through VSCode diagnostics
- Review logs for error patterns

### Backup
- Configuration files backed up to `/Users/mp/mcp_backup_[timestamp]/`
- Original configurations preserved before changes
- Easy rollback capability available

## Integration Benefits

### Development Workflow
- Seamless AI assistance within VSCode
- Project-aware code suggestions
- Contextual problem solving

### Code Quality
- Enhanced code analysis capabilities
- Structured refactoring assistance
- Comprehensive project understanding

### Productivity
- Reduced context switching
- Intelligent file navigation
- Automated documentation assistance

---

**Configuration Date**: August 6, 2025  
**Version**: 1.0  
**Maintainer**: Thoth Project Team

## Advanced Configuration

### Custom Environment Variables
Each project can be customized by modifying the `env` section in `.mcp.json`:

```json
"env": {
  "DEFAULT_MINIMUM_TOKENS": "15000",
  "PROJECT_ROOT": "/Users/mp/Thoth/thoth_be",
  "PROJECT_NAME": "Thoth Backend",
  "PROJECT_DESCRIPTION": "Backend services and APIs for the Thoth project",
  "CUSTOM_CONTEXT_RULES": "focus_on_api_design,security_first",
  "LANGUAGE_PREFERENCE": "python",
  "FRAMEWORK_CONTEXT": "fastapi,sqlalchemy"
}
```

### Server-Specific Customization

#### Context7 Advanced Options
```json
"context7-thoth-be": {
  "command": "npx",
  "args": ["-y", "@upstash/context7-mcp@latest", "--verbose"],
  "env": {
    "DEFAULT_MINIMUM_TOKENS": "15000",
    "MAX_CONTEXT_SIZE": "50000",
    "CONTEXT_STRATEGY": "hierarchical",
    "PROJECT_ROOT": "/Users/mp/Thoth/thoth_be"
  }
}
```

#### Filesystem Server Restrictions
```json
"filesystem": {
  "command": "npx",
  "args": [
    "-y", 
    "@modelcontextprotocol/server-filesystem", 
    "/Users/mp/Thoth/thoth_be",
    "--allowed-extensions", "py,json,md,yml,yaml",
    "--max-file-size", "1MB"
  ],
  "env": {
    "READ_ONLY_PATHS": "config/,secrets/",
    "EXCLUDED_PATTERNS": "*.log,*.tmp,__pycache__"
  }
}
```

## Practical Usage Examples

### Backend Development (thoth_be)
```
# API Analysis
@context7-thoth-be Analyze the current API structure and suggest improvements for scalability

# Database Integration
@filesystem Show me all database models and their relationships

# Code Review
@sequential-thinking Review this FastAPI endpoint for security vulnerabilities and performance issues
```

### Frontend Development (thoth_ui)
```
# Component Analysis
@context7-thoth-ui Analyze this React component and suggest optimization opportunities

# State Management
@filesystem Find all Redux/state management files and show their structure

# UI/UX Planning
@sequential-thinking Plan the implementation of a new dashboard component with responsive design
```

### Database Operations (thoth_sqldb2)
```
# Schema Analysis
@context7-thoth-sqldb Review the database schema and identify normalization opportunities

# Migration Planning
@sequential-thinking Plan a database migration strategy for the new user authentication system

# Query Optimization
@filesystem Show me all SQL queries that might need performance optimization
```

### Vector Database (thoth_vdb2)
```
# Embedding Analysis
@context7-thoth-vdb Analyze the current embedding strategy and suggest improvements

# Search Optimization
@filesystem Review vector search implementations and identify bottlenecks

# Scaling Strategy
@sequential-thinking Design a strategy for scaling vector operations to handle 10x more data
```

## Configuration Templates

### Development Environment
```json
{
  "mcpServers": {
    "context7-dev": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"],
      "env": {
        "DEFAULT_MINIMUM_TOKENS": "8000",
        "ENVIRONMENT": "development",
        "DEBUG_MODE": "true",
        "PROJECT_ROOT": "/Users/mp/Thoth/[project]"
      }
    }
  }
}
```

### Production Environment
```json
{
  "mcpServers": {
    "context7-prod": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"],
      "env": {
        "DEFAULT_MINIMUM_TOKENS": "12000",
        "ENVIRONMENT": "production",
        "PERFORMANCE_MODE": "true",
        "SECURITY_LEVEL": "high"
      }
    }
  }
}
```

## File Structure

```
/Users/mp/Thoth/
├── MCP_CONFIG.md                    # This documentation
├── thoth_be/
│   └── .mcp.json                   # Backend MCP configuration
├── thoth_ui/
│   └── .mcp.json                   # Frontend MCP configuration
├── thoth_sqldb2/
│   └── .mcp.json                   # SQL DB MCP configuration
├── thoth_vdb2/
│   └── .mcp.json                   # Vector DB MCP configuration
└── mcp_backup_[timestamp]/         # Configuration backups
    ├── thoth_be_claude/
    ├── thoth_ui_claude/
    ├── thoth_sqldb2_claude/
    └── thoth_vdb2_claude/
```

## Version History

### v1.0 (August 6, 2025)
- Initial MCP configuration implementation
- Project-specific `.mcp.json` files created
- Context7, Filesystem, and Sequential Thinking servers configured
- Security isolation implemented
- Documentation created

## Quick Reference

### Server Names by Project
- **thoth_be**: `@context7-thoth-be`, `@filesystem`, `@sequential-thinking`
- **thoth_ui**: `@context7-thoth-ui`, `@filesystem`, `@sequential-thinking`
- **thoth_sqldb2**: `@context7-thoth-sqldb`, `@filesystem`, `@sequential-thinking`
- **thoth_vdb2**: `@context7-thoth-vdb`, `@filesystem`, `@sequential-thinking`

### Configuration Files
- Backend: `/Users/mp/Thoth/thoth_be/.mcp.json`
- Frontend: `/Users/mp/Thoth/thoth_ui/.mcp.json`
- SQL DB: `/Users/mp/Thoth/thoth_sqldb2/.mcp.json`
- Vector DB: `/Users/mp/Thoth/thoth_vdb2/.mcp.json`

### Backup Location
- `/Users/mp/mcp_backup_20250806_171230/`
