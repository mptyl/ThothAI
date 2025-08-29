#!/bin/bash

# Thoth Unified Installation Tool - Linux/macOS
# Installs both ThothAI Backend (Django) and ThothSL Frontend (Streamlit)
# Cross-platform installer with plugin-based dependency management

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALLER_DIR="$SCRIPT_DIR/installer"
PYTHON_SCRIPT="$INSTALLER_DIR/install.py"

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_header() {
    echo
    print_color $CYAN "=============================================="
    print_color $CYAN "🚀 Thoth Unified Installation Tool"
    print_color $CYAN "=============================================="
    print_color $CYAN "   Backend (Django) + Frontend (Streamlit)"
    print_color $CYAN "=============================================="
    echo
}

print_success() {
    print_color $GREEN "✅ $1"
}

print_error() {
    print_color $RED "❌ $1"
}

print_warning() {
    print_color $YELLOW "⚠️  $1"
}

print_info() {
    print_color $CYAN "ℹ️  $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python() {
    local python_cmd=""
    
    # Try different python commands
    for cmd in python3 python; do
        if command_exists "$cmd"; then
            local version=$($cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
            local major=$(echo $version | cut -d. -f1)
            local minor=$(echo $version | cut -d. -f2)
            
            if [ "$major" -eq 3 ] && [ "$minor" -ge 8 ]; then
                python_cmd="$cmd"
                break
            fi
        fi
    done
    
    if [ -z "$python_cmd" ]; then
        print_error "Python 3.8+ is required but not found"
        print_info "Please install Python 3.8 or higher"
        print_info "For macOS: brew install python"
        print_info "For Ubuntu/Debian: sudo apt install python3 python3-pip"
        print_info "For CentOS/RHEL: sudo yum install python3 python3-pip"
        exit 1
    fi
    
    echo "$python_cmd"
}

# Function to activate project virtual environment
activate_project_venv() {
    local project_venv="$SCRIPT_DIR/.venv"
    
    # Check if project .venv exists
    if [ -d "$project_venv" ]; then
        print_info "Found project virtual environment at: $project_venv"
        
        # Check if we're not already in it
        if [ -z "$VIRTUAL_ENV" ] || [ "$VIRTUAL_ENV" != "$project_venv" ]; then
            print_info "Activating project virtual environment..."
            
            # Export the activation for the Python script
            export VIRTUAL_ENV="$project_venv"
            export PATH="$project_venv/bin:$PATH"
            
            print_success "Virtual environment activated: $(basename $project_venv)"
            return 0
        else
            print_success "Already using project virtual environment: $(basename $VIRTUAL_ENV)"
            return 0
        fi
    else
        return 1
    fi
}

# Function to create and activate virtual environment
create_and_activate_venv() {
    local python_cmd=$1
    local venv_path="$SCRIPT_DIR/.venv"
    
    # Check if project .venv already exists
    if [ -d "$venv_path" ]; then
        print_info "Found existing virtual environment at: $venv_path"
    else
        print_info "Creating virtual environment at: $venv_path"
        $python_cmd -m venv "$venv_path"
        print_success "Virtual environment created"
    fi
    
    # Activate the virtual environment
    print_info "Activating virtual environment..."
    export VIRTUAL_ENV="$venv_path"
    export PATH="$venv_path/bin:$PATH"
    
    # Verify activation worked
    if [ "$VIRTUAL_ENV" = "$venv_path" ]; then
        print_success "Virtual environment activated: $(basename $VIRTUAL_ENV)"
        
        # Upgrade pip in the virtual environment
        print_info "Upgrading pip in virtual environment..."
        "$venv_path/bin/python" -m pip install --upgrade pip
        
        return 0
    else
        print_error "Failed to activate virtual environment"
        return 1
    fi
}

# Function to check virtual environment
check_virtual_env() {
    local python_cmd=$1
    
    # First try to activate project .venv if it exists
    if activate_project_venv; then
        return 0
    fi
    
    # If no project .venv and not in any virtual environment, create one
    if [ -z "$VIRTUAL_ENV" ]; then
        print_info "No virtual environment detected"
        create_and_activate_venv "$python_cmd"
        return $?
    else
        print_success "Virtual environment detected: $(basename $VIRTUAL_ENV)"
        return 0
    fi
}

# Function to check pip
check_pip() {
    local python_cmd=$1
    
    if ! $python_cmd -m pip --version >/dev/null 2>&1; then
        print_error "pip is not available"
        print_info "Please install pip for Python 3"
        exit 1
    fi
    
    # Check if pip is up to date
    local pip_version=$($python_cmd -m pip --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    print_success "pip $pip_version detected"
}

# Function to check Docker
check_docker() {
    if command_exists docker; then
        local docker_version=$(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
        print_success "Docker $docker_version detected"
        
        if command_exists docker-compose || docker compose version >/dev/null 2>&1; then
            print_success "Docker Compose detected"
            return 0
        else
            print_warning "Docker Compose not found"
            print_info "Install with: pip install docker-compose"
            return 1
        fi
    else
        print_warning "Docker not found"
        print_info "Docker is optional but recommended for easy deployment"
        print_info "Install from: https://docs.docker.com/get-docker/"
        return 1
    fi
}

# Function to show help
show_help() {
    print_header
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "This unified installer sets up both:"
    echo "  • ThothAI Backend (Django) - Configuration and metadata management"  
    echo "  • ThothSL Frontend (Streamlit) - Natural language to SQL interface"
    echo
    echo "OPTIONS:"
    echo "  --help, -h              Show this help message"
    echo "  --db DATABASE           Comma-separated list of databases"
    echo "  --vdb VECTORDB          Comma-separated list of vector databases"
    echo "  --auto                  Auto-rebuild and start Docker containers (default)"
    echo "  --manual                Manual mode - only generate requirements"
    echo "  --show-config           Show current configuration"
    echo "  --reset                 Reset configuration to defaults"
    echo "  --check-deps            Check system dependencies only"
    echo "  --create-venv           Create virtual environment and exit"
    echo "  --verbose               Show detailed Docker build output"
    echo "  --backend-only          Install only the backend components"
    echo "  --frontend-only         Install only the frontend components"
    echo
    echo "DOCKER INTEGRATION:"
    echo "  --auto                  Automatically rebuild Docker images and start containers"
    echo "  --manual                Generate requirements only, manual Docker startup required"
    echo
    echo "EXAMPLES:"
    echo "  $0                                    # Interactive mode with auto Docker"
    echo "  $0 --db postgresql,sqlite             # Install with specific databases (auto)"
    echo "  $0 --vdb qdrant,chroma --manual      # Install vector DBs, manual Docker startup"
    echo "  $0 --backend-only --auto             # Install only backend with Docker"
    echo "  $0 --show-config                     # Show current configuration"
    echo "  $0 --reset                           # Reset to defaults"
    echo
    echo "DEFAULT CONFIGURATION:"
    echo "  Databases: PostgreSQL + SQLite"
    echo "  Vector DB: Qdrant"
    echo "  Docker: Auto mode (rebuild and start both backend and frontend)"
    echo "  Virtual Environment: Automatically created at ./.venv if not present"
    echo
    echo "SUPPORTED DATABASES:"
    echo "  postgresql, mysql, sqlite, oracle, sqlserver, mariadb, supabase"
    echo
    echo "SUPPORTED VECTOR DATABASES:"
    echo "  qdrant, weaviate, milvus, chroma, pgvector, pinecone"
    echo
    echo "ACCESS POINTS AFTER INSTALLATION:"
    echo "  🌐 Backend (Django): http://localhost:8040"
    echo "  🎯 Frontend (Streamlit): http://localhost:8501"
    echo "  📊 Admin Panel: http://localhost:8040/admin"
    echo "  🔍 Qdrant Dashboard: http://localhost:6333/dashboard"
    echo
}

# Function to check system dependencies
check_system_deps() {
    print_info "Checking system dependencies for Thoth..."
    
    local python_cmd=$(check_python)
    print_success "Python: $($python_cmd --version)"
    
    check_pip "$python_cmd"
    
    # Check Docker (optional but recommended)
    check_docker
    
    # Check for common system libraries that might be needed
    local missing_libs=()
    
    # Check for development headers (needed for some packages)
    if command_exists pkg-config; then
        print_success "pkg-config: Available"
    else
        missing_libs+=("pkg-config")
    fi
    
    # Check for git (might be needed for some packages)
    if command_exists git; then
        print_success "git: $(git --version)"
    else
        missing_libs+=("git")
    fi
    
    # Platform-specific checks
    case "$(uname -s)" in
        Linux*)
            # Check for build essentials on Linux
            if command_exists gcc; then
                print_success "gcc: Available"
            else
                missing_libs+=("build-essential")
            fi
            
            # Check for common library dependencies
            for lib in libffi-dev libssl-dev; do
                if ldconfig -p | grep -q "$lib" 2>/dev/null; then
                    print_success "$lib: Available"
                else
                    missing_libs+=("$lib")
                fi
            done
            ;;
        Darwin*)
            # Check for Xcode command line tools on macOS
            if xcode-select -p >/dev/null 2>&1; then
                print_success "Xcode command line tools: Available"
            else
                print_warning "Xcode command line tools not found"
                print_info "Install with: xcode-select --install"
            fi
            
            # Check for Homebrew (recommended)
            if command_exists brew; then
                print_success "Homebrew: Available"
            else
                print_info "Homebrew not found (optional but recommended)"
                print_info "Install from: https://brew.sh/"
            fi
            ;;
    esac
    
    if [ ${#missing_libs[@]} -gt 0 ]; then
        print_warning "Missing system dependencies: ${missing_libs[*]}"
        case "$(uname -s)" in
            Linux*)
                if command_exists apt-get; then
                    print_info "Install with: sudo apt-get install ${missing_libs[*]}"
                elif command_exists yum; then
                    print_info "Install with: sudo yum install ${missing_libs[*]}"
                elif command_exists dnf; then
                    print_info "Install with: sudo dnf install ${missing_libs[*]}"
                fi
                ;;
            Darwin*)
                if command_exists brew; then
                    print_info "Install with: brew install ${missing_libs[*]}"
                fi
                ;;
        esac
    else
        print_success "All system dependencies available"
    fi
}

# Function to check Thoth project structure requirements
check_thoth_requirements() {
    print_info "Checking Thoth project structure..."
    
    # Check for backend components
    if [ -d "$SCRIPT_DIR/thoth_be" ]; then
        print_success "Backend directory found: thoth_be/"
        if [ -f "$SCRIPT_DIR/thoth_be/manage.py" ]; then
            print_success "Django manage.py found"
        else
            print_warning "Django manage.py not found in thoth_be/"
        fi
    else
        print_warning "Backend directory not found: thoth_be/"
        print_info "Backend installation may not work correctly"
    fi
    
    # Check for frontend components
    if [ -d "$SCRIPT_DIR/thoth_sl" ]; then
        print_success "Frontend directory found: thoth_sl/"
        if [ -f "$SCRIPT_DIR/thoth_sl/ThothAI.py" ]; then
            print_success "Streamlit ThothAI.py found"
        else
            print_warning "Streamlit ThothAI.py not found in thoth_sl/"
        fi
    else
        print_warning "Frontend directory not found: thoth_sl/"
        print_info "Frontend installation may not work correctly"
    fi
    
    # Check for Docker Compose files
    local docker_files_found=0
    if [ -f "$SCRIPT_DIR/thoth_be/docker-compose.yml" ]; then
        print_success "Backend docker-compose.yml found"
        docker_files_found=$((docker_files_found + 1))
    fi
    
    if [ -f "$SCRIPT_DIR/thoth_sl/docker-compose.yml" ]; then
        print_success "Frontend docker-compose.yml found"
        docker_files_found=$((docker_files_found + 1))
    fi
    
    if [ $docker_files_found -eq 0 ]; then
        print_warning "No docker-compose.yml files found"
        print_info "Docker deployment may not be available"
    fi
}

# Main installation function
main() {
    # Parse command line arguments
    local python_args=()
    local show_help_flag=false
    local check_deps_only=false
    local create_venv_only=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help_flag=true
                shift
                ;;
            --check-deps)
                check_deps_only=true
                shift
                ;;
            --create-venv)
                create_venv_only=true
                shift
                ;;
            --db|--databases)
                python_args+=("--db" "$2")
                shift 2
                ;;
            --vdb|--vectordbs)
                python_args+=("--vdb" "$2")
                shift 2
                ;;
            --auto)
                python_args+=("--auto")
                shift
                ;;
            --manual)
                python_args+=("--manual")
                shift
                ;;
            --show-config)
                python_args+=("--show-config")
                shift
                ;;
            --reset)
                python_args+=("--reset")
                shift
                ;;
            --verbose)
                python_args+=("--verbose")
                shift
                ;;
            --backend-only)
                python_args+=("--backend-only")
                shift
                ;;
            --frontend-only)
                python_args+=("--frontend-only")
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Show help if requested
    if [ "$show_help_flag" = true ]; then
        show_help
        exit 0
    fi
    
    print_header
    
    # Check system dependencies
    check_system_deps
    check_thoth_requirements
    
    if [ "$check_deps_only" = true ]; then
        print_success "System dependency check completed"
        exit 0
    fi
    
    # Get Python command
    local python_cmd=$(check_python)
    
    # Handle virtual environment creation
    if [ "$create_venv_only" = true ]; then
        create_and_activate_venv "$python_cmd"
        print_success "Virtual environment created successfully"
        print_info "Activate it with: source $SCRIPT_DIR/.venv/bin/activate"
        exit 0
    fi
    
    # Check if installer script exists
    if [ ! -f "$PYTHON_SCRIPT" ]; then
        print_error "Installation script not found: $PYTHON_SCRIPT"
        print_info "Make sure you're running this from the Thoth project root directory"
        exit 1
    fi
    
    # Virtual environment check and automatic creation
    check_virtual_env "$python_cmd"
    
    print_info "Starting Thoth unified installation..."
    echo
    
    # Run the Python installer
    if [ ${#python_args[@]} -gt 0 ]; then
        # Non-interactive mode with arguments
        $python_cmd "$PYTHON_SCRIPT" "${python_args[@]}"
    else
        # Interactive mode
        $python_cmd "$PYTHON_SCRIPT"
    fi
    
    local exit_code=$?
    
    echo
    if [ $exit_code -eq 0 ]; then
        print_success "Thoth installation completed successfully!"
        echo
        # Check if manual mode was used
        if [[ "${python_args[*]}" =~ "--manual" ]]; then
            print_info "Manual mode - start Thoth components with:"
            print_info "  Backend:  cd thoth_be && docker compose up --build"
            print_info "  Frontend: cd thoth_sl && docker compose up --build"
            print_info "  OR run both: docker compose -f thoth_be/docker-compose.yml -f thoth_sl/docker-compose.yml up --build"
        else
            print_info "Thoth should now be running at:"
            print_info "  🌐 Backend (Django): http://localhost:8040"
            print_info "  🎯 Frontend (Streamlit): http://localhost:8501"
            print_info "  📊 Admin Panel: http://localhost:8040/admin"
            print_info "  🔍 Qdrant Dashboard: http://localhost:6333/dashboard"
        fi
        echo
        print_info "Additional steps:"
        print_info "1. Verify backend: python -c \"import thoth_core; print('Backend OK!')\""
        print_info "2. Verify frontend: python -c \"import streamlit; print('Frontend OK!')\""
        print_info "3. Check Docker logs: docker compose logs"
        print_info "4. Configure workspaces and AI providers as needed"
    else
        print_error "Thoth installation failed with exit code $exit_code"
        print_info "Check the error messages above for details"
        print_info "Common solutions:"
        print_info "1. Make sure you have Python 3.8+ installed"
        print_info "2. Ensure you have sufficient disk space"
        print_info "3. Check your internet connection for package downloads"
        print_info "4. Try running with --verbose for more details"
        print_info "5. For manual installation, use --manual flag"
    fi
    
    exit $exit_code
}

# Trap to handle interruption
trap 'echo; print_warning "Thoth installation interrupted by user"; exit 130' INT

# Run main function with all arguments  
main "$@"