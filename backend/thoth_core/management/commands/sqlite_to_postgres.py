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

import os
import subprocess
import sqlite3
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import connection


class Command(BaseCommand):
    help = 'Convert SQLite database to PostgreSQL using pgloader'

    def add_arguments(self, parser):
        parser.add_argument(
            'sqlite_path',
            type=str,
            help='Percorso del file SQLite relativo alla directory data/ (es: file.sqlite o subdir/file.sqlite)'
        )
        parser.add_argument(
            '--target-db',
            type=str,
            help='Nome del database PostgreSQL di destinazione (default: nome del file SQLite senza estensione)'
        )
        parser.add_argument(
            '--create-db',
            action='store_true',
            help='Create the destination database if it does not exist'
        )
        parser.add_argument(
            '--drop-tables',
            action='store_true',
            help='Drop existing tables before import (requires --create-db)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra il comando pgloader che verrebbe eseguito senza eseguirlo'
        )

    def handle(self, *args, **options):
        sqlite_path_input = options['sqlite_path']
        target_db = options.get('target_db')
        create_db = options.get('create_db', False)
        drop_tables = options.get('drop_tables', False)
        dry_run = options.get('dry_run', False)

        # Determina il nome del database di destinazione
        if not target_db:
            # Usa solo il nome del file (senza directory e senza estensione)
            filename = os.path.basename(sqlite_path_input)
            target_db = os.path.splitext(filename)[0]

        self.stdout.write(f"Conversione SQLite -> PostgreSQL")
        self.stdout.write(f"File SQLite: {sqlite_path_input}")
        self.stdout.write(f"Database PostgreSQL di destinazione: {target_db}")

        try:
            # Step 1: Valida il file SQLite
            sqlite_full_path = self._validate_sqlite_file(sqlite_path_input)
            
            # Step 2: Ottieni le credenziali PostgreSQL
            pg_config = self._get_postgres_config()
            
            # Step 3: Create the database if requested
            if create_db:
                self._create_postgres_database(target_db, pg_config, drop_tables)
            
            # Step 4: Esegui pgloader
            self._run_pgloader(sqlite_full_path, target_db, pg_config, dry_run)
            
            if not dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Conversione completata con successo! "
                        f"Database '{target_db}' è ora disponibile in PostgreSQL."
                    )
                )
            
        except CommandError:
            raise
        except Exception as e:
            raise CommandError(f"Errore durante la conversione: {str(e)}")

    def _validate_sqlite_file(self, sqlite_filename):
        """Valida l'esistenza e la validità del file SQLite"""
        # Percorso nel container dell'app
        data_dir = '/app/data'
        sqlite_path = os.path.join(data_dir, sqlite_filename)
        
        # Check if the file exists
        if not os.path.exists(sqlite_path):
            raise CommandError(
                f"File SQLite non trovato: {sqlite_path}\n"
                f"Assicurati che il file sia presente nella directory data/"
            )
        
        # Verifica che sia un file SQLite valido
        try:
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            conn.close()
            
            if not tables:
                self.stdout.write(
                    self.style.WARNING(
                        f"Il file SQLite '{sqlite_filename}' non contiene tabelle."
                    )
                )
            else:
                self.stdout.write(f"File SQLite valido con {len(tables)} tabelle trovate.")
                
        except sqlite3.Error as e:
            raise CommandError(f"File SQLite non valido: {str(e)}")
        
        return sqlite_path

    def _get_postgres_config(self):
        """Get PostgreSQL configuration from Django settings"""
        db_config = settings.DATABASES.get('default', {})
        
        return {
            'host': db_config.get('HOST', 'localhost'),
            'port': db_config.get('PORT', '5432'),
            'user': db_config.get('USER', 'thoth_user'),
            'password': db_config.get('PASSWORD', 'thoth_password'),
        }

    def _create_postgres_database(self, target_db, pg_config, drop_tables):
        """Create the PostgreSQL database if it does not exist"""
        self.stdout.write(f"Verificando/creando database '{target_db}'...")
        
        # Comando per creare il database
        create_db_cmd = [
            'docker', 'exec', 'thoth-db', 'psql',
            '-h', 'localhost',
            '-U', pg_config['user'],
            '-d', 'postgres',
            '-c', f"SELECT 1 FROM pg_database WHERE datname = '{target_db}';"
        ]
        
        try:
            # Check if the database exists
            result = subprocess.run(
                create_db_cmd,
                capture_output=True,
                text=True,
                env={**os.environ, 'PGPASSWORD': pg_config['password']}
            )
            
            if result.returncode == 0 and '1' in result.stdout:
                self.stdout.write(f"Database '{target_db}' già esistente.")
                
                if drop_tables:
                    self.stdout.write("Eliminando tabelle esistenti...")
                    drop_cmd = [
                        'docker', 'exec', 'thoth-db', 'psql',
                        '-h', 'localhost',
                        '-U', pg_config['user'],
                        '-d', target_db,
                        '-c', "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
                    ]
                    
                    drop_result = subprocess.run(
                        drop_cmd,
                        capture_output=True,
                        text=True,
                        env={**os.environ, 'PGPASSWORD': pg_config['password']}
                    )
                    
                    if drop_result.returncode != 0:
                        raise CommandError(f"Errore nell'eliminazione delle tabelle: {drop_result.stderr}")
                    
                    self.stdout.write("Tabelle eliminate con successo.")
            else:
                # Crea il database
                self.stdout.write(f"Creando database '{target_db}'...")
                create_cmd = [
                    'docker', 'exec', 'thoth-db', 'psql',
                    '-h', 'localhost',
                    '-U', pg_config['user'],
                    '-d', 'postgres',
                    '-c', f"CREATE DATABASE \"{target_db}\";"
                ]
                
                create_result = subprocess.run(
                    create_cmd,
                    capture_output=True,
                    text=True,
                    env={**os.environ, 'PGPASSWORD': pg_config['password']}
                )
                
                if create_result.returncode != 0:
                    if 'already exists' in create_result.stderr:
                        self.stdout.write(f"Database '{target_db}' già esistente.")
                    else:
                        raise CommandError(f"Errore nella creazione del database: {create_result.stderr}")
                else:
                    self.stdout.write(f"Database '{target_db}' creato con successo.")
                    
        except subprocess.SubprocessError as e:
            raise CommandError(f"Errore nell'esecuzione del comando PostgreSQL: {str(e)}")

    def _run_pgloader(self, sqlite_path, target_db, pg_config, dry_run):
        """Esegui pgloader per convertire da SQLite a PostgreSQL"""
        # Costruisci l'URL di connessione PostgreSQL
        postgres_url = (
            f"postgresql://{pg_config['user']}:{pg_config['password']}"
            f"@{pg_config['host']}:{pg_config['port']}/{target_db}"
        )
        
        # Costruisci l'URL SQLite (percorso nel container PostgreSQL)
        sqlite_url = f"sqlite://{sqlite_path}"
        
        # Comando pgloader
        pgloader_cmd = [
            'docker', 'exec', 'thoth-db', 'pgloader',
            sqlite_url,
            postgres_url
        ]
        
        self.stdout.write("Comando pgloader:")
        self.stdout.write(" ".join(pgloader_cmd))
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: Il comando non è stato eseguito."))
            return
        
        self.stdout.write("Eseguendo pgloader...")
        
        try:
            # Esegui pgloader
            result = subprocess.run(
                pgloader_cmd,
                capture_output=True,
                text=True,
                timeout=300  # Timeout di 5 minuti
            )
            
            # Mostra l'output di pgloader
            if result.stdout:
                self.stdout.write("Output pgloader:")
                self.stdout.write(result.stdout)
            
            if result.stderr:
                self.stdout.write("Errori/Warning pgloader:")
                self.stdout.write(result.stderr)
            
            if result.returncode != 0:
                raise CommandError(
                    f"pgloader ha terminato con errore (codice {result.returncode}). "
                    f"Controlla l'output sopra per i dettagli."
                )
                
        except subprocess.TimeoutExpired:
            raise CommandError(
                "pgloader ha superato il timeout di 5 minuti. "
                "Il database potrebbe essere troppo grande o ci potrebbero essere problemi di connessione."
            )
        except subprocess.SubprocessError as e:
            raise CommandError(f"Errore nell'esecuzione di pgloader: {str(e)}")
