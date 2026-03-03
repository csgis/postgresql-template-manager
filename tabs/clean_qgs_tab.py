"""
Clean QGS tab for removing database credentials from QGIS project files.
"""

import os
import re
import configparser
import xml.etree.ElementTree as ET
from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.PyQt.QtWidgets import (QVBoxLayout, QHBoxLayout, QFormLayout, 
                                QPushButton, QGroupBox, QLabel, QLineEdit,
                                QFileDialog, QMessageBox, QTextEdit, QCheckBox,
                                QTableWidget, QTableWidgetItem, QHeaderView)
from qgis.PyQt.QtGui import QFont
from .base_tab import BaseTab
from ..compat import ElideNone, MsgBoxOk, ResizeToContents, RichText, SelectRows, Stretch


class CleanQGSTab(BaseTab):
    """Tab for cleaning database credentials from QGIS project files."""
    
    # Signals
    file_cleaned = pyqtSignal(str)  # Cleaned file path
    
    def __init__(self, db_manager, parent=None):
        super().__init__(db_manager, parent)
    
    def setup_ui(self):
        """Setup the clean QGS tab UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title and help button section
        title_layout = QHBoxLayout()
        title_label = QLabel("QGS File Credential Cleaner")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        
        self.help_btn = QPushButton("Help")
        self.help_btn.setFixedWidth(80)
        self.help_btn.setStyleSheet(
            "QPushButton { "
            "background-color: #2196F3; "
            "color: white; "
            "font-weight: bold; "
            "padding: 5px 10px; "
            "border: none; "
            "border-radius: 4px; "
            "font-size: 12px; "
            "} "
            "QPushButton:hover { background-color: #1976D2; }"
        )
        self.help_btn.clicked.connect(self._show_help_popup)
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.help_btn)
        layout.addLayout(title_layout)
        
        # File selection section
        file_section = QGroupBox("Select QGS File")
        file_layout = QVBoxLayout(file_section)
        
        file_select_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select a QGIS project file (.qgs or .qgz)")
        self.file_path_edit.setReadOnly(True)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_file)
        
        file_select_layout.addWidget(self.file_path_edit)
        file_select_layout.addWidget(self.browse_btn)
        file_layout.addLayout(file_select_layout)
        
        layout.addWidget(file_section)
        
        # Options section
        options_section = QGroupBox("Cleaning Options")
        options_layout = QVBoxLayout(options_section)
        
        self.remove_user_checkbox = QCheckBox("Remove user credentials")
        self.remove_user_checkbox.setChecked(True)
        self.remove_user_checkbox.setToolTip("Remove 'user' parameter from datasource connections")
        
        self.remove_password_checkbox = QCheckBox("Remove password credentials")
        self.remove_password_checkbox.setChecked(True)
        self.remove_password_checkbox.setToolTip("Remove 'password' parameter from datasource connections")
        
        options_layout.addWidget(self.remove_user_checkbox)
        options_layout.addWidget(self.remove_password_checkbox)
        
        layout.addWidget(options_section)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("Preview Changes")
        self.preview_btn.clicked.connect(self.preview_changes)
        self.preview_btn.setEnabled(False)
        
        self.clean_btn = QPushButton("Clean File")
        self.clean_btn.clicked.connect(self.clean_file)
        self.clean_btn.setEnabled(False)
        self.clean_btn.setStyleSheet(
            "QPushButton { "
            "background-color: #4CAF50; "
            "color: white; "
            "font-weight: bold; "
            "padding: 8px 16px; "
            "border: none; "
            "border-radius: 4px; "
            "} "
            "QPushButton:hover { background-color: #45a049; } "
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        
        action_layout.addWidget(self.preview_btn)
        action_layout.addStretch()
        action_layout.addWidget(self.clean_btn)
        layout.addLayout(action_layout)
        
        # Preview section
        preview_section = QGroupBox("Preview Changes")
        preview_layout = QVBoxLayout(preview_section)
        
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(3)
        self.preview_table.setHorizontalHeaderLabels(["#", "Original Datasource", "Cleaned Datasource"])
        
        # Configure table appearance
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setSelectionBehavior(SelectRows)
        self.preview_table.verticalHeader().setVisible(False)
        
        # Set column widths
        header = self.preview_table.horizontalHeader()
        header.setSectionResizeMode(0, ResizeToContents)  # # column
        header.setSectionResizeMode(1, Stretch)  # Original column
        header.setSectionResizeMode(2, Stretch)  # Cleaned column
        
        # Set maximum height and word wrap
        self.preview_table.setMaximumHeight(250)
        self.preview_table.setWordWrap(True)
        self.preview_table.setTextElideMode(ElideNone)
        
        # Add placeholder message
        self.preview_info_label = QLabel("Select a file and click 'Preview Changes' to see what will be modified...")
        self.preview_info_label.setStyleSheet("color: #666; font-style: italic; padding: 10px;")
        
        preview_layout.addWidget(self.preview_info_label)
        preview_layout.addWidget(self.preview_table)
        
        # Initially hide table and show info label
        self.preview_table.setVisible(False)
        
        layout.addWidget(preview_section)
        
        # ---- Service.conf section ----
        service_section = QGroupBox("PostgreSQL Service File (pg_service.conf)")
        service_layout = QVBoxLayout(service_section)
        
        service_file_layout = QHBoxLayout()
        self.service_file_edit = QLineEdit()
        self.service_file_edit.setPlaceholderText("Select a pg_service.conf file")
        self.service_file_edit.setReadOnly(True)
        
        self.browse_service_btn = QPushButton("Browse...")
        self.browse_service_btn.clicked.connect(self.browse_service_file)
        
        self.detect_service_btn = QPushButton("Auto-detect")
        self.detect_service_btn.setToolTip("Try to find pg_service.conf in standard locations")
        self.detect_service_btn.clicked.connect(self.detect_service_file)
        
        service_file_layout.addWidget(self.service_file_edit)
        service_file_layout.addWidget(self.browse_service_btn)
        service_file_layout.addWidget(self.detect_service_btn)
        service_layout.addLayout(service_file_layout)
        
        # Service cleaning options
        service_options_layout = QHBoxLayout()
        self.service_remove_password_cb = QCheckBox("Remove passwords")
        self.service_remove_password_cb.setChecked(True)
        self.service_remove_user_cb = QCheckBox("Remove users")
        self.service_remove_user_cb.setChecked(False)
        service_options_layout.addWidget(self.service_remove_password_cb)
        service_options_layout.addWidget(self.service_remove_user_cb)
        service_options_layout.addStretch()
        service_layout.addLayout(service_options_layout)
        
        # Service preview
        self.service_preview_text = QTextEdit()
        self.service_preview_text.setReadOnly(True)
        self.service_preview_text.setMaximumHeight(120)
        self.service_preview_text.setPlaceholderText("Service file contents will appear here...")
        service_layout.addWidget(self.service_preview_text)
        
        # Service action buttons
        service_btn_layout = QHBoxLayout()
        self.preview_service_btn = QPushButton("Preview")
        self.preview_service_btn.clicked.connect(self.preview_service_file)
        self.preview_service_btn.setEnabled(False)
        
        self.clean_service_btn = QPushButton("Clean Service File")
        self.clean_service_btn.clicked.connect(self.clean_service_file)
        self.clean_service_btn.setEnabled(False)
        self.clean_service_btn.setStyleSheet(
            "QPushButton { "
            "background-color: #4CAF50; "
            "color: white; "
            "font-weight: bold; "
            "padding: 8px 16px; "
            "border: none; "
            "border-radius: 4px; "
            "} "
            "QPushButton:hover { background-color: #45a049; } "
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        
        service_btn_layout.addWidget(self.preview_service_btn)
        service_btn_layout.addStretch()
        service_btn_layout.addWidget(self.clean_service_btn)
        service_layout.addLayout(service_btn_layout)
        
        layout.addWidget(service_section)
        
        # Connect service file path changes
        self.service_file_edit.textChanged.connect(self._on_service_file_path_changed)
        
        # Connect file path changes to enable/disable buttons
        self.file_path_edit.textChanged.connect(self._on_file_path_changed)
    
    def _show_help_popup(self):
        """Show help information in a popup dialog."""
        help_text = (
            "<h3>QGS File Credential Cleaner</h3>"
            "<p>This tool removes database credentials (user/password) from QGIS project files "
            "and PostgreSQL service configuration files.</p>"
            "<h4>QGS/QGZ Cleaning:</h4>"
            "<ul>"
            "<li>Scans the QGS/QGZ file for PostgreSQL datasource connections</li>"
            "<li>Shows a table preview of what will be changed</li>"
            "<li>Removes user and/or password parameters from connection strings</li>"
            "<li>Creates a cleaned version with '_cleaned' suffix</li>"
            "<li>Original file remains untouched</li>"
            "</ul>"
            "<h4>Example:</h4>"
            "<p><b>Before:</b> dbname='mydb' host=localhost user='admin' password='secret'</p>"
            "<p><b>After:</b> dbname='mydb' host=localhost</p>"
            "<h4>PostgreSQL Service File (pg_service.conf):</h4>"
            "<ul>"
            "<li><b>Auto-detect:</b> Searches standard locations for pg_service.conf</li>"
            "<li><b>Preview:</b> Shows services and which credentials will be removed</li>"
            "<li><b>Clean:</b> Creates a cleaned copy with '_cleaned' suffix</li>"
            "<li>Supports removing passwords and/or user entries from all services</li>"
            "</ul>"
            "<h4>Standard pg_service.conf locations:</h4>"
            "<ul>"
            "<li><b>Windows:</b> %APPDATA%\\postgresql\\pg_service.conf</li>"
            "<li><b>Linux/macOS:</b> ~/.pg_service.conf or /etc/pg_service.conf</li>"
            "<li><b>PGSERVICEFILE:</b> Custom path via environment variable</li>"
            "</ul>"
            "<h4>Supported file types:</h4>"
            "<ul>"
            "<li><b>.qgs files:</b> Direct XML processing</li>"
            "<li><b>.qgz files:</b> Extracts and processes the contained .qgs file</li>"
            "<li><b>pg_service.conf:</b> INI-style PostgreSQL connection configuration</li>"
            "</ul>"
        )
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Help - QGS File Credential Cleaner")
        msg.setTextFormat(RichText)  # Rich text format
        msg.setText(help_text)
        msg.setStandardButtons(MsgBoxOk)
        msg.exec()
    
    def _on_file_path_changed(self, text):
        """Enable/disable buttons based on file path."""
        has_file = bool(text.strip())
        self.preview_btn.setEnabled(has_file)
        self.clean_btn.setEnabled(has_file)
        
        # Clear preview when file changes
        if not has_file:
            self.preview_table.setRowCount(0)
            self.preview_table.setVisible(False)
            self.preview_info_label.setVisible(True)
            self.preview_info_label.setText("Select a file and click 'Preview Changes' to see what will be modified...")
            self.preview_info_label.setStyleSheet("color: #666; font-style: italic; padding: 10px;")
    
    def browse_file(self):
        """Browse for QGS file."""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self,
            "Select QGIS Project File",
            "",
            "QGIS Project Files (*.qgs *.qgz);;All Files (*)"
        )
        
        if file_path:
            self.file_path_edit.setText(file_path)
            self.emit_log(f"Selected file: {os.path.basename(file_path)}")
    
    def preview_changes(self):
        """Preview what changes will be made to the file."""
        file_path = self.file_path_edit.text().strip()
        if not file_path:
            return
        
        try:
            self.emit_progress_started()
            
            # Read and parse the file
            qgs_content = self._read_qgs_file(file_path)
            if not qgs_content:
                return
            
            # Find datasources that would be changed
            changes = self._find_datasource_changes(qgs_content)
            
            if changes:
                # Show table and hide info label
                self.preview_info_label.setVisible(False)
                self.preview_table.setVisible(True)
                
                # Populate table
                self.preview_table.setRowCount(len(changes))
                
                for i, (original, cleaned) in enumerate(changes):
                    # Datasource number
                    num_item = QTableWidgetItem(str(i + 1))
                    num_item.setFlags(num_item.flags() & ~2)  # Remove editable flag
                    self.preview_table.setItem(i, 0, num_item)
                    
                    # Original datasource
                    original_item = QTableWidgetItem(original)
                    original_item.setFlags(original_item.flags() & ~2)  # Remove editable flag
                    original_item.setToolTip(original)  # Full text in tooltip
                    self.preview_table.setItem(i, 1, original_item)
                    
                    # Cleaned datasource
                    cleaned_item = QTableWidgetItem(cleaned)
                    cleaned_item.setFlags(cleaned_item.flags() & ~2)  # Remove editable flag
                    cleaned_item.setToolTip(cleaned)  # Full text in tooltip
                    self.preview_table.setItem(i, 2, cleaned_item)
                
                # Auto-resize rows to content
                self.preview_table.resizeRowsToContents()
                
                self.emit_log(f"Preview completed: {len(changes)} type(s) of credentials found")
            else:
                # Hide table and show info message
                self.preview_table.setVisible(False)
                self.preview_info_label.setVisible(True)
                self.preview_info_label.setText("No credentials found in this file.")
                self.preview_info_label.setStyleSheet("color: #4CAF50; font-style: italic; padding: 10px;")
                
                self.emit_log("Preview completed: No credentials found")
            
        except Exception as e:
            self.show_error(f"Error previewing file: {str(e)}")
            self.emit_log(f"Error during preview: {str(e)}")
        finally:
            self.emit_progress_finished()
    
    def clean_file(self):
        """Clean the selected QGS file."""
        file_path = self.file_path_edit.text().strip()
        if not file_path:
            return
        
        if not os.path.exists(file_path):
            self.show_error("Selected file does not exist.")
            return
        
        try:
            self.emit_progress_started()
            
            # Read and parse the file
            qgs_content = self._read_qgs_file(file_path)
            if not qgs_content:
                return
            
            # Clean the content
            cleaned_content, changes_count = self._clean_datasources(qgs_content)
            
            if changes_count == 0:
                self.emit_log("No credentials found to clean in the file.")
                self.show_info("No credentials found to clean in the file.")
                return
            
            # Generate cleaned file path
            base_name, ext = os.path.splitext(file_path)
            cleaned_path = f"{base_name}_cleaned{ext}"
            
            # Write cleaned content
            self._write_qgs_file(cleaned_path, cleaned_content, file_path.endswith('.qgz'))
            
            # Emit success signal
            self.file_cleaned.emit(cleaned_path)
            
            success_msg = (f"✓ File cleaned successfully!\n"
                          f"• Removed {changes_count} credential(s)\n"
                          f"• Original file preserved\n"
                          f"• Saved to: {os.path.basename(cleaned_path)}")
            
            self.emit_log(success_msg.replace('\n', ' '))
            self.show_info(success_msg)
            
        except Exception as e:
            self.show_error(f"Error cleaning file: {str(e)}")
            self.emit_log(f"Error during cleaning: {str(e)}")
        finally:
            self.emit_progress_finished()
    
    def _read_qgs_file(self, file_path):
        """Read QGS file content (handles both .qgs and .qgz files)."""
        try:
            if file_path.endswith('.qgz'):
                import zipfile
                with zipfile.ZipFile(file_path, 'r') as zip_file:
                    # Find the .qgs file in the archive
                    qgs_files = [f for f in zip_file.namelist() if f.endswith('.qgs')]
                    if not qgs_files:
                        raise Exception("No .qgs file found in the .qgz archive")
                    
                    with zip_file.open(qgs_files[0]) as qgs_file:
                        return qgs_file.read().decode('utf-8')
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            self.show_error(f"Error reading file: {str(e)}")
            return None
    
    def _write_qgs_file(self, output_path, content, is_qgz=False):
        """Write QGS file content (handles both .qgs and .qgz files)."""
        if is_qgz:
            import zipfile
            import tempfile
            
            # Create a temporary .qgs file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.qgs', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(content)
                temp_qgs_path = temp_file.name
            
            try:
                # Create the .qgz file
                with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    zip_file.write(temp_qgs_path, os.path.basename(output_path).replace('.qgz', '.qgs'))
            finally:
                os.unlink(temp_qgs_path)
        else:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
    
    def _find_datasource_changes(self, content):
        """Find datasources that would be changed and return before/after pairs."""
        changes = []
        found_connections = set()  # To avoid duplicates
        
        # Pattern to find all PostgreSQL connection strings (containing dbname=)
        # This covers quoted strings, attribute values, and various formats
        patterns = [
            r'"[^"]*dbname=[^"]*"',     # Double-quoted strings
            r"'[^']*dbname=[^']*'",     # Single-quoted strings  
            r'(?:value|source|dataSource|destinationLayerSource)="([^"]*dbname=[^"]*)"',  # Attribute values
            r"(?:value|source|dataSource|destinationLayerSource)='([^']*dbname=[^']*)'",  # Single-quoted attribute values
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                # Get the connection string (either full match or group 1 if it's an attribute)
                if match.groups():
                    connection_string = match.group(1)
                else:
                    connection_string = match.group(0)
                
                # Skip if we've already found this connection string
                if connection_string in found_connections:
                    continue
                
                # Check if this connection string has credentials we want to remove
                if self._has_postgres_credentials(connection_string):
                    cleaned = self._clean_single_datasource(connection_string)
                    if cleaned != connection_string:
                        changes.append((connection_string, cleaned))
                        found_connections.add(connection_string)
        
        return changes
    
    def _clean_datasources(self, content):
        """Clean all datasources in the content and return cleaned content and count."""
        changes_count = 0
        cleaned_content = content
        
        # Global removal of user credentials
        if self.remove_user_checkbox.isChecked():
            # Count user credentials before removing them
            user_matches = re.findall(r'user=[\'"][^\'\"]*[\'"]|user=[^\s]+', cleaned_content)
            changes_count += len(user_matches)
            
            # Remove user credentials (being very careful about spaces)
            # Handle space + user= (most common case)
            cleaned_content = re.sub(r'\s+user=[\'"][^\'\"]*[\'"]', '', cleaned_content)
            cleaned_content = re.sub(r'\s+user=[^\s]+', '', cleaned_content)
            # Handle user= + space (when user is first parameter)  
            cleaned_content = re.sub(r'user=[\'"][^\'\"]*[\'"]\s+', '', cleaned_content)
            cleaned_content = re.sub(r'user=[^\s]+\s+', '', cleaned_content)
            # Handle isolated user= (no surrounding spaces)
            cleaned_content = re.sub(r'user=[\'"][^\'\"]*[\'"]', '', cleaned_content)
            cleaned_content = re.sub(r'user=[^\s]+', '', cleaned_content)
        
        # Global removal of password credentials
        if self.remove_password_checkbox.isChecked():
            # Count password credentials before removing them
            password_matches = re.findall(r'password=[\'"][^\'\"]*[\'"]|password=[^\s]+', cleaned_content)
            changes_count += len(password_matches)
            
            # Remove password credentials (being very careful about spaces)
            # Handle space + password= (most common case)
            cleaned_content = re.sub(r'\s+password=[\'"][^\'\"]*[\'"]', '', cleaned_content)
            cleaned_content = re.sub(r'\s+password=[^\s]+', '', cleaned_content)
            # Handle password= + space (when password is first parameter)
            cleaned_content = re.sub(r'password=[\'"][^\'\"]*[\'"]\s+', '', cleaned_content)
            cleaned_content = re.sub(r'password=[^\s]+\s+', '', cleaned_content)
            # Handle isolated password= (no surrounding spaces)
            cleaned_content = re.sub(r'password=[\'"][^\'\"]*[\'"]', '', cleaned_content)
            cleaned_content = re.sub(r'password=[^\s]+', '', cleaned_content)
                
        return cleaned_content, changes_count
    
    def _has_postgres_credentials(self, datasource):
        """Check if datasource has PostgreSQL credentials."""
        # Must have dbname= (indicates PostgreSQL) and credentials we want to remove
        has_dbname = 'dbname=' in datasource
        has_user = 'user=' in datasource and self.remove_user_checkbox.isChecked()
        has_password = 'password=' in datasource and self.remove_password_checkbox.isChecked()
        
        return has_dbname and (has_user or has_password)
    
    def _clean_single_datasource(self, datasource):
        """Clean a single datasource string."""
        # This method is less important now, but kept for compatibility
        cleaned = datasource
        
        if self.remove_user_checkbox.isChecked():
            cleaned = re.sub(r'\s*user=[\'"][^\'\"]*[\'"]', '', cleaned)
            cleaned = re.sub(r'\s*user=[^\s]+', '', cleaned)
        
        if self.remove_password_checkbox.isChecked():
            cleaned = re.sub(r'\s*password=[\'"][^\'\"]*[\'"]', '', cleaned)
            cleaned = re.sub(r'\s*password=[^\s]+', '', cleaned)
        
        # Clean up any double spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def connect_signals(self):
        """Connect signals."""
        super().connect_signals()
        # No database manager operations needed for this tab
        pass
    
    # ---- Service.conf methods ----
    
    def _on_service_file_path_changed(self, text):
        """Enable/disable service buttons based on file path."""
        has_file = bool(text.strip()) and os.path.exists(text.strip())
        self.preview_service_btn.setEnabled(has_file)
        self.clean_service_btn.setEnabled(has_file)
        if not has_file:
            self.service_preview_text.clear()
    
    def detect_service_file(self):
        """Auto-detect pg_service.conf in standard locations."""
        candidates = []
        
        # PGSERVICEFILE environment variable (highest priority)
        env_path = os.environ.get('PGSERVICEFILE')
        if env_path:
            candidates.append(env_path)
        
        # Platform-specific standard locations
        if os.name == 'nt':
            # Windows
            appdata = os.environ.get('APPDATA', '')
            if appdata:
                candidates.append(os.path.join(appdata, 'postgresql', 'pg_service.conf'))
            candidates.append(os.path.join(os.path.expanduser('~'), 'pg_service.conf'))
        else:
            # Linux / macOS
            candidates.append(os.path.expanduser('~/.pg_service.conf'))
            candidates.append('/etc/pg_service.conf')
            candidates.append(os.path.expanduser('~/pg_service.conf'))
        
        for path in candidates:
            if path and os.path.isfile(path):
                self.service_file_edit.setText(path)
                self.emit_log(f"Found pg_service.conf at: {path}")
                self.preview_service_file()
                return
        
        self.emit_log("Could not auto-detect pg_service.conf in standard locations")
        self.show_warning(
            "Could not find pg_service.conf.\n\n"
            "Searched locations:\n" +
            "\n".join(f"  • {c}" for c in candidates if c) +
            "\n\nPlease use 'Browse...' to select the file manually."
        )
    
    def browse_service_file(self):
        """Browse for pg_service.conf file."""
        start_dir = ""
        if os.name == 'nt':
            appdata = os.environ.get('APPDATA', '')
            if appdata:
                pg_dir = os.path.join(appdata, 'postgresql')
                if os.path.isdir(pg_dir):
                    start_dir = pg_dir
        else:
            start_dir = os.path.expanduser('~')
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PostgreSQL Service File",
            start_dir,
            "Service Config (pg_service.conf *.conf);;All Files (*)"
        )
        
        if file_path:
            self.service_file_edit.setText(file_path)
            self.emit_log(f"Selected service file: {file_path}")
            self.preview_service_file()
    
    def _parse_service_file(self, file_path):
        """Parse a pg_service.conf file and return config + raw lines."""
        config = configparser.ConfigParser()
        config.read(file_path, encoding='utf-8')
        return config
    
    def preview_service_file(self):
        """Preview what credentials would be removed from the service file."""
        file_path = self.service_file_edit.text().strip()
        if not file_path or not os.path.exists(file_path):
            return
        
        try:
            config = self._parse_service_file(file_path)
            
            preview_lines = []
            remove_pw = self.service_remove_password_cb.isChecked()
            remove_user = self.service_remove_user_cb.isChecked()
            
            if not config.sections():
                self.service_preview_text.setPlainText("No services found in this file.")
                return
            
            for section in config.sections():
                preview_lines.append(f"[{section}]")
                for key, value in config.items(section):
                    if key == 'password' and remove_pw:
                        preview_lines.append(f"  ✗ {key} = *** (WILL BE REMOVED)")
                    elif key == 'user' and remove_user:
                        preview_lines.append(f"  ✗ {key} = {value} (WILL BE REMOVED)")
                    else:
                        preview_lines.append(f"  ✓ {key} = {value}")
                preview_lines.append("")
            
            self.service_preview_text.setPlainText("\n".join(preview_lines))
            self.emit_log(f"Previewed service file: {len(config.sections())} service(s) found")
            
        except Exception as e:
            self.service_preview_text.setPlainText(f"Error reading file: {str(e)}")
            self.emit_log(f"Error previewing service file: {str(e)}")
    
    def clean_service_file(self):
        """Clean credentials from the pg_service.conf file."""
        file_path = self.service_file_edit.text().strip()
        if not file_path or not os.path.exists(file_path):
            return
        
        remove_pw = self.service_remove_password_cb.isChecked()
        remove_user = self.service_remove_user_cb.isChecked()
        
        if not remove_pw and not remove_user:
            self.show_warning("Please select at least one credential type to remove.")
            return
        
        try:
            self.emit_progress_started()
            
            # Read the file line by line to preserve formatting and comments
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            cleaned_lines = []
            changes_count = 0
            
            for line in lines:
                stripped = line.strip()
                
                # Check if this line is a key=value we want to remove
                if stripped and not stripped.startswith('#') and not stripped.startswith('['):
                    if '=' in stripped:
                        key = stripped.split('=', 1)[0].strip().lower()
                        if key == 'password' and remove_pw:
                            changes_count += 1
                            continue  # Skip this line
                        elif key == 'user' and remove_user:
                            changes_count += 1
                            continue  # Skip this line
                
                cleaned_lines.append(line)
            
            if changes_count == 0:
                self.emit_log("No credentials found to remove from service file.")
                self.show_info("No credentials found to remove from the service file.")
                return
            
            # Generate cleaned file path
            base_name, ext = os.path.splitext(file_path)
            if not ext:
                ext = '.conf'
            cleaned_path = f"{base_name}_cleaned{ext}"
            
            # Write cleaned file
            with open(cleaned_path, 'w', encoding='utf-8') as f:
                f.writelines(cleaned_lines)
            
            success_msg = (f"Service file cleaned successfully!\n"
                          f"• Removed {changes_count} credential(s)\n"
                          f"• Original file preserved\n"
                          f"• Saved to: {os.path.basename(cleaned_path)}")
            
            self.emit_log(success_msg.replace('\n', ' '))
            self.show_info(success_msg)
            
            # Refresh preview
            self.preview_service_file()
            
        except Exception as e:
            self.show_error(f"Error cleaning service file: {str(e)}")
            self.emit_log(f"Error during service file cleaning: {str(e)}")
        finally:
            self.emit_progress_finished()