import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.core import QgsMessageLog, Qgis
import tempfile
import os
import zipfile
import re
import shutil
from datetime import datetime
from .compat import MessageCritical, MessageInfo, MessageWarning


class DatabaseManager(QObject):
    """Handles all database operations using psycopg2."""
    
    # Signals
    operation_finished = pyqtSignal(bool, str)  # success, message
    progress_updated = pyqtSignal(str)  # progress message
    
    def __init__(self):
        super().__init__()
        self.connection_params = {}
        self.connection = None
    
    def log_message(self, message, level=MessageInfo):
        """Log message to QGIS message log."""
        QgsMessageLog.logMessage(message, 'KGR Toolbox', level)
    
    def set_connection_params(self, host, port, database, username, password):
        """Set connection parameters."""
        self.connection_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': username,
            'password': password
        }
    
    def test_connection(self):
        """Test database connection."""
        try:
            self.progress_updated.emit("Testing connection...")
            
            conn = psycopg2.connect(**self.connection_params)
            conn.close()
            
            self.progress_updated.emit("Connection successful!")
            self.operation_finished.emit(True, "Connection successful!")
            return True
            
        except psycopg2.Error as e:
            error_msg = f"Connection failed: {str(e)}"
            self.log_message(error_msg, MessageCritical)
            self.operation_finished.emit(False, error_msg)
            return False
    
    def get_databases(self):
        """Get list of non-template databases."""
        try:
            conn_params = self.connection_params.copy()
            conn_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            try:
                query = """
                    SELECT datname FROM pg_database 
                    WHERE datistemplate = false 
                    AND datname NOT IN ('postgres', 'template0', 'template1')
                    ORDER BY datname;
                """
                
                cursor.execute(query)
                results = cursor.fetchall()
                
                databases = []
                for row in results:
                    if row and len(row) > 0 and row[0] is not None:
                        databases.append(str(row[0]))
                
                return databases
                
            except psycopg2.Error as db_error:
                self.log_message(f"Database error getting databases: {str(db_error)}", MessageCritical)
                return []
            finally:
                cursor.close()
                conn.close()
            
        except psycopg2.Error as e:
            self.log_message(f"Error getting databases: {str(e)}", MessageCritical)
            return []
    
    def get_templates(self):
        """Get list of template databases."""
        try:
            conn_params = self.connection_params.copy()
            conn_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            try:
                query = """
                    SELECT datname FROM pg_database 
                    WHERE datistemplate = true 
                    AND datname NOT IN ('template0', 'template1')
                    ORDER BY datname;
                """
                
                cursor.execute(query)
                results = cursor.fetchall()
                
                templates = []
                for row in results:
                    if row and len(row) > 0 and row[0] is not None:
                        templates.append(str(row[0]))
                
                return templates
                
            except psycopg2.Error as db_error:
                self.log_message(f"Database error getting templates: {str(db_error)}", MessageCritical)
                return []
            finally:
                cursor.close()
                conn.close()
            
        except psycopg2.Error as e:
            self.log_message(f"Error getting templates: {str(e)}", MessageCritical)
            return []
    
    def check_user_privileges(self):
        """Check user privileges."""
        try:
            conn_params = self.connection_params.copy()
            conn_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            try:
                # Check if user is superuser
                cursor.execute("SELECT usesuper FROM pg_user WHERE usename = %s;", (self.connection_params['user'],))
                result = cursor.fetchone()
                is_superuser = result[0] if result and len(result) > 0 else False
                
                # Check CREATEDB privilege
                cursor.execute("SELECT usecreatedb FROM pg_user WHERE usename = %s;", (self.connection_params['user'],))
                result = cursor.fetchone()
                can_create_db = result[0] if result and len(result) > 0 else False
                
                return {
                    'is_superuser': is_superuser,
                    'can_create_db': can_create_db
                }
                
            except psycopg2.Error as db_error:
                self.log_message(f"Database error checking privileges: {str(db_error)}", MessageCritical)
                return {'is_superuser': False, 'can_create_db': False}
            finally:
                cursor.close()
                conn.close()
            
        except psycopg2.Error as e:
            self.log_message(f"Error checking privileges: {str(e)}", MessageCritical)
            return {'is_superuser': False, 'can_create_db': False}
    
    def database_exists(self, db_name):
        """Check if database exists."""
        try:
            conn_params = self.connection_params.copy()
            conn_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            try:
                cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (db_name,))
                result = cursor.fetchone()
                exists = result is not None
                
                return exists
                
            except psycopg2.Error as db_error:
                self.log_message(f"Database error checking database existence: {str(db_error)}", MessageCritical)
                return False
            finally:
                cursor.close()
                conn.close()
            
        except psycopg2.Error as e:
            self.log_message(f"Error checking database existence: {str(e)}", MessageCritical)
            return False
    
    def is_system_database(self, db_name):
        """Check if database is a system database that should not be deleted."""
        system_databases = ['postgres', 'template0', 'template1']
        return db_name.lower() in system_databases
    
    def get_database_info(self, db_name):
        """Get detailed information about a database."""
        try:
            conn_params = self.connection_params.copy()
            conn_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            try:
                query = """
                    SELECT 
                        pg_database.datname,
                        pg_database.datistemplate,
                        pg_database.datallowconn,
                        pg_database.datconnlimit,
                        pg_database.datlastsysoid,
                        pg_database.datfrozenxid,
                        pg_database.datminmxid,
                        pg_database.dattablespace,
                        pg_database.datacl,
                        pg_size_pretty(pg_database_size(pg_database.datname)) as size,
                        pg_database_size(pg_database.datname) as size_bytes,
                        pg_user.usename as owner
                    FROM pg_database
                    JOIN pg_user ON pg_database.datdba = pg_user.usesysid
                    WHERE pg_database.datname = %s;
                """
                
                cursor.execute(query, (db_name,))
                result = cursor.fetchone()
                
                if result and len(result) >= 12:
                    db_info = {
                        'name': result[0],
                        'is_template': result[1],
                        'allow_connections': result[2],
                        'connection_limit': result[3],
                        'size_pretty': result[9],
                        'size_bytes': result[10],
                        'owner': result[11]
                    }
                else:
                    db_info = None
                
                return db_info
                
            except psycopg2.Error as db_error:
                self.log_message(f"Database error getting database info: {str(db_error)}", MessageCritical)
                return None
            finally:
                cursor.close()
                conn.close()
            
        except psycopg2.Error as e:
            self.log_message(f"Error getting database info: {str(e)}", MessageCritical)
            return None
    
    def delete_database(self, db_name, force_drop_connections=False):
        """
        Delete a database with strong safety checks and warnings.
        
        Args:
            db_name (str): Name of the database to delete
            force_drop_connections (bool): Whether to force drop active connections
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # ============ SAFETY CHECKS ============
            
            # Check if database exists
            if not self.database_exists(db_name):
                error_msg = f"Database '{db_name}' does not exist."
                self.log_message(error_msg, MessageWarning)
                self.operation_finished.emit(False, error_msg)
                return False
            
            # Prevent deletion of system databases
            if self.is_system_database(db_name):
                error_msg = f"Cannot delete system database '{db_name}'. System databases (postgres, template0, template1) cannot be deleted."
                self.log_message(error_msg, MessageCritical)
                self.operation_finished.emit(False, error_msg)
                return False
            
            # Prevent deletion of currently connected database
            if self.connection_params.get('database') == db_name:
                error_msg = f"Cannot delete database '{db_name}' because you are currently connected to it. Please connect to a different database first."
                self.log_message(error_msg, MessageCritical)
                self.operation_finished.emit(False, error_msg)
                return False
            
            # Get database information for logging
            db_info = self.get_database_info(db_name)
            if db_info:
                self.progress_updated.emit(f"Database info - Name: {db_info['name']}, Size: {db_info['size_pretty']}, Owner: {db_info['owner']}")
            
            # Check for active connections
            connection_count = self.get_connection_count(db_name)
            if connection_count > 0:
                if force_drop_connections:
                    self.progress_updated.emit(f"⚠️  WARNING: Found {connection_count} active connections to '{db_name}'. Forcing termination...")
                    
                    # Drop connections
                    if not self.drop_database_connections(db_name):
                        error_msg = f"Failed to drop active connections to database '{db_name}'. Cannot proceed with deletion."
                        self.log_message(error_msg, MessageCritical)
                        self.operation_finished.emit(False, error_msg)
                        return False
                    
                    # Wait a moment for connections to be fully dropped
                    import time
                    time.sleep(1)
                    
                    # Verify connections are dropped
                    remaining_connections = self.get_connection_count(db_name)
                    if remaining_connections > 0:
                        error_msg = f"Still {remaining_connections} active connections after termination. Cannot delete database."
                        self.log_message(error_msg, MessageCritical)
                        self.operation_finished.emit(False, error_msg)
                        return False
                else:
                    error_msg = f"Cannot delete database '{db_name}' because it has {connection_count} active connections. Use 'force_drop_connections=True' to terminate connections first."
                    self.log_message(error_msg, MessageCritical)
                    self.operation_finished.emit(False, error_msg)
                    return False
            
            # ============ DELETION PROCESS ============
            
            self.progress_updated.emit(f"🗑️  DELETING DATABASE '{db_name}' - THIS ACTION CANNOT BE UNDONE!")
            
            # Log the deletion attempt
            self.log_message(f"CRITICAL: Attempting to delete database '{db_name}' by user '{self.connection_params['user']}'", MessageCritical)
            
            conn_params = self.connection_params.copy()
            conn_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**conn_params)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Execute the deletion
            cursor.execute(f'DROP DATABASE "{db_name}";')
            
            cursor.close()
            conn.close()
            
            # Log successful deletion
            success_msg = f"✅ Database '{db_name}' has been permanently deleted!"
            self.log_message(f"SUCCESS: Database '{db_name}' deleted successfully by user '{self.connection_params['user']}'", MessageInfo)
            self.progress_updated.emit(success_msg)
            self.operation_finished.emit(True, success_msg)
            
            return True
            
        except psycopg2.Error as e:
            error_msg = f"❌ Error deleting database '{db_name}': {str(e)}"
            self.log_message(error_msg, MessageCritical)
            self.operation_finished.emit(False, error_msg)
            return False
        except Exception as e:
            error_msg = f"❌ Unexpected error deleting database '{db_name}': {str(e)}"
            self.log_message(error_msg, MessageCritical)
            self.operation_finished.emit(False, error_msg)
            return False
    
    def find_qgis_projects(self, database_name):
        """Find QGIS projects tables in all schemas of the specified database."""
        try:
            self.progress_updated.emit(f"Searching for QGIS projects in '{database_name}'...")
            
            conn_params = self.connection_params.copy()
            conn_params['database'] = database_name
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            try:
                # Find all qgis_projects tables in all schemas
                query = """
                    SELECT schemaname, tablename
                    FROM pg_tables 
                    WHERE tablename = 'qgis_projects'
                    AND schemaname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                    ORDER BY schemaname;
                """
                
                cursor.execute(query)
                tables = cursor.fetchall()
                
                projects = []
                for schema, table in tables:
                    # Get projects from this table
                    project_query = f"""
                        SELECT name, metadata 
                        FROM "{schema}"."{table}"
                        ORDER BY name;
                    """
                    
                    try:
                        cursor.execute(project_query)
                        table_projects = cursor.fetchall()
                        
                        for name, metadata in table_projects:
                            projects.append({
                                'schema': schema,
                                'table': table,
                                'name': name,
                                'metadata': metadata
                            })
                            
                    except psycopg2.Error as e:
                        self.log_message(f"Warning: Could not read projects from {schema}.{table}: {str(e)}", MessageWarning)
                
                self.progress_updated.emit(f"Found {len(projects)} QGIS projects")
                return projects
                
            except psycopg2.Error as db_error:
                self.log_message(f"Database error finding QGIS projects: {str(db_error)}", MessageCritical)
                return []
            finally:
                cursor.close()
                conn.close()
            
        except psycopg2.Error as e:
            self.log_message(f"Error finding QGIS projects: {str(e)}", MessageCritical)
            return []
    
    def fix_qgis_project_layers(self, database_name, schema, table, project_name, new_params, create_backup=True):
        """Fix QGIS project layers with new connection parameters."""
        try:
            self.progress_updated.emit(f"Starting to fix project '{project_name}'...")
            
            # Step 1: Download project content
            content = self._download_project_content(database_name, schema, table, project_name)
            if not content:
                self.operation_finished.emit(False, "Failed to download project content")
                return
            
            # Step 2: Process the QGS file (will save both files for comparison)
            fixed_content = self._process_qgs_file(content, new_params, project_name, create_backup)
            if not fixed_content:
                self.operation_finished.emit(False, "Failed to process QGS file")
                return
            
            # Step 3: DISABLED - Upload fixed content back to database
            # Commenting out the upload for debugging purposes
            # self.progress_updated.emit("SKIPPING UPLOAD - Debug mode enabled")
            self.progress_updated.emit("Both original and modified QGS files have been saved for comparison")
            
            success = self._upload_project_content(database_name, schema, table, project_name, fixed_content)
            if success:
                self.operation_finished.emit(True, f"Successfully fixed project '{project_name}'")
            else:
                self.operation_finished.emit(False, "Failed to upload fixed project content")
            
            # Instead, just report success with debug info
            # self.operation_finished.emit(True, f"Debug mode: Project '{project_name}' processed successfully. Files saved for comparison. Upload was SKIPPED.")
                
        except Exception as e:
            error_msg = f"Error fixing QGIS project: {str(e)}"
            self.log_message(error_msg, MessageCritical)
            self.operation_finished.emit(False, error_msg)
    
    def _download_project_content(self, database_name, schema, table, project_name):
        """Download project content from database."""
        try:
            self.progress_updated.emit(f"Downloading project content...")
            
            conn_params = self.connection_params.copy()
            conn_params['database'] = database_name
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            query = f'SELECT content FROM "{schema}"."{table}" WHERE name = %s;'
            cursor.execute(query, (project_name,))
            
            result = cursor.fetchone()
            if not result:
                raise Exception(f"Project '{project_name}' not found")
            
            content = result[0]
            
            # Convert memoryview to bytes if necessary
            if isinstance(content, memoryview):
                content = content.tobytes()
            elif not isinstance(content, bytes):
                # Handle other types (like buffer objects)
                content = bytes(content)
            
            cursor.close()
            conn.close()
            
            self.progress_updated.emit(f"Downloaded {len(content)} bytes of project content")
            return content
            
        except psycopg2.Error as e:
            self.log_message(f"Error downloading project content: {str(e)}", MessageCritical)
            return None
    

    def _process_qgs_file(self, content, new_params, project_name, create_backup=True):
        """Process QGS file - unzip, modify, zip, and save both versions for comparison."""
        try:
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Sanitize project name for filename (remove invalid characters)
                safe_project_name = re.sub(r'[<>:"/\\|?*]', '_', project_name)
                
                # Clean the content and preserve the prefix bytes
                clean_content, prefix_bytes = self._clean_and_preserve_zip_content(content)
                if not clean_content:
                    raise Exception("Invalid ZIP content - no ZIP magic bytes found")
                
                # Write cleaned content to temporary file
                qgz_path = os.path.join(temp_dir, f"{safe_project_name}.qgz")
                with open(qgz_path, 'wb') as f:
                    f.write(clean_content)
                
                self.progress_updated.emit("Extracting project file...")
                
                # Verify ZIP file is valid before extraction
                if not zipfile.is_zipfile(qgz_path):
                    raise Exception("Invalid ZIP file after cleaning")
                
                # Extract QGZ file
                extract_dir = os.path.join(temp_dir, "extracted")
                os.makedirs(extract_dir, exist_ok=True)
                
                with zipfile.ZipFile(qgz_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                # Find QGS and QLS file(s) (case-insensitive search for cross-platform compatibility)
                qgs_files = []
                qls_files = []
                for f in os.listdir(extract_dir):
                    if f.lower().endswith('.qgs'):
                        qgs_files.append(f)
                    if f.lower().endswith('.qls'):
                        qls_files.append(f)
                
                if not qgs_files:
                    raise Exception("No .qgs file found in project")
                
                qgs_path = os.path.join(extract_dir, qgs_files[0])
                
                # Create debug directory for saving files
                debug_locations = [
                    os.path.expanduser("~/qgis_debug_files"),
                    os.path.join(tempfile.gettempdir(), "qgis_debug_files"),
                    os.path.join(os.getcwd(), "qgis_debug_files")
                ]
                
                debug_dir = None
                for location in debug_locations:
                    try:
                        os.makedirs(location, exist_ok=True)
                        test_file = os.path.join(location, "test_write.tmp")
                        with open(test_file, 'w') as f:
                            f.write("test")
                        os.remove(test_file)
                        debug_dir = location
                        break
                    except (OSError, PermissionError):
                        continue
                
                if debug_dir:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    # Save ORIGINAL QGS file (before modifications)
                    original_qgs_path = os.path.join(debug_dir, f"{safe_project_name}_ORIGINAL_{timestamp}.qgs")
                    shutil.copy2(qgs_path, original_qgs_path)
                    self.progress_updated.emit(f"Saved ORIGINAL QGS file: {original_qgs_path}")
                    
                    # Create backup if requested (using original content for authentic backup)
                    if create_backup:
                        self._create_backup_with_content(content, safe_project_name)
                    
                    # Modify QGS file
                    self.progress_updated.emit("Modifying datasource connections...")
                    modifications_made = self._modify_qgs_datasources(qgs_path, new_params)
                    
                    if not modifications_made:
                        self.progress_updated.emit("No datasource modifications were needed")
                    
                    # Save MODIFIED QGS file (after modifications)
                    modified_qgs_path = os.path.join(debug_dir, f"{safe_project_name}_MODIFIED_{timestamp}.qgs")
                    shutil.copy2(qgs_path, modified_qgs_path)
                    self.progress_updated.emit(f"Saved MODIFIED QGS file: {modified_qgs_path}")
                    
                    # Also save QLS files if present
                    for qls_file in qls_files:
                        qls_path = os.path.join(extract_dir, qls_file)
                        qls_debug_path = os.path.join(debug_dir, f"{safe_project_name}_{qls_file}_{timestamp}.qls")
                        shutil.copy2(qls_path, qls_debug_path)
                        self.progress_updated.emit(f"Saved QLS file: {qls_debug_path}")
                    
                    # Create comparison instructions file
                    diff_instructions_path = os.path.join(debug_dir, f"DIFF_INSTRUCTIONS_{safe_project_name}_{timestamp}.txt")
                    with open(diff_instructions_path, 'w') as f:
                        f.write(f"QGS Files Comparison Instructions\n")
                        f.write(f"====================================\n\n")
                        f.write(f"Project: {project_name}\n")
                        f.write(f"Timestamp: {timestamp}\n\n")
                        f.write(f"ORIGINAL file: {original_qgs_path}\n")
                        f.write(f"MODIFIED file: {modified_qgs_path}\n\n")
                        f.write(f"To compare using diff command:\n")
                        f.write(f"diff \"{original_qgs_path}\" \"{modified_qgs_path}\"\n\n")
                        f.write(f"To compare using git diff:\n")
                        f.write(f"git diff --no-index \"{original_qgs_path}\" \"{modified_qgs_path}\"\n\n")
                        f.write(f"Connection parameters used for modification:\n")
                        for key, value in new_params.items():
                            if value.strip():
                                f.write(f"  {key}: {value}\n")
                    
                    self.progress_updated.emit(f"Created diff instructions: {diff_instructions_path}")
                else:
                    self.log_message("No writable debug directory found for saving QGS files.", MessageWarning)

                # Create new QGZ file with only the files at the archive root (including .db, .qls, etc.)
                self.progress_updated.emit("Creating updated project file...")
                new_qgz_path = os.path.join(temp_dir, f"{safe_project_name}_fixed.qgz")
                
                with zipfile.ZipFile(new_qgz_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zip_ref:
                    for file in os.listdir(extract_dir):
                        file_path = os.path.join(extract_dir, file)
                        if os.path.isfile(file_path):
                            zip_ref.write(file_path, file)  # file is the name at root

                # Read fixed content
                with open(new_qgz_path, 'rb') as f:
                    fixed_zip_content = f.read()
                
                # Verify the new ZIP is valid
                if not zipfile.is_zipfile(new_qgz_path):
                    raise Exception("Created ZIP file is invalid")
                
                # DO NOT restore prefix_bytes! QGIS expects a standard ZIP starting with PK!
                final_content = fixed_zip_content
                
                return final_content
                
        except Exception as e:
            self.log_message(f"Error processing QGS file: {str(e)}", MessageCritical)
            return None
        
    def _clean_and_preserve_zip_content(self, content):
        """Remove extra bytes before ZIP magic and return clean ZIP content + prefix bytes."""
        if not content:
            return None, None
        
        # Ensure content is bytes
        if isinstance(content, memoryview):
            content = content.tobytes()
        elif not isinstance(content, bytes):
            content = bytes(content)
        
        # ZIP files start with 'PK' (0x504B)
        zip_magic = b'PK'
        
        # Find the first occurrence of ZIP magic bytes
        zip_start = content.find(zip_magic)
        
        if zip_start == -1:
            self.log_message("No ZIP magic bytes found in content", MessageCritical)
            return None, None
        
        # Extract prefix bytes (database metadata)
        prefix_bytes = content[:zip_start] if zip_start > 0 else None
        
        if zip_start > 0:
            self.progress_updated.emit(f"Found {zip_start} database header bytes (will be preserved)")
        
        # Return clean ZIP content and prefix bytes
        return content[zip_start:], prefix_bytes
    
    def _create_backup_with_content(self, content, project_name):
        """Create local backup with raw content."""
        try:
            # Convert memoryview to bytes if necessary
            if isinstance(content, memoryview):
                content = content.tobytes()
            elif not isinstance(content, bytes):
                content = bytes(content)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            backup_locations = [
                os.path.expanduser("~/qgis_project_backups"),
                os.path.join(tempfile.gettempdir(), "qgis_project_backups"),
                os.path.join(os.getcwd(), "qgis_project_backups")
            ]
            
            backup_dir = None
            for location in backup_locations:
                try:
                    os.makedirs(location, exist_ok=True)
                    test_file = os.path.join(location, "test_write.tmp")
                    with open(test_file, 'w') as f:
                        f.write("test")
                    os.remove(test_file)
                    backup_dir = location
                    break
                except (OSError, PermissionError):
                    continue
            
            if not backup_dir:
                raise Exception("No writable backup directory found")
            
            # Save both raw and cleaned versions
            raw_backup_path = os.path.join(backup_dir, f"{project_name}_backup_raw_{timestamp}.qgz")
            clean_backup_path = os.path.join(backup_dir, f"{project_name}_backup_clean_{timestamp}.qgz")
            
            # Raw backup (original from database)
            with open(raw_backup_path, 'wb') as f:
                f.write(content)
            
            # Clean backup (ZIP-compatible)
            clean_content, _ = self._clean_and_preserve_zip_content(content)
            if clean_content:
                with open(clean_backup_path, 'wb') as f:
                    f.write(clean_content)
            
            self.progress_updated.emit(f"Backups created: {raw_backup_path}")
            
        except Exception as e:
            self.log_message(f"Warning: Could not create backup: {str(e)}", MessageWarning)
    
    def _modify_qgs_datasources(self, qgs_path, new_params):
        """Modify datasource connections in QGS file - manual parsing approach."""
        try:
            # Read QGS file
            with open(qgs_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            modifications_count = 0
            
            mode = new_params.get('__mode__', 'explicit')
            
            # Build working params (exclude internal keys)
            params_to_change = {}
            for param_name, new_value in new_params.items():
                if param_name.startswith('_'):
                    continue
                if isinstance(new_value, str) and new_value.strip():
                    params_to_change[param_name] = new_value.strip()
                elif isinstance(new_value, dict):
                    params_to_change[param_name] = new_value
            
            if not params_to_change:
                self.progress_updated.emit("No parameters to change")
                return False
            
            self.progress_updated.emit(f"Mode: {mode}, parameters: {list(params_to_change.keys())}")
            
            # Find all datasource tags and their positions
            datasource_pattern = r'<datasource>([^<]+)</datasource>'
            matches = list(re.finditer(datasource_pattern, content))
            
            # Process matches in reverse order to avoid position shifts
            for match in reversed(matches):
                full_match = match.group(0)
                datasource_content = match.group(1)
                start_pos = match.start()
                end_pos = match.end()
                
                # Parse the datasource content into key-value pairs
                original_params = self._parse_datasource_simple(datasource_content)
                
                # Skip non-PostgreSQL datasources (must have table= or service= or dbname=)
                if not any(k in original_params for k in ('table', 'service', 'dbname')):
                    continue
                
                if mode == 'service':
                    new_datasource_content = self._apply_service_mode(
                        datasource_content, original_params, params_to_change)
                else:
                    new_datasource_content = self._apply_explicit_mode(
                        datasource_content, original_params, params_to_change)
                
                if new_datasource_content != datasource_content:
                    modifications_count += 1
                    new_full_datasource = f'<datasource>{new_datasource_content}</datasource>'
                    content = content[:start_pos] + new_full_datasource + content[end_pos:]
                    
                    table_name = original_params.get('table', 'unknown')
                    self.progress_updated.emit(f"Updated datasource {modifications_count}: {table_name}")
                    self.progress_updated.emit(f"  Original: {datasource_content[:100]}...")
                    self.progress_updated.emit(f"  Modified: {new_datasource_content[:100]}...")
            
            # Also update source= attributes in layer-tree-layer and other XML attributes
            # These use &quot; for quotes in attribute values
            content = self._update_source_attributes(content, new_params, mode)
            
            # Write modified content back only if changes were made
            if content != original_content:
                with open(qgs_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.progress_updated.emit(f"Successfully updated {modifications_count} datasource connections")
                return True
            else:
                self.progress_updated.emit("No datasource connections were changed")
                return False
            
        except Exception as e:
            raise Exception(f"Error modifying QGS datasources: {str(e)}")
    
    def _apply_service_mode(self, datasource_content, original_params, params_to_change):
        """Apply service mode: replace explicit credentials with service='name'."""
        result = datasource_content
        service_name = params_to_change.get('service', '')
        
        if not service_name:
            return result
        
        # Remove explicit connection parameters
        for param in ['host', 'dbname', 'port', 'user', 'password']:
            # Remove param='value' (with quotes)
            result = re.sub(rf"\s*{param}='[^']*'", '', result)
            result = re.sub(rf'\s*{param}="[^"]*"', '', result)
            # Remove param=value (without quotes)
            result = re.sub(rf"\s*{param}=[^\s'\"]+", '', result)
        
        # Add or replace service parameter
        if 'service' in original_params:
            # Replace existing service
            result = re.sub(r"service='[^']*'", f"service='{service_name}'", result)
            result = re.sub(r'service="[^"]*"', f"service='{service_name}'", result)
            result = re.sub(r"service=[^\s'\"]+", f"service='{service_name}'", result)
        else:
            # Prepend service= at the beginning of the datasource string
            result = f"service='{service_name}' {result.strip()}"
        
        # Handle schema remapping (same logic as explicit mode)
        result = self._apply_schema_changes(result, original_params, params_to_change)
        
        # Clean up whitespace
        result = re.sub(r'\s+', ' ', result).strip()
        
        return result
    
    def _apply_explicit_mode(self, datasource_content, original_params, params_to_change):
        """Apply explicit mode: update individual parameters, remove service= if explicit params given."""
        new_params_dict = original_params.copy()
        datasource_changed = False
        result = datasource_content
        
        # If we're providing explicit connection params, remove service=
        explicit_conn_params = [k for k in params_to_change if k in ('host', 'dbname', 'port', 'user', 'password')]
        if explicit_conn_params and 'service' in original_params:
            result = re.sub(r"\s*service='[^']*'", '', result)
            result = re.sub(r'\s*service="[^"]*"', '', result)
            result = re.sub(r"\s*service=[^\s'\"]+", '', result)
            datasource_changed = True
        
        # Apply parameter changes
        for param in ['dbname', 'host', 'port', 'user', 'password']:
            if param in params_to_change:
                new_value = params_to_change[param]
                if param in original_params:
                    # Replace existing
                    new_params_dict[param] = new_value
                    datasource_changed = True
                elif 'service' in original_params or datasource_changed:
                    # Adding new param when switching from service to explicit
                    # Find a good position: before key= or table=
                    insert_patterns = ['key=', 'table=', 'srid=', 'type=']
                    inserted = False
                    for ip in insert_patterns:
                        if ip in result:
                            result = result.replace(ip, f"{param}='{new_value}' {ip}", 1)
                            inserted = True
                            break
                    if not inserted:
                        result = f"{param}='{new_value}' {result.strip()}"
                    datasource_changed = True
        
        # If we changed existing params, rebuild via the replacement approach
        if datasource_changed:
            result = self._rebuild_datasource_simple(result, new_params_dict)
        
        # Handle schema changes
        result = self._apply_schema_changes(result, original_params, params_to_change)
        if result != datasource_content:
            datasource_changed = True
        
        # Clean up whitespace
        result = re.sub(r'\s+', ' ', result).strip()
        
        return result if datasource_changed else datasource_content
    
    def _apply_schema_changes(self, datasource_content, original_params, params_to_change):
        """Apply schema changes to a datasource string."""
        result = datasource_content
        
        if 'schema' in params_to_change and 'table' in original_params:
            table_value = original_params['table']
            new_schema = params_to_change['schema']
            if '.' in table_value:
                if table_value.startswith('"'):
                    parts = table_value.split('"."', 1)
                    if len(parts) == 2:
                        old_table = f'{parts[0]}"."{parts[1]}'
                        new_table = f'"{new_schema}"."{parts[1]}'
                        result = result.replace(old_table, new_table)
                else:
                    parts = table_value.split('.', 1)
                    if len(parts) == 2:
                        result = result.replace(
                            f'{parts[0]}.{parts[1]}',
                            f'{new_schema}.{parts[1]}'
                        )
        
        if 'schema_remapping' in params_to_change and 'table' in original_params:
            remap = params_to_change['schema_remapping']
            table_value = original_params['table']
            source = remap['source']
            target = remap['target']
            
            if table_value.startswith('"'):
                if f'"{source}".' in table_value:
                    result = result.replace(f'"{source}".', f'"{target}".')
            else:
                if f'{source}.' in table_value:
                    result = result.replace(f'{source}.', f'{target}.')
        
        return result
    
    def _update_source_attributes(self, content, new_params, mode):
        """Update source= attributes in XML elements (layer-tree-layer, GPS settings, etc.)."""
        # These attributes use &quot; for quotes inside attribute values
        source_attr_pattern = r'(source|destinationLayerSource)="([^"]*)"'
        
        def replace_source_attr(match):
            attr_name = match.group(1)
            attr_value = match.group(2)
            
            # Only process PostgreSQL sources (contain service= or dbname=)
            if 'service=' not in attr_value and 'dbname=' not in attr_value:
                return match.group(0)
            
            # Decode &quot; to " for processing
            decoded = attr_value.replace('&quot;', '"')
            
            original_params = self._parse_datasource_simple(decoded)
            
            if mode == 'service':
                modified = self._apply_service_mode(decoded, original_params, 
                    {k: v for k, v in new_params.items() if not k.startswith('_')})
            else:
                modified = self._apply_explicit_mode(decoded, original_params,
                    {k: v for k, v in new_params.items() if not k.startswith('_')})
            
            if modified != decoded:
                # Re-encode " to &quot; for XML attribute
                encoded = modified.replace('"', '&quot;')
                return f'{attr_name}="{encoded}"'
            
            return match.group(0)
        
        return re.sub(source_attr_pattern, replace_source_attr, content)
    
    def _parse_datasource_simple(self, datasource_content):
        """Simple parser to extract key=value pairs from datasource string."""
        params = {}
        
        # Use regex to find all key=value pairs, handling quoted and unquoted values
        patterns = [
            r"(\w+)='([^']*)'",     # key='value'
            r'(\w+)="([^"]*)"',     # key="value"  
            r"(\w+)=([^\s'\"]+)"    # key=value (no quotes, no spaces)
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, datasource_content)
            for key, value in matches:
                if key not in params:  # Don't overwrite already found values
                    params[key] = value
        
        return params
    
    def _rebuild_datasource_simple(self, original_datasource, new_params):
        """Rebuild datasource string by replacing only changed parameters."""
        result = original_datasource
        
        # Replace each parameter individually using precise regex
        for key, new_value in new_params.items():
            # Try different quote formats
            patterns_replacements = [
                (rf"{re.escape(key)}='[^']*'", f"{key}='{new_value}'"),
                (rf'{re.escape(key)}="[^"]*"', f'{key}="{new_value}"'),
                (rf"{re.escape(key)}=[^\s'\"]+", f"{key}={new_value}")
            ]
            
            for pattern, replacement in patterns_replacements:
                new_result = re.sub(pattern, replacement, result)
                if new_result != result:
                    result = new_result
                    break  # Found and replaced, move to next parameter
        
        return result
    
    def _upload_project_content(self, database_name, schema, table, project_name, content):
        """Upload fixed project content back to database."""
        try:
            self.progress_updated.emit("Uploading fixed project...")
            
            # Ensure content is bytes
            if not isinstance(content, bytes):
                if isinstance(content, memoryview):
                    content = content.tobytes()
                else:
                    content = bytes(content)
            
            conn_params = self.connection_params.copy()
            conn_params['database'] = database_name
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            query = f'UPDATE "{schema}"."{table}" SET content = %s WHERE name = %s;'
            cursor.execute(query, (content, project_name))
            
            if cursor.rowcount == 0:
                raise Exception(f"No project named '{project_name}' was found to update")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            self.progress_updated.emit(f"Project uploaded successfully ({len(content)} bytes)")
            return True
            
        except psycopg2.Error as e:
            self.log_message(f"Error uploading project content: {str(e)}", MessageCritical)
            return False

    def get_active_connections(self, database_name):
        """Get list of active connections to a specific database."""
        try:
            conn_params = self.connection_params.copy()
            conn_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            try:
                # Query to get active connections (excluding our own connection)
                query = """
                    SELECT 
                        pid,
                        usename,
                        client_addr,
                        client_hostname,
                        client_port,
                        backend_start,
                        state,
                        query
                    FROM pg_stat_activity 
                    WHERE datname = %s 
                    AND pid != pg_backend_pid()
                    AND state != 'idle'
                    ORDER BY backend_start;
                """
                
                cursor.execute(query, (database_name,))
                connections = cursor.fetchall()
                
                return connections
                
            except psycopg2.Error as db_error:
                self.log_message(f"Database error getting active connections: {str(db_error)}", MessageCritical)
                return []
            finally:
                cursor.close()
                conn.close()
            
        except psycopg2.Error as e:
            self.log_message(f"Error getting active connections: {str(e)}", MessageCritical)
            return []

    def get_connection_count(self, database_name):
        """Get count of active connections to a specific database."""
        try:
            conn_params = self.connection_params.copy()
            conn_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            try:
                # Count connections excluding our own
                query = """
                    SELECT COUNT(*) 
                    FROM pg_stat_activity 
                    WHERE datname = %s 
                    AND pid != pg_backend_pid();
                """
                
                cursor.execute(query, (database_name,))
                result = cursor.fetchone()
                count = result[0] if result and len(result) > 0 else 0
                
                return count
                
            except psycopg2.Error as db_error:
                self.log_message(f"Database error getting connection count: {str(db_error)}", MessageCritical)
                return 0
            finally:
                cursor.close()
                conn.close()
            
        except psycopg2.Error as e:
            self.log_message(f"Error getting connection count: {str(e)}", MessageCritical)
            return 0

    def drop_database_connections(self, database_name):
        """Drop all active connections to a specific database."""
        try:
            self.progress_updated.emit(f"Dropping active connections to '{database_name}'...")
            
            conn_params = self.connection_params.copy()
            conn_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**conn_params)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Get connection details before dropping
            connections = self.get_active_connections(database_name)
            
            if connections:
                self.progress_updated.emit(f"Found {len(connections)} active connections to drop")
                
                # Log connection details
                for conn_info in connections:
                    pid, username, client_addr, client_hostname, client_port, backend_start, state, query = conn_info
                    self.log_message(f"Dropping connection: PID={pid}, User={username}, Client={client_addr or client_hostname}", MessageInfo)
            
            # Drop all connections to the database (excluding our own)
            terminate_query = """
                SELECT pg_terminate_backend(pid) 
                FROM pg_stat_activity 
                WHERE datname = %s 
                AND pid != pg_backend_pid();
            """
            
            cursor.execute(terminate_query, (database_name,))
            terminated_connections = cursor.fetchall()
            
            # Count successful terminations
            successful_terminations = sum(1 for result in terminated_connections if result[0])
            
            cursor.close()
            conn.close()
            
            self.progress_updated.emit(f"Successfully dropped {successful_terminations} connections")
            return True
            
        except psycopg2.Error as e:
            error_msg = f"Error dropping database connections: {str(e)}"
            self.log_message(error_msg, MessageCritical)
            self.progress_updated.emit(error_msg)
            return False

    def create_template(self, source_db, template_name, template_comment=None, 
                    preserve_qgis_projects=False, excluded_schemas=None):
        """Create a template from source database with optional comment and data preservation options."""
        try:
            if excluded_schemas is None:
                excluded_schemas = []
            
            self.progress_updated.emit(f"Creating template '{template_name}' from '{source_db}'...")
            
            # Log preservation settings
            if preserve_qgis_projects or excluded_schemas:
                preservation_info = []
                if preserve_qgis_projects:
                    preservation_info.append("qgis_projects table will be preserved")
                if excluded_schemas:
                    preservation_info.append(f"schemas {excluded_schemas} will be preserved")
                self.progress_updated.emit(f"Data preservation: {'; '.join(preservation_info)}")
            
            # Check for active connections first
            connection_count = self.get_connection_count(source_db)
            if connection_count > 0:
                self.progress_updated.emit(f"Found {connection_count} active connections to '{source_db}'")
                
                # Drop connections
                if not self.drop_database_connections(source_db):
                    raise Exception("Failed to drop database connections")
                
                # Wait a moment for connections to be fully dropped
                import time
                time.sleep(1)
                
                # Verify connections are dropped
                remaining_connections = self.get_connection_count(source_db)
                if remaining_connections > 0:
                    raise Exception(f"Still {remaining_connections} active connections after termination")
            
            conn_params = self.connection_params.copy()
            conn_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**conn_params)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Drop existing template if it exists
            if self.database_exists(template_name):
                self.progress_updated.emit(f"Dropping existing template '{template_name}'...")
                cursor.execute(f'DROP DATABASE "{template_name}";')
            
            # Create template database
            cursor.execute(f'CREATE DATABASE "{template_name}" WITH TEMPLATE "{source_db}" IS_TEMPLATE = true;')
            
            # Add comment if provided
            if template_comment:
                self.progress_updated.emit(f"Adding comment to template...")
                # Escape single quotes in comment
                escaped_comment = template_comment.replace("'", "''")
                cursor.execute(f"COMMENT ON DATABASE \"{template_name}\" IS '{escaped_comment}';")
                self.progress_updated.emit(f"Comment added: {template_comment}")
            
            # Connect to template database to remove data selectively
            cursor.close()
            conn.close()
            
            template_conn_params = self.connection_params.copy()
            template_conn_params['database'] = template_name
            
            template_conn = psycopg2.connect(**template_conn_params)
            template_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            template_cursor = template_conn.cursor()
            
            # Get all user tables
            template_cursor.execute("""
                SELECT schemaname, tablename 
                FROM pg_tables 
                WHERE schemaname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                ORDER BY schemaname, tablename;
            """)
            
            tables = template_cursor.fetchall()
            
            # Process tables with selective preservation
            truncated_count = 0
            preserved_count = 0
            
            self.progress_updated.emit("Processing tables with data preservation rules...")
            
            for schema, table in tables:
                # Check if this schema should be excluded entirely
                if schema in excluded_schemas:
                    self.progress_updated.emit(f"Preserving data in {schema}.{table} (excluded schema)")
                    preserved_count += 1
                    continue
                
                # Check if this is the qgis_projects table and should be preserved
                if preserve_qgis_projects and table == 'qgis_projects':
                    self.progress_updated.emit(f"Preserving data in {schema}.{table} (qgis_projects table)")
                    preserved_count += 1
                    continue
                
                # Truncate this table
                try:
                    template_cursor.execute(f'TRUNCATE TABLE "{schema}"."{table}" CASCADE;')
                    self.progress_updated.emit(f"Cleared data from {schema}.{table}")
                    truncated_count += 1
                except psycopg2.Error as e:
                    self.log_message(f"Warning: Could not truncate {schema}.{table}: {str(e)}", MessageWarning)
            
            template_cursor.close()
            template_conn.close()
            
            # Prepare success message with detailed info
            success_msg = f"Template '{template_name}' created successfully!"
            if template_comment:
                success_msg += f" Comment: {template_comment}"
            
            details = []
            if truncated_count > 0:
                details.append(f"{truncated_count} tables truncated")
            if preserved_count > 0:
                details.append(f"{preserved_count} tables preserved")
            
            if details:
                success_msg += f" ({', '.join(details)})"
            
            self.progress_updated.emit(success_msg)
            self.operation_finished.emit(True, success_msg)
            return True
            
        except psycopg2.Error as e:
            error_msg = f"Error creating template: {str(e)}"
            self.log_message(error_msg, MessageCritical)
            self.operation_finished.emit(False, error_msg)
            return False
    
    def create_database_from_template(self, template_name, new_db_name, db_comment=None):
        """Create a new database from template with optional comment."""
        try:
            self.progress_updated.emit(f"Creating database '{new_db_name}' from template '{template_name}'...")
            
            # Check for active connections to the template database first
            connection_count = self.get_connection_count(template_name)
            if connection_count > 0:
                self.progress_updated.emit(f"Found {connection_count} active connections to template '{template_name}'")
                
                # Drop connections
                if not self.drop_database_connections(template_name):
                    raise Exception("Failed to drop database connections to template")
                
                # Wait a moment for connections to be fully dropped
                import time
                time.sleep(1)
                
                # Verify connections are dropped
                remaining_connections = self.get_connection_count(template_name)
                if remaining_connections > 0:
                    raise Exception(f"Still {remaining_connections} active connections to template after termination")
            
            conn_params = self.connection_params.copy()
            conn_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**conn_params)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Drop existing database if it exists
            if self.database_exists(new_db_name):
                self.progress_updated.emit(f"Dropping existing database '{new_db_name}'...")
                cursor.execute(f'DROP DATABASE "{new_db_name}";')
            
            # Create database from template
            cursor.execute(f'CREATE DATABASE "{new_db_name}" WITH TEMPLATE "{template_name}";')
            
            # Add comment if provided
            if db_comment:
                self.progress_updated.emit(f"Adding comment to database...")
                # Escape single quotes in comment
                escaped_comment = db_comment.replace("'", "''")
                cursor.execute(f"COMMENT ON DATABASE \"{new_db_name}\" IS '{escaped_comment}';")
                self.progress_updated.emit(f"Comment added: {db_comment}")
            
            cursor.close()
            conn.close()
            
            success_msg = f"Database '{new_db_name}' created successfully from template '{template_name}'!"
            if db_comment:
                success_msg += f" Comment: {db_comment}"
            
            self.progress_updated.emit(success_msg)
            self.operation_finished.emit(True, success_msg)
            return True
            
        except psycopg2.Error as e:
            error_msg = f"Error creating database: {str(e)}"
            self.log_message(error_msg, MessageCritical)
            self.operation_finished.emit(False, error_msg)
            return False    

    def delete_template(self, template_name):
        """Delete a template."""
        try:
            self.progress_updated.emit(f"Deleting template '{template_name}'...")
            
            conn_params = self.connection_params.copy()
            conn_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**conn_params)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Deactivate template status
            cursor.execute(f"UPDATE pg_database SET datistemplate = false WHERE datname = '{template_name}';")
            
            # Drop database
            cursor.execute(f'DROP DATABASE "{template_name}";')
            
            cursor.close()
            conn.close()
            
            success_msg = f"Template '{template_name}' deleted successfully!"
            self.progress_updated.emit(success_msg)
            self.operation_finished.emit(True, success_msg)
            return True
            
        except psycopg2.Error as e:
            error_msg = f"Error deleting template: {str(e)}"
            self.log_message(error_msg, MessageCritical)
            self.operation_finished.emit(False, error_msg)
            return False

    def get_templates_with_comments(self):
        """Get list of template databases with their comments."""
        try:
            conn_params = self.connection_params.copy()
            conn_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            try:
                query = """
                    SELECT 
                        d.datname,
                        shobj_description(d.oid, 'pg_database') as comment
                    FROM pg_database d
                    WHERE d.datistemplate = true 
                    AND d.datname NOT IN ('template0', 'template1')
                    ORDER BY d.datname;
                """
                
                cursor.execute(query)
                results = cursor.fetchall()
                
                templates = []
                for row in results:
                    if row and len(row) >= 2:
                        templates.append((str(row[0]), row[1]))
                
                return templates
                
            except psycopg2.Error as db_error:
                self.log_message(f"Database error getting templates with comments: {str(db_error)}", MessageCritical)
                return []
            finally:
                cursor.close()
                conn.close()
            
        except psycopg2.Error as e:
            self.log_message(f"Error getting templates with comments: {str(e)}", MessageCritical)
            return []

    def get_database_comment(self, db_name):
        """Get comment for a specific database."""
        try:
            conn_params = self.connection_params.copy()
            conn_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            try:
                query = """
                    SELECT obj_description(d.oid, 'pg_database') as comment
                    FROM pg_database d
                    WHERE d.datname = %s;
                """
                
                cursor.execute(query, (db_name,))
                result = cursor.fetchone()
                
                return result[0] if result and len(result) > 0 else None
                
            except psycopg2.Error as db_error:
                self.log_message(f"Database error getting database comment: {str(db_error)}", MessageCritical)
                return None
            finally:
                cursor.close()
                conn.close()
            
        except psycopg2.Error as e:
            self.log_message(f"Error getting database comment: {str(e)}", MessageCritical)
            return None
        
    def get_databases_with_comments(self):
        """Get list of non-template databases with their comments."""
        try:
            conn_params = self.connection_params.copy()
            conn_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            try:
                query = """
                    SELECT 
                        d.datname,
                        shobj_description(d.oid, 'pg_database') as comment
                    FROM pg_database d
                    WHERE d.datistemplate = false 
                    AND d.datname NOT IN ('postgres', 'template0', 'template1')
                    ORDER BY d.datname;
                """
                
                cursor.execute(query)
                results = cursor.fetchall()
                
                databases = []
                for row in results:
                    if row and len(row) >= 2:
                        databases.append((str(row[0]), row[1]))
                
                return databases
                
            except psycopg2.Error as db_error:
                self.log_message(f"Database error getting databases with comments: {str(db_error)}", MessageCritical)
                return []
            finally:
                cursor.close()
                conn.close()
            
        except psycopg2.Error as e:
            self.log_message(f"Error getting databases with comments: {str(e)}", MessageCritical)
            return []
        
    def create_database_from_database(self, source_db_name, new_db_name, db_comment=None):
        """Create a new database from an existing database (copy)."""
        try:
            self.progress_updated.emit(f"Creating database '{new_db_name}' from existing database '{source_db_name}'...")
            
            # Check for active connections to the source database first
            connection_count = self.get_connection_count(source_db_name)
            if connection_count > 0:
                self.progress_updated.emit(f"Found {connection_count} active connections to source database '{source_db_name}'")
                
                # Drop connections
                if not self.drop_database_connections(source_db_name):
                    raise Exception("Failed to drop database connections to source database")
                
                # Wait a moment for connections to be fully dropped
                import time
                time.sleep(1)
                
                # Verify connections are dropped
                remaining_connections = self.get_connection_count(source_db_name)
                if remaining_connections > 0:
                    raise Exception(f"Still {remaining_connections} active connections to source database after termination")
            
            conn_params = self.connection_params.copy()
            conn_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**conn_params)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Drop existing database if it exists
            if self.database_exists(new_db_name):
                self.progress_updated.emit(f"Dropping existing database '{new_db_name}'...")
                cursor.execute(f'DROP DATABASE "{new_db_name}";')
            
            # Create database from source database (includes data)
            cursor.execute(f'CREATE DATABASE "{new_db_name}" WITH TEMPLATE "{source_db_name}";')
            
            # Add comment if provided
            if db_comment:
                self.progress_updated.emit(f"Adding comment to database...")
                # Escape single quotes in comment
                escaped_comment = db_comment.replace("'", "''")
                cursor.execute(f"COMMENT ON DATABASE \"{new_db_name}\" IS '{escaped_comment}';")
                self.progress_updated.emit(f"Comment added: {db_comment}")
            
            cursor.close()
            conn.close()
            
            success_msg = f"Database '{new_db_name}' created successfully from existing database '{source_db_name}'!"
            if db_comment:
                success_msg += f" Comment: {db_comment}"
            
            self.progress_updated.emit(success_msg)
            self.operation_finished.emit(True, success_msg)
            return True
            
        except psycopg2.Error as e:
            error_msg = f"Error creating database from existing database: {str(e)}"
            self.log_message(error_msg, MessageCritical)
            self.operation_finished.emit(False, error_msg)
            return False
        
    def get_database_schemas(self, database_name):
        """Get list of schemas in the specified database."""
        try:
            if not database_name or not isinstance(database_name, str):
                self.log_message(f"Invalid database_name: {database_name}", MessageCritical)
                return []
            
            conn_params = self.connection_params.copy()
            conn_params['database'] = database_name
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            try:
                query = """
                    SELECT schema_name 
                    FROM information_schema.schemata 
                    WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast', 'pg_temp_1', 'pg_toast_temp_1')
                    AND schema_name NOT LIKE 'pg_temp_%'
                    AND schema_name NOT LIKE 'pg_toast_temp_%'
                    ORDER BY schema_name;
                """
                
                cursor.execute(query)
                results = cursor.fetchall()
                
                schemas = []
                for row in results:
                    if row and len(row) > 0 and row[0] is not None:
                        schemas.append(str(row[0]))
                
                return schemas
                
            except psycopg2.Error as db_error:
                self.log_message(f"Database error getting schemas for database '{database_name}': {str(db_error)}", MessageCritical)
                return []
            finally:
                cursor.close()
                conn.close()
            
        except psycopg2.Error as e:
            self.log_message(f"PostgreSQL error getting schemas for database '{database_name}': {str(e)}", MessageCritical)
            return []
        except Exception as e:
            self.log_message(f"Unexpected error getting schemas for database '{database_name}': {str(e)}", MessageCritical)
            return []


    def get_schema_tables(self, database_name, schema_name):
        """Get list of tables in the specified schema."""
        try:
            # Validate inputs
            if not database_name or not isinstance(database_name, str):
                self.log_message(f"Invalid database_name: {database_name}", MessageCritical)
                return []
            
            if not schema_name or not isinstance(schema_name, str):
                self.log_message(f"Invalid schema_name: {schema_name}", MessageCritical)
                return []
            
            self.progress_updated.emit(f"Getting tables for schema '{schema_name}' in database '{database_name}'...")
            
            conn_params = self.connection_params.copy()
            conn_params['database'] = database_name
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            try:
                # First, verify that the schema exists
                schema_check_query = """
                    SELECT schema_name 
                    FROM information_schema.schemata 
                    WHERE schema_name = %s;
                """
                
                cursor.execute(schema_check_query, (schema_name,))
                schema_result = cursor.fetchone()
                
                # Check if schema exists
                if schema_result is None:
                    self.log_message(f"Schema '{schema_name}' does not exist in database '{database_name}'", MessageWarning)
                    return []
                
                # Use string formatting approach (safe because we validated schema_name)
                # Escape single quotes in schema_name to prevent SQL injection
                safe_schema_name = schema_name.replace("'", "''")
                
                query = f"""
                    SELECT tablename 
                    FROM pg_tables 
                    WHERE schemaname = '{safe_schema_name}'
                    AND tablename NOT LIKE 'pg_%'
                    ORDER BY tablename;
                """
                
                cursor.execute(query)
                results = cursor.fetchall()
                
                # Process the results safely
                tables = []
                for row in results:
                    if row and len(row) > 0 and row[0] is not None:
                        tables.append(str(row[0]))
                
                self.progress_updated.emit(f"Found {len(tables)} tables in schema '{schema_name}'")
                return tables
                
            except psycopg2.Error as db_error:
                self.log_message(f"Database error getting tables for schema '{schema_name}': {str(db_error)}", MessageCritical)
                return []
            finally:
                cursor.close()
                conn.close()
            
        except psycopg2.Error as e:
            self.log_message(f"PostgreSQL error getting tables for schema '{schema_name}' in database '{database_name}': {str(e)}", MessageCritical)
            return []
        except Exception as e:
            self.log_message(f"Unexpected error getting tables for schema '{schema_name}' in database '{database_name}': {str(e)}", MessageCritical)
            return []

    def get_database_tables(self, database_name):
        """Get list of tables in the specified database (fallback method)."""
        try:
            if not database_name or not isinstance(database_name, str):
                self.log_message(f"Invalid database_name: {database_name}", MessageCritical)
                return []
            
            conn_params = self.connection_params.copy()
            conn_params['database'] = database_name
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            try:
                query = """
                    SELECT tablename 
                    FROM pg_tables 
                    WHERE schemaname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                    AND tablename NOT LIKE 'pg_%'
                    ORDER BY tablename;
                """
                
                cursor.execute(query)
                results = cursor.fetchall()
                
                tables = []
                for row in results:
                    if row and len(row) > 0 and row[0] is not None:
                        tables.append(str(row[0]))
                
                return tables
                
            except psycopg2.Error as db_error:
                self.log_message(f"Database error getting tables for database '{database_name}': {str(db_error)}", MessageCritical)
                return []
            finally:
                cursor.close()
                conn.close()
            
        except psycopg2.Error as e:
            self.log_message(f"PostgreSQL error getting tables for database '{database_name}': {str(e)}", MessageCritical)
            return []
        except Exception as e:
            self.log_message(f"Unexpected error getting tables for database '{database_name}': {str(e)}", MessageCritical)
            return []

    def truncate_schema_tables(self, database_name, schema_name, table_names):
        """Truncate specified tables in the given schema."""
        try:
            self.progress_updated.emit(f"Truncating {len(table_names)} tables in schema '{schema_name}' of database '{database_name}'...")
            
            conn_params = self.connection_params.copy()
            conn_params['database'] = database_name
            
            conn = psycopg2.connect(**conn_params)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            try:
                truncated_count = 0
                failed_tables = []
                
                for table_name in table_names:
                    try:
                        # Use CASCADE to handle foreign key constraints
                        cursor.execute(f'TRUNCATE TABLE "{schema_name}"."{table_name}" CASCADE;')
                        truncated_count += 1
                        self.progress_updated.emit(f"Truncated: {schema_name}.{table_name}")
                        
                    except psycopg2.Error as table_error:
                        failed_tables.append(table_name)
                        self.log_message(f"Failed to truncate {schema_name}.{table_name}: {str(table_error)}", MessageWarning)
                        self.progress_updated.emit(f"Failed to truncate: {schema_name}.{table_name} - {str(table_error)}")
                
                # Prepare result message
                if truncated_count > 0:
                    success_msg = f"Successfully truncated {truncated_count} table(s) in schema '{schema_name}'"
                    if failed_tables:
                        success_msg += f" (Failed: {len(failed_tables)} table(s))"
                    
                    self.progress_updated.emit(success_msg)
                    self.operation_finished.emit(True, success_msg)
                    return True
                else:
                    error_msg = f"No tables were truncated in schema '{schema_name}'"
                    self.operation_finished.emit(False, error_msg)
                    return False
                    
            except psycopg2.Error as db_error:
                error_msg = f"Database error truncating tables in schema '{schema_name}': {str(db_error)}"
                self.log_message(error_msg, MessageCritical)
                self.operation_finished.emit(False, error_msg)
                return False
            finally:
                cursor.close()
                conn.close()
            
        except psycopg2.Error as e:
            error_msg = f"Error truncating tables in schema '{schema_name}': {str(e)}"
            self.log_message(error_msg, MessageCritical)
            self.operation_finished.emit(False, error_msg)
            return False