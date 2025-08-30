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
Thoth Unified Installation Tool
Manages plugin-based dependencies for both ThothAI Backend and ThothSL Frontend
Combines thoth-dbmanager and thoth-vdbmanager installation with Docker orchestration
"""

import json
import os
import sys
import subprocess
import platform
import uuid
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
import argparse


class ThothUnifiedInstaller:
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir.parent
        self.configs_dir = self.script_dir / "configs"
        self.templates_dir = self.script_dir / "requirements-templates"
        
        # Component paths
        self.backend_dir = self.project_root / "thoth_be"
        self.frontend_dir = self.project_root / "thoth_sl"
        
        # Load configuration files
        self.db_plugins = self._load_config("database-plugins.json")
        self.vdb_plugins = self._load_config("vectordb-plugins.json")
        self.dependency_map = self._load_config("dependency-map.json")
        self.user_prefs = self._load_user_preferences()
        
        # Installation state
        self.selected_databases: Set[str] = set()
        self.selected_vectordbs: Set[str] = set()
        
        # Component selection
        self.install_backend = True
        self.install_frontend = True
        
    def _load_config(self, filename: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        config_path = self.configs_dir / filename
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ Configuration file not found: {config_path}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in {config_path}: {e}")
            sys.exit(1)
    
    def _load_user_preferences(self) -> Dict[str, Any]:
        """Load user preferences, create if doesn't exist"""
        prefs_path = self.configs_dir / "user-preferences.json"
        if prefs_path.exists():
            with open(prefs_path, 'r', encoding='utf-8') as f:
                prefs = json.load(f)
        else:
            prefs = {
                "version": "2.0",
                "last_updated": None,
                "installation_id": str(uuid.uuid4()),
                "selected_databases": ["postgresql", "sqlite"],
                "selected_vectordbs": ["qdrant"],
                "installation_history": [],
                "environment": {
                    "python_version": None,
                    "platform": None,
                    "virtual_env": None
                },
                "rollback_points": [],
                "unified_config": {
                    "backend_enabled": True,
                    "frontend_enabled": True,
                    "backend_port": 8040,
                    "frontend_port": 8501,
                    "auto_docker": True,
                    "enable_monitoring": True
                },
                "installation_preferences": {
                    "auto_docker": True,
                    "create_venv": True,
                    "install_dev_tools": False,
                    "enable_jupyter": False,
                    "verbose_docker": False
                }
            }
        
        # Update environment info
        prefs["environment"]["python_version"] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        prefs["environment"]["platform"] = platform.system()
        prefs["environment"]["virtual_env"] = os.environ.get('VIRTUAL_ENV') is not None
        
        return prefs
    
    def save_user_preferences(self):
        """Save current user preferences"""
        self.user_prefs["last_updated"] = datetime.now().isoformat()
        self.user_prefs["selected_databases"] = list(self.selected_databases)
        self.user_prefs["selected_vectordbs"] = list(self.selected_vectordbs)
        
        prefs_path = self.configs_dir / "user-preferences.json"
        with open(prefs_path, 'w', encoding='utf-8') as f:
            json.dump(self.user_prefs, f, indent=2)
    
    def show_welcome(self):
        """Display welcome message"""
        print("🚀 Thoth Unified Installation Tool")
        print("=" * 50)
        print("Configure your complete Thoth installation:")
        print("  • ThothAI Backend (Django) - Configuration and metadata management")
        print("  • ThothSL Frontend (Streamlit) - Natural language to SQL interface")
        print()
        
        if self.user_prefs.get("selected_databases") or self.user_prefs.get("selected_vectordbs"):
            print("📋 Previous Configuration Found:")
            if self.user_prefs.get("selected_databases"):
                db_names = [self.db_plugins["database_managers"][db]["display_name"] 
                           for db in self.user_prefs["selected_databases"] 
                           if db in self.db_plugins["database_managers"]]
                print(f"   Databases: {', '.join(db_names)}")
            
            if self.user_prefs.get("selected_vectordbs"):
                vdb_names = [self.vdb_plugins["vector_databases"][vdb]["display_name"] 
                            for vdb in self.user_prefs["selected_vectordbs"] 
                            if vdb in self.vdb_plugins["vector_databases"]]
                print(f"   Vector DBs: {', '.join(vdb_names)}")
            print()
    
    def interactive_database_selection(self):
        """Interactive database manager selection with spacebar toggle"""
        print("📊 Select Database Managers:")
        print("-" * 30)
        print("Use SPACE to select/deselect, ENTER to continue")
        print()
        
        db_managers = self.db_plugins["database_managers"]
        
        # Load previous selection as current selection
        if self.user_prefs.get("selected_databases"):
            self.selected_databases = set(self.user_prefs["selected_databases"])
        else:
            # Use defaults if no previous selection
            self.selected_databases = {key for key, info in db_managers.items() if info.get("default", False)}
        
        options = list(db_managers.items())
        current_index = 0
        
        while True:
            # Clear screen
            print("\033[2J\033[H", end="")
            print("🚀 Thoth Unified Installation Tool")
            print("=" * 50)
            print()
            print("📊 Select Database Managers:")
            print("-" * 30)
            print("Use SPACE to select/deselect, ↑↓ to navigate, ENTER to continue")
            print()
            
            for i, (key, info) in enumerate(options):
                prefix = ">" if i == current_index else " "
                selected = "✓" if key in self.selected_databases else " "
                print(f"{prefix} [{selected}] {info['display_name']}")
                if i == current_index:
                    print(f"     {info['description']}")
            
            print(f"\nSelected: {len(self.selected_databases)} database(s)")
            if self.selected_databases:
                selected_names = [db_managers[db]["display_name"] for db in self.selected_databases]
                print(f"Current: {', '.join(selected_names)}")
            
            # Get input
            try:
                import sys, tty, termios
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                tty.setraw(sys.stdin.fileno())
                ch = sys.stdin.read(1)
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                
                if ch == '\r' or ch == '\n':  # Enter
                    break
                elif ch == ' ':  # Space - toggle selection
                    key = options[current_index][0]
                    if key in self.selected_databases:
                        self.selected_databases.remove(key)
                    else:
                        self.selected_databases.add(key)
                elif ch == '\x1b':  # Arrow keys
                    ch = sys.stdin.read(2)
                    if ch == '[A':  # Up arrow
                        current_index = (current_index - 1) % len(options)
                    elif ch == '[B':  # Down arrow
                        current_index = (current_index + 1) % len(options)
                elif ch == '\x03':  # Ctrl+C
                    print("\nInstallation cancelled.")
                    sys.exit(0)
                    
            except (ImportError, termios.error):
                # Fallback for systems without termios (like Windows)
                print(f"\nCurrent selection (enter number to toggle, 0 to continue):")
                for i, (key, info) in enumerate(options, 1):
                    selected = "✓" if key in self.selected_databases else " "
                    print(f"  {i}. [{selected}] {info['display_name']}")
                
                try:
                    choice = input("\nEnter choice: ").strip()
                    if choice == "0" or choice == "":
                        break
                    elif choice.isdigit():
                        idx = int(choice) - 1
                        if 0 <= idx < len(options):
                            key = options[idx][0]
                            if key in self.selected_databases:
                                self.selected_databases.remove(key)
                            else:
                                self.selected_databases.add(key)
                except (ValueError, KeyboardInterrupt):
                    break
        
        # Clear screen
        print("\033[2J\033[H", end="")
        print("🚀 Thoth Unified Installation Tool")
        print("=" * 50)
        print()
        
        if self.selected_databases:
            selected_names = [db_managers[db]["display_name"] for db in self.selected_databases]
            print(f"✅ Selected databases: {', '.join(selected_names)}")
        else:
            print("ℹ️  No databases selected")
        
    
    def interactive_vectordb_selection(self):
        """Interactive vector database selection with spacebar toggle"""
        print("\n🔍 Select Vector Databases:")
        print("-" * 30)
        print("Use SPACE to select/deselect, ↑↓ to navigate, B to go back, ENTER to continue")
        print()
        print("─" * 74)
        print("  ⚠️  WARNING: Milvus and Weaviate cannot be installed together!")
        print("      This is due to conflicting library dependencies.")
        print("      You can install only one of them, optionally with others.")
        print("─" * 74)
        print()
        
        vdb_managers = self.vdb_plugins["vector_databases"]
        
        # Check for conflicts (e.g., pgvector requires postgresql)
        available_vdbs = {}
        for key, info in vdb_managers.items():
            if "requires" in info:
                if not any(req in self.selected_databases for req in info["requires"]):
                    continue  # Skip if requirements not met
            available_vdbs[key] = info
        
        if not available_vdbs:
            print("⚠️  No vector databases available. Please select database managers first.")
            return
        
        # Load previous selection as current selection
        if self.user_prefs.get("selected_vectordbs"):
            # Only keep previous selections that are still available
            self.selected_vectordbs = set(self.user_prefs["selected_vectordbs"]).intersection(set(available_vdbs.keys()))
        else:
            # Use defaults if no previous selection
            self.selected_vectordbs = {key for key, info in available_vdbs.items() if info.get("default", False)}
        
        options = list(available_vdbs.items())
        current_index = 0
        
        while True:
            # Clear screen
            print("\033[2J\033[H", end="")
            print("🚀 Thoth Unified Installation Tool")
            print("=" * 50)
            print()
            print("🔍 Select Vector Databases:")
            print("-" * 30)
            print("Use SPACE to select/deselect, ↑↓ to navigate, B to go back, ENTER to continue")
            print()
            print("─" * 74)
            print("  ⚠️  WARNING: Milvus and Weaviate cannot be installed together!")
            print("      This is due to conflicting library dependencies.")
            print("      You can install only one of them, optionally with others.")
            print("─" * 74)
            print()
            
            for i, (key, info) in enumerate(options):
                prefix = ">" if i == current_index else " "
                selected = "✓" if key in self.selected_vectordbs else " "
                requires_text = f" (requires {', '.join(info['requires'])})" if info.get('requires') else ""
                print(f"{prefix} [{selected}] {info['display_name']}{requires_text}")
                if i == current_index:
                    print(f"     {info['description']}")
            
            print(f"\nSelected: {len(self.selected_vectordbs)} vector database(s)")
            if self.selected_vectordbs:
                selected_names = [vdb_managers[vdb]["display_name"] for vdb in self.selected_vectordbs]
                print(f"Current: {', '.join(selected_names)}")
            
            # Get input
            try:
                import sys, tty, termios
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                tty.setraw(sys.stdin.fileno())
                ch = sys.stdin.read(1)
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                
                if ch == '\r' or ch == '\n':  # Enter
                    break
                elif ch == ' ':  # Space - toggle selection
                    key = options[current_index][0]
                    if key in self.selected_vectordbs:
                        self.selected_vectordbs.remove(key)
                    else:
                        # Check for Milvus/Weaviate conflict
                        if key in ['milvus', 'weaviate']:
                            conflicting = 'weaviate' if key == 'milvus' else 'milvus'
                            if conflicting in self.selected_vectordbs:
                                # Remove conflicting selection
                                self.selected_vectordbs.remove(conflicting)
                        self.selected_vectordbs.add(key)
                elif ch == '\x1b':  # Arrow keys
                    ch = sys.stdin.read(2)
                    if ch == '[A':  # Up arrow
                        current_index = (current_index - 1) % len(options)
                    elif ch == '[B':  # Down arrow
                        current_index = (current_index + 1) % len(options)
                elif ch.lower() == 'b':  # Back to database selection
                    return "back"
                elif ch == '\x03':  # Ctrl+C
                    print("\nInstallation cancelled.")
                    sys.exit(0)
                    
            except (ImportError, termios.error):
                # Fallback for systems without termios (like Windows)
                print(f"\nCurrent selection (enter number to toggle, 0 to continue, 'b' to go back):")
                for i, (key, info) in enumerate(options, 1):
                    selected = "✓" if key in self.selected_vectordbs else " "
                    requires_text = f" (requires {', '.join(info['requires'])})" if info.get('requires') else ""
                    print(f"  {i}. [{selected}] {info['display_name']}{requires_text}")
                
                try:
                    choice = input("\nEnter choice: ").strip()
                    if choice == "0" or choice == "":
                        break
                    elif choice.lower() == 'b':
                        return "back"
                    elif choice.isdigit():
                        idx = int(choice) - 1
                        if 0 <= idx < len(options):
                            key = options[idx][0]
                            if key in self.selected_vectordbs:
                                self.selected_vectordbs.remove(key)
                            else:
                                # Check for Milvus/Weaviate conflict
                                if key in ['milvus', 'weaviate']:
                                    conflicting = 'weaviate' if key == 'milvus' else 'milvus'
                                    if conflicting in self.selected_vectordbs:
                                        # Remove conflicting selection
                                        self.selected_vectordbs.remove(conflicting)
                                self.selected_vectordbs.add(key)
                except (ValueError, KeyboardInterrupt):
                    break
        
        # Clear screen
        print("\033[2J\033[H", end="")
        print("🚀 Thoth Unified Installation Tool")
        print("=" * 50)
        print()
        
        if self.selected_vectordbs:
            selected_names = [vdb_managers[vdb]["display_name"] for vdb in self.selected_vectordbs]
            print(f"✅ Selected vector databases: {', '.join(selected_names)}")
        else:
            print("ℹ️  No vector databases selected")
    
    def generate_requirements(self, component: str = "both") -> Tuple[List[str], List[str]]:
        """Generate requirements lists for backend and frontend based on selections"""
        backend_requirements = []
        frontend_requirements = []
        
        # Thoth manager libraries with profiles
        db_profiles = []
        vdb_profiles = []
        
        # Collect database manager profiles
        for db in self.selected_databases:
            db_info = self.db_plugins["database_managers"][db]
            if "manager_profile" in db_info:
                db_profiles.append(db_info["manager_profile"])
        
        # Collect vector database manager profiles  
        for vdb in self.selected_vectordbs:
            vdb_info = self.vdb_plugins["vector_databases"][vdb]
            if "manager_profile" in vdb_info:
                vdb_profiles.append(vdb_info["manager_profile"])
        
        # Generate backend requirements
        if component in ["both", "backend"] and self.install_backend:
            # Core backend dependencies
            backend_requirements.extend(self.dependency_map["core_thoth"])
            
            # Add thoth-dbmanager with profiles
            if db_profiles:
                db_requirement = f"thoth-dbmanager[{','.join(db_profiles)}]>=0.4.2"
                backend_requirements.append(db_requirement)
                # Add core database dependencies
                backend_requirements.extend(self.db_plugins["core_database_dependencies"])
            
            # Add thoth-vdbmanager with profiles
            if vdb_profiles:
                vdb_requirement = f"thoth-vdbmanager[{','.join(vdb_profiles)}]>=0.2.16"
                backend_requirements.append(vdb_requirement)
                # Add core vector dependencies
                backend_requirements.extend(self.vdb_plugins["core_vector_dependencies"])
            
            # Add individual plugin dependencies (if any remain)
            for db in self.selected_databases:
                db_info = self.db_plugins["database_managers"][db]
                backend_requirements.extend(db_info.get("dependencies", []))
            
            for vdb in self.selected_vectordbs:
                vdb_info = self.vdb_plugins["vector_databases"][vdb]
                backend_requirements.extend(vdb_info.get("dependencies", []))
            
            # Haystack integration
            if self.selected_vectordbs:
                backend_requirements.extend(self.dependency_map["haystack_integration"])
            
            # Security and monitoring (always included)
            backend_requirements.extend(self.dependency_map["security"])
            backend_requirements.extend(self.dependency_map["monitoring"])
        
        # Generate frontend requirements
        if component in ["both", "frontend"] and self.install_frontend:
            # Core frontend dependencies
            frontend_requirements.extend(self.dependency_map["core_thothsl"])
            
            # Add same thoth-dbmanager and thoth-vdbmanager with profiles for frontend
            if db_profiles:
                db_requirement = f"thoth-dbmanager[{','.join(db_profiles)}]>=0.4.5"
                frontend_requirements.append(db_requirement)
            
            if vdb_profiles:
                vdb_requirement = f"thoth-vdbmanager[{','.join(vdb_profiles)}]>=0.2.16"
                frontend_requirements.append(vdb_requirement)
            
            # AI providers - include popular ones by default
            frontend_requirements.extend(self.dependency_map["ai_providers"]["openai"])
            frontend_requirements.extend(self.dependency_map["ai_providers"]["anthropic"])
            frontend_requirements.extend(self.dependency_map["ai_providers"]["ollama"])
            
            # Django API integration (for ThothSL to communicate with backend)
            frontend_requirements.extend(self.dependency_map["django_api_integration"])
            
            # Monitoring
            frontend_requirements.extend(self.dependency_map["monitoring"])
        
        return backend_requirements, frontend_requirements
    
    def show_installation_summary(self, backend_requirements: List[str], frontend_requirements: List[str]):
        """Show what will be installed"""
        print("\n📦 Installation Summary:")
        print("=" * 50)
        
        # Component status
        components = []
        if self.install_backend:
            components.append("Backend (Django)")
        if self.install_frontend:
            components.append("Frontend (Streamlit)")
        print(f"Components: {', '.join(components)}")
        
        if self.selected_databases:
            db_names = [self.db_plugins["database_managers"][db]["display_name"] for db in self.selected_databases]
            print(f"Database Managers: {', '.join(db_names)}")
        
        if self.selected_vectordbs:
            vdb_names = [self.vdb_plugins["vector_databases"][vdb]["display_name"] for vdb in self.selected_vectordbs]
            print(f"Vector Databases: {', '.join(vdb_names)}")
        
        if self.install_backend:
            print(f"\nBackend packages: {len(backend_requirements)}")
        if self.install_frontend:
            print(f"Frontend packages: {len(frontend_requirements)}")
        
        # Environment check
        venv_status = "✅ Active" if os.environ.get('VIRTUAL_ENV') else "❌ None"
        print(f"Virtual Environment: {venv_status}")
        
        print(f"Python Version: {self.user_prefs['environment']['python_version']}")
        print(f"Platform: {self.user_prefs['environment']['platform']}")
    
    def install_packages(self, backend_requirements: List[str], frontend_requirements: List[str]) -> bool:
        """Install packages using pip"""
        try:
            all_requirements = []
            
            if self.install_backend and backend_requirements:
                print("\n🔧 Installing backend dependencies...")
                all_requirements.extend(backend_requirements)
            
            if self.install_frontend and frontend_requirements:
                print("\n🔧 Installing frontend dependencies...")
                all_requirements.extend(frontend_requirements)
            
            if not all_requirements:
                print("ℹ️  No packages to install")
                return True
            
            # Remove duplicates while preserving order
            unique_requirements = list(dict.fromkeys(all_requirements))
            
            print(f"Installing {len(unique_requirements)} packages...")
            
            # Install packages
            result = subprocess.run([
                sys.executable, "-m", "pip", "install"
            ] + unique_requirements, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Package installation successful!")
                return True
            else:
                print(f"❌ Package installation failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Installation error: {e}")
            return False
    
    def finalize_installation(self, docker_mode="auto", verbose=False):
        """Finalize installation with Docker integration for both components"""
        print(f"\n🐳 Docker Integration ({docker_mode} mode)")
        print("-" * 50)
        
        if docker_mode == "auto":
            try:
                # Check if docker and docker compose are available
                subprocess.run(["docker", "--version"], capture_output=True, check=True)
                subprocess.run(["docker", "compose", "--version"], capture_output=True, check=True)
                
                success_count = 0
                
                # Handle backend
                if self.install_backend and self.backend_dir.exists():
                    print("\n🔄 Building and starting backend (Django)...")
                    if self._setup_docker_component("backend", self.backend_dir, verbose):
                        success_count += 1
                        print("✅ Backend started successfully!")
                        print("🌐 Backend: http://localhost:8040")
                        print("📊 Admin: http://localhost:8040/admin")
                    else:
                        print("❌ Backend Docker setup failed")
                
                # Handle frontend
                if self.install_frontend and self.frontend_dir.exists():
                    print("\n🔄 Building and starting frontend (Streamlit)...")
                    if self._setup_docker_component("frontend", self.frontend_dir, verbose):
                        success_count += 2
                        print("✅ Frontend started successfully!")
                        print("🎯 Frontend: http://localhost:8501")
                    else:
                        print("❌ Frontend Docker setup failed")
                
                # Final status
                expected_components = int(self.install_backend) + int(self.install_frontend)
                if success_count == expected_components:
                    print("\n🎉 All components running successfully!")
                    if self.install_backend and self.install_frontend:
                        print("🔍 Qdrant Dashboard: http://localhost:6333/dashboard")
                    return True
                else:
                    print(f"\n⚠️  {success_count}/{expected_components} components started successfully")
                    return False
                
            except subprocess.CalledProcessError:
                print("❌ Docker or Docker Compose not found!")
                print("💡 Install Docker and try again, or use --manual mode")
                return False
            except Exception as e:
                print(f"❌ Docker integration error: {e}")
                print("💡 Try manual startup or check Docker installation")
                return False
        
        else:  # manual mode
            print("✅ Installation complete!")
            print("🐳 To start Thoth manually:")
            if self.install_backend:
                print("   Backend:  cd thoth_be && docker compose up --build")
            if self.install_frontend:
                print("   Frontend: cd thoth_sl && docker compose up --build")
            print()
            print("🌐 Access points after manual startup:")
            if self.install_backend:
                print("   Backend: http://localhost:8040")
            if self.install_frontend:
                print("   Frontend: http://localhost:8501")
            return True
    
    def _setup_docker_component(self, component_name: str, component_dir: Path, verbose: bool) -> bool:
        """Setup Docker for a specific component"""
        try:
            # Build the component image with animated spinner
            print(f"Building {component_name} image...")
            
            # Start build process
            build_process = subprocess.Popen(
                ["docker", "compose", "build"], 
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, 
                cwd=component_dir
            )
            
            # Animated spinner
            spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
            spinner_running = True
            
            def spinner():
                i = 0
                while spinner_running:
                    print(f"\r🐳 Building {component_name} image... {spinner_chars[i % len(spinner_chars)]}", end="", flush=True)
                    time.sleep(0.1)
                    i += 1
            
            # Start spinner in background
            spinner_thread = threading.Thread(target=spinner)
            spinner_thread.daemon = True
            spinner_thread.start()
            
            # Wait for build to complete
            stdout, _ = build_process.communicate()
            spinner_running = False
            spinner_thread.join(timeout=0.2)
            
            # Clear spinner line
            print("\r" + " " * 60 + "\r", end="")
            
            if build_process.returncode != 0:
                print(f"❌ {component_name} build failed")
                if verbose:
                    print(stdout)
                return False
            
            # Start containers
            print(f"🚀 Starting {component_name} containers...")
            
            if not verbose:
                # Simple spinner for startup
                start_process = subprocess.Popen(
                    ["docker", "compose", "up", "-d"], 
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                    cwd=component_dir
                )
                
                spinner_running = True
                spinner_thread = threading.Thread(target=lambda: self._simple_spinner(f"{component_name} containers starting"))
                spinner_thread.daemon = True
                spinner_thread.start()
                
                start_process.wait()
                spinner_running = False
                spinner_thread.join(timeout=0.2)
                
                # Clear spinner line
                print("\r" + " " * 60 + "\r", end="")
                
                return start_process.returncode == 0
            else:
                # Verbose mode with output
                result = subprocess.run(
                    ["docker", "compose", "up", "-d"], 
                    capture_output=True, text=True, cwd=component_dir
                )
                if result.returncode != 0:
                    print(f"❌ {component_name} start failed: {result.stderr}")
                    return False
                print(result.stdout)
                return True
                
        except Exception as e:
            print(f"❌ {component_name} Docker setup error: {e}")
            return False
    
    def _simple_spinner(self, message: str):
        """Simple spinner for Docker operations"""
        spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        i = 0
        while hasattr(self, '_spinner_running') and self._spinner_running:
            print(f"\r🐳 {message}... {spinner_chars[i % len(spinner_chars)]}", end="", flush=True)
            time.sleep(0.1)
            i += 1
    
    def run_interactive(self, docker_mode="auto", verbose=False):
        """Run interactive installation"""
        self.show_welcome()
        
        # Check for immediate ENTER (use defaults)
        print("📊 Default Configuration: PostgreSQL + SQLite + Qdrant")
        print("Press ENTER to use defaults or any key + ENTER to customize...")
        
        try:
            import select
            import sys
            import tty
            import termios
            
            # Check if Enter was pressed immediately
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            
            # Wait briefly for input
            ready, _, _ = select.select([sys.stdin], [], [], 0.1)
            if ready:
                # Input available, read it
                tty.setraw(sys.stdin.fileno())
                ch = sys.stdin.read(1)
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                
                if ch == '\r' or ch == '\n':  # Enter pressed
                    print("✅ Using default configuration...")
                    # Set defaults: PostgreSQL + SQLite + Qdrant
                    self.selected_databases = {"postgresql", "sqlite"}
                    self.selected_vectordbs = {"qdrant"}
                else:
                    # Custom selection
                    print("🎛️  Custom configuration selected...")
                    while True:
                        self.interactive_database_selection()
                        result = self.interactive_vectordb_selection()
                        if result != "back":
                            break
            else:
                # No immediate input, proceed with custom selection
                print("🎛️  Custom configuration mode...")
                while True:
                    self.interactive_database_selection()
                    result = self.interactive_vectordb_selection()
                    if result != "back":
                        break
                
        except (ImportError, OSError):
            # Fallback for systems without termios/select
            user_input = input().strip()
            if user_input == "":
                print("✅ Using default configuration...")
                self.selected_databases = {"postgresql", "sqlite"}
                self.selected_vectordbs = {"qdrant"}
            else:
                print("🎛️  Custom configuration mode...")
                while True:
                    self.interactive_database_selection()
                    result = self.interactive_vectordb_selection()
                    if result != "back":
                        break
        
        # Generate requirements
        backend_requirements, frontend_requirements = self.generate_requirements()
        self.show_installation_summary(backend_requirements, frontend_requirements)
        
        # Final confirmation loop
        while True:
            print("\n🚀 Final Confirmation:")
            print("Ready to install Thoth with the following configuration:")
            print("  [E]xecute - Proceed with installation (default)")
            print("  [B]ack - Return to configuration")
            print("  [Q]uit - Cancel installation")
            confirm = input("\nEnter your choice (E/B/Q) [E]: ").lower().strip()
            
            # Default to 'execute' if Enter is pressed
            if confirm == "":
                confirm = "e"
            
            if confirm in ['e', 'execute']:
                if self.install_packages(backend_requirements, frontend_requirements):
                    self.save_user_preferences()
                    # Finalize with Docker integration
                    if self.finalize_installation(docker_mode, verbose):
                        print("\n🎉 Thoth installation and setup completed successfully!")
                        print("\033[0m", end="")  # Reset any terminal colors
                    else:
                        print("\n⚠️  Installation completed but Docker setup failed.")
                        print("   You can start Thoth manually with Docker commands.")
                else:
                    print("\n❌ Installation failed. Please check the errors above.")
                break
            elif confirm in ['b', 'back']:
                print("🔄 Returning to configuration...")
                # Return to configuration loop
                while True:
                    self.interactive_database_selection()
                    result = self.interactive_vectordb_selection()
                    if result != "back":
                        break
                # Regenerate requirements and show summary again
                backend_requirements, frontend_requirements = self.generate_requirements()
                self.show_installation_summary(backend_requirements, frontend_requirements)
            elif confirm in ['q', 'quit']:
                print("❌ Installation cancelled by user.")
                sys.exit(0)
            else:
                print("❌ Invalid choice. Please enter E, B, or Q.")
    
    def show_config(self):
        """Show current configuration"""
        print("📋 Current Thoth Configuration:")
        print("=" * 40)
        
        # Component status
        components = []
        config = self.user_prefs.get("unified_config", {})
        if config.get("backend_enabled", True):
            components.append("Backend (Django)")
        if config.get("frontend_enabled", True):
            components.append("Frontend (Streamlit)")
        print(f"Components: {', '.join(components) if components else 'Both (default)'}")
        
        if self.user_prefs.get("selected_databases"):
            db_names = [self.db_plugins["database_managers"][db]["display_name"] 
                       for db in self.user_prefs["selected_databases"] 
                       if db in self.db_plugins["database_managers"]]
            print(f"Databases: {', '.join(db_names)}")
        else:
            print("Databases: None selected")
        
        if self.user_prefs.get("selected_vectordbs"):
            vdb_names = [self.vdb_plugins["vector_databases"][vdb]["display_name"] 
                        for vdb in self.user_prefs["selected_vectordbs"] 
                        if vdb in self.vdb_plugins["vector_databases"]]
            print(f"Vector DBs: {', '.join(vdb_names)}")
        else:
            print("Vector DBs: None selected")
        
        print(f"\nLast updated: {self.user_prefs.get('last_updated', 'Never')}")
        print(f"Installation ID: {self.user_prefs.get('installation_id', 'Unknown')}")
        
        # Show installation history
        if self.user_prefs.get("installation_history"):
            print(f"Previous installations: {len(self.user_prefs['installation_history'])}")
        
        # Show ports
        config = self.user_prefs.get("unified_config", {})
        print(f"Backend port: {config.get('backend_port', 8040)}")
        print(f"Frontend port: {config.get('frontend_port', 8501)}")


def main():
    """Main installation function"""
    parser = argparse.ArgumentParser(description="Thoth Unified Installation Tool")
    
    # Component selection
    component_group = parser.add_mutually_exclusive_group()
    component_group.add_argument("--backend-only", action="store_true", 
                                help="Install only the backend components")
    component_group.add_argument("--frontend-only", action="store_true", 
                                help="Install only the frontend components")
    
    # Configuration options
    parser.add_argument("--db", "--databases", help="Comma-separated list of databases")
    parser.add_argument("--vdb", "--vectordbs", help="Comma-separated list of vector databases")
    parser.add_argument("--show-config", action="store_true", help="Show current configuration")
    parser.add_argument("--reset", action="store_true", help="Reset configuration to defaults")
    parser.add_argument("--verbose", action="store_true", help="Show detailed Docker build output")
    
    # Docker integration mode
    docker_group = parser.add_mutually_exclusive_group()
    docker_group.add_argument("--auto", action="store_true", default=True, 
                              help="Automatically rebuild and start Docker containers (default)")
    docker_group.add_argument("--manual", action="store_true", 
                              help="Manual mode - only generate requirements, don't start Docker")
    
    args = parser.parse_args()
    
    installer = ThothUnifiedInstaller()
    
    # Set component installation flags
    if args.backend_only:
        installer.install_backend = True
        installer.install_frontend = False
    elif args.frontend_only:
        installer.install_backend = False
        installer.install_frontend = True
    else:
        # Both by default
        installer.install_backend = True
        installer.install_frontend = True
    
    if args.show_config:
        installer.show_config()
        return
    
    if args.reset:
        prefs_path = installer.configs_dir / "user-preferences.json"
        if prefs_path.exists():
            prefs_path.unlink()
            print("✅ Configuration reset to defaults")
        else:
            print("ℹ️  No configuration found to reset")
        return
    
    # Determine Docker mode
    docker_mode = "manual" if args.manual else "auto"
    
    # Command line mode
    if args.db or args.vdb:
        if args.db:
            db_list = [db.strip() for db in args.db.split(',')]
            valid_dbs = set(installer.db_plugins["database_managers"].keys())
            installer.selected_databases = set(db for db in db_list if db in valid_dbs)
            invalid_dbs = set(db_list) - installer.selected_databases
            if invalid_dbs:
                print(f"⚠️  Invalid databases: {', '.join(invalid_dbs)}")
        
        if args.vdb:
            vdb_list = [vdb.strip() for vdb in args.vdb.split(',')]
            valid_vdbs = set(installer.vdb_plugins["vector_databases"].keys())
            installer.selected_vectordbs = set(vdb for vdb in vdb_list if vdb in valid_vdbs)
            invalid_vdbs = set(vdb_list) - installer.selected_vectordbs
            if invalid_vdbs:
                print(f"⚠️  Invalid vector databases: {', '.join(invalid_vdbs)}")
        
        backend_requirements, frontend_requirements = installer.generate_requirements()
        installer.show_installation_summary(backend_requirements, frontend_requirements)
        
        if installer.install_packages(backend_requirements, frontend_requirements):
            installer.save_user_preferences()
            # Finalize with Docker integration
            if installer.finalize_installation(docker_mode, args.verbose):
                print("🎉 Installation and setup completed successfully!")
                print("\033[0m", end="")  # Reset any terminal colors
            else:
                print("⚠️  Installation completed but Docker setup failed.")
        else:
            print("❌ Installation failed!")
    else:
        # Interactive mode
        installer.run_interactive(docker_mode, args.verbose)


if __name__ == "__main__":
    main()