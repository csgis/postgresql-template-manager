"""
Truncate Tables tab for PostgreSQL Template Manager with table truncation functionality.
"""

from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.PyQt.QtWidgets import (QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, 
                                QPushButton, QGroupBox, QLabel, QMessageBox, QDialog, 
                                QCheckBox, QTextEdit, QFrame, QTableWidget, QTableWidgetItem,
                                QHeaderView)
from qgis.PyQt.QtGui import QFont
from .base_tab import BaseTab
from ..compat import DialogAccepted, ItemIsEditable, MsgBoxOk, RichText, SelectRows, Stretch


class TruncateConfirmationDialog(QDialog):
    """
    Confirmation dialog for table truncation with strong warning.
    """
    
    def __init__(self, database_name, table_count, excluded_tables, parent=None):
        super().__init__(parent)
        self.database_name = database_name
        self.table_count = table_count
        self.excluded_tables = excluded_tables
        
        self.setWindowTitle("TRUNCATE TABLES - WARNING")
        self.setModal(True)
        self.setMinimumSize(500, 400)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout()
        

        
        # Operation information
        info_label = QLabel("You are about to TRUNCATE TABLES in the following database:")
        info_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #333; margin-top: 15px;")
        layout.addWidget(info_label)
        
        # Database details
        details_frame = QFrame()
        details_frame.setStyleSheet("""
            QFrame {
                border-radius: 5px;
                padding: 10px;
                margin: 10px 0;
            }
        """)
        details_layout = QVBoxLayout(details_frame)
        
        db_name_label = QLabel(f"Database: {self.database_name}")
        db_name_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #4a148c;")
        details_layout.addWidget(db_name_label)
        
        tables_label = QLabel(f"Tables to truncate: {self.table_count}")
        tables_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #6a1b9a;")
        details_layout.addWidget(tables_label)
        
        if self.excluded_tables:
            excluded_label = QLabel(f"Excluded tables: {', '.join(self.excluded_tables)}")
            excluded_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #388e3c;")
            details_layout.addWidget(excluded_label)
        
        layout.addWidget(details_frame)
        
        # Warning text
        warning_text = QTextEdit()
        warning_text.setReadOnly(True)
        warning_text.setMaximumHeight(120)
        warning_text.setStyleSheet("background-color: #ffebee;")
        warning_text.setPlainText(
            "WARNING: This action will DELETE ALL DATA from the selected tables!\n\n"
            "• ALL rows in the affected tables will be permanently removed\n"
            "• Table structure (columns, indexes, constraints) will remain intact\n"
            "• This operation cannot be undone\n"
            "• Applications using this data may stop working properly"
        )
        layout.addWidget(warning_text)
        
        # Button area
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 20, 0, 0)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.cancel_button.clicked.connect(self.reject)
        
        self.truncate_button = QPushButton("TRUNCATE TABLES")
        self.truncate_button.setStyleSheet("""
            QPushButton {
                background-color: #ff0000;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
        """)
        self.truncate_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()
        button_layout.addWidget(self.truncate_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)


class TruncateTablesTab(BaseTab):
    """Tab for truncating tables in selected database."""
    
    # Signals
    tables_truncated = pyqtSignal(str, int)  # database_name, table_count
    
    def __init__(self, db_manager, parent=None):
        super().__init__(db_manager, parent)
        self.current_databases = []
        self.current_schemas = []
        self.current_tables = []
    
    def setup_ui(self):
        """Setup the truncate tables tab UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title and help button section
        title_layout = QHBoxLayout()
        title_label = QLabel("Truncate Tables")
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
        
        # Database and schema selection section
        selection_group = QGroupBox("Database and Schema Selection")
        selection_layout = QFormLayout(selection_group)
        
        self.database_combo = QComboBox()
        self.database_combo.currentTextChanged.connect(self.on_database_changed)
        selection_layout.addRow("Database:", self.database_combo)
        
        self.schema_combo = QComboBox()
        self.schema_combo.currentTextChanged.connect(self.on_schema_changed)
        self.schema_combo.setEnabled(False)
        selection_layout.addRow("Schema:", self.schema_combo)
        
        # Exclusion options
        self.exclude_qgis_projects_cb = QCheckBox("Exclude 'qgis_projects' table from truncation")
        self.exclude_qgis_projects_cb.setChecked(True)
        self.exclude_qgis_projects_cb.setStyleSheet("font-weight: bold; color: #388e3c;")
        self.exclude_qgis_projects_cb.stateChanged.connect(self.update_tables_display)
        selection_layout.addRow("", self.exclude_qgis_projects_cb)
        
        layout.addWidget(selection_group)
        
        # Table preview section
        preview_group = QGroupBox("Tables to be Truncated")
        preview_layout = QVBoxLayout(preview_group)
        
        # Refresh button
        refresh_layout = QHBoxLayout()
        self.refresh_tables_btn = QPushButton("Refresh Tables")
        self.refresh_tables_btn.clicked.connect(self.refresh_tables)
        refresh_layout.addWidget(self.refresh_tables_btn)
        
        self.refresh_schemas_btn = QPushButton("Refresh Schemas")
        self.refresh_schemas_btn.clicked.connect(self.refresh_schemas)
        refresh_layout.addWidget(self.refresh_schemas_btn)
        
        refresh_layout.addStretch()
        preview_layout.addLayout(refresh_layout)
        
        # Tables table
        self.tables_table = QTableWidget()
        self.tables_table.setColumnCount(2)
        self.tables_table.setHorizontalHeaderLabels(["Table Name", "Status"])
        self.tables_table.setSelectionBehavior(SelectRows)
        self.tables_table.horizontalHeader().setStretchLastSection(True)
        self.tables_table.horizontalHeader().setSectionResizeMode(0, Stretch)
        self.tables_table.setSortingEnabled(True)
        self.tables_table.setMaximumHeight(200)
        preview_layout.addWidget(self.tables_table)
        
        layout.addWidget(preview_group)
        
        # Truncate section
        truncate_group = QGroupBox("Truncate Operation")
        truncate_layout = QVBoxLayout(truncate_group)
                
        self.truncate_btn = QPushButton("Truncate Tables")
        self.truncate_btn.setStyleSheet("""
            QPushButton {
                background-color: #e50000;
                color: white;
                font-weight: bold;
                padding: 12px 24px;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #ff0000;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.truncate_btn.clicked.connect(self.truncate_tables)
        self.truncate_btn.setEnabled(False)
        truncate_layout.addWidget(self.truncate_btn)
        
        layout.addWidget(truncate_group)
        
        # Status section
        self.status_label = QLabel("Select a database and schema to view tables")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.status_label)

    def _show_help_popup(self):
        """Show help information in a popup dialog."""
        help_text = (
            "<h3>Truncate Tables</h3>"
            "<p>Remove all data from tables in a selected database schema while preserving table structure.</p>"
            
            "<h4>What happens:</h4>"
            "<ul>"
            "<li><b>Data removal:</b> All rows are permanently deleted from selected tables</li>"
            "<li><b>Structure preserved:</b> Table schema, columns, and indexes remain intact</li>"
            "<li><b>Cannot be undone:</b> No way to recover data after truncation</li>"
            "</ul>"
            
            "<h4>How to use:</h4>"
            "<ol>"
            "<li>Select target database from dropdown</li>"
            "<li>Choose schema containing tables to truncate</li>"
            "<li>Review which tables will be affected</li>"
            "<li>Optionally exclude 'qgis_projects' table</li>"
            "<li>Confirm operation and execute</li>"
            "</ol>"
            
            "<h4>Important warnings:</h4>"
            "<ul>"
            "<li><b>Irreversible:</b> Once truncated, data cannot be recovered</li>"
            "<li><b>Applications:</b> May break applications that depend on the data</li>"
            "<li><b>Schema scope:</b> Only affects tables in the selected schema</li>"
            "<li><b>Backup recommended:</b> Create backups before truncating important data</li>"
            "</ul>"
        )
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Help - Truncate Tables")
        msg.setTextFormat(RichText)  # Rich text format
        msg.setText(help_text)
        msg.setStandardButtons(MsgBoxOk)
        
        # Make dialog appropriately sized
        msg.resize(500, 400)
        msg.exec()

    def connect_signals(self):
        """Connect signals."""
        super().connect_signals()
        self.db_manager.operation_finished.connect(self.on_operation_finished)
    
    def on_database_changed(self):
        """Handle database selection change."""
        self.current_schemas = []
        self.current_tables = []
        self.schema_combo.clear()
        self.schema_combo.setEnabled(False)
        self.tables_table.setRowCount(0)
        
        database_name = self.database_combo.currentText()
        if database_name:
            self.status_label.setText(f"Selected database: {database_name}")
            self.truncate_btn.setEnabled(False)
            self.refresh_schemas()
        else:
            self.status_label.setText("Select a database and schema to view tables")
            self.truncate_btn.setEnabled(False)
    
    def on_schema_changed(self):
        """Handle schema selection change."""
        self.current_tables = []
        self.tables_table.setRowCount(0)
        
        schema_name = self.schema_combo.currentText()
        if schema_name:
            self.status_label.setText(f"Selected schema: {schema_name}")
            self.truncate_btn.setEnabled(False)
            self.refresh_tables()
        else:
            self.status_label.setText("Select a schema to view tables")
            self.truncate_btn.setEnabled(False)
    
    def refresh_databases(self, databases):
        """Refresh available databases."""
        current_selection = self.database_combo.currentText()
        self.database_combo.clear()
        
        # Filter out system databases
        available_databases = []
        for db_name in databases:
            if not self.db_manager.is_system_database(db_name):
                available_databases.append(db_name)
        
        self.current_databases = available_databases
        self.database_combo.addItems(available_databases)
        
        # Restore previous selection if it still exists
        if current_selection in available_databases:
            self.database_combo.setCurrentText(current_selection)
    
    def refresh_schemas(self):
        """Refresh schemas for selected database."""
        database_name = self.database_combo.currentText()
        if not database_name:
            return
        
        if not self.check_connection():
            return
        
        try:
            # Get schemas from database manager
            if hasattr(self.db_manager, 'get_database_schemas'):
                schemas = self.db_manager.get_database_schemas(database_name)
            else:
                # Fallback - common PostgreSQL schemas
                schemas = ['public']
                self.emit_log("⚠️ Warning: get_database_schemas method not found in database manager, using 'public' schema")
            
            self.current_schemas = schemas
            self.schema_combo.clear()
            self.schema_combo.addItems(schemas)
            self.schema_combo.setEnabled(True)
            
            # Auto-select 'public' schema if available
            if 'public' in schemas:
                self.schema_combo.setCurrentText('public')
            
            self.emit_log(f"Refreshed schemas for database '{database_name}': {len(schemas)} schemas found")
            
        except Exception as e:
            self.emit_log(f"Error refreshing schemas: {str(e)}")
    
    def refresh_tables(self):
        """Refresh tables for selected database and schema."""
        database_name = self.database_combo.currentText()
        schema_name = self.schema_combo.currentText()
        
        if not database_name or not schema_name:
            self.status_label.setText("Please select both database and schema")
            return
        
        if not self.check_connection():
            self.status_label.setText("Connection check failed")
            return
        
        try:
            # Clear current tables
            self.current_tables = []
            self.tables_table.setRowCount(0)
            self.truncate_btn.setEnabled(False)
            
            # Get tables from database manager
            tables = []
            if hasattr(self.db_manager, 'get_schema_tables'):
                tables = self.db_manager.get_schema_tables(database_name, schema_name)
            elif hasattr(self.db_manager, 'get_database_tables'):
                # Fallback to old method
                tables = self.db_manager.get_database_tables(database_name)
                self.emit_log("⚠️ Warning: Using fallback method - results may not be schema-specific")
            else:
                self.emit_log("❌ Error: No method found to get tables from database manager")
                self.status_label.setText("Database manager method not found")
                return
            
            # Handle the case where tables is None or empty
            if tables is None:
                tables = []
                self.emit_log("⚠️ Warning: get_schema_tables returned None")
            elif not isinstance(tables, list):
                self.emit_log(f"⚠️ Warning: get_schema_tables returned unexpected type: {type(tables)}")
                tables = []
            
            # Filter out any None or empty table names
            valid_tables = []
            for table in tables:
                if table and isinstance(table, str) and table.strip():
                    valid_tables.append(table.strip())
            
            self.current_tables = valid_tables
            self.update_tables_display()
            
            # Update status
            if valid_tables:
                self.emit_log(f"✅ Found {len(valid_tables)} table(s) in schema '{schema_name}' of database '{database_name}'")
            else:
                self.emit_log(f"ℹ️ No tables found in schema '{schema_name}' of database '{database_name}'")
                self.status_label.setText(f"No tables found in schema '{schema_name}'")
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.emit_log(f"❌ Error refreshing tables: {str(e)}")
            self.emit_log(f"Full traceback: {error_details}")
            self.status_label.setText(f"Error: {str(e)}")
            
            # Reset state on error
            self.current_tables = []
            self.tables_table.setRowCount(0)
            self.truncate_btn.setEnabled(False)

    def update_tables_display(self):
        """Update the tables display with current tables and exclusions."""
        from qgis.PyQt.QtGui import QColor, QFont
        from qgis.PyQt.QtCore import Qt
        
        self.tables_table.setRowCount(0)
        
        exclude_qgis_projects = self.exclude_qgis_projects_cb.isChecked()
        tables_to_truncate = 0
        
        for row, table_name in enumerate(self.current_tables):
            self.tables_table.insertRow(row)
            
            # Table name
            name_item = QTableWidgetItem(table_name)
            name_item.setFlags(name_item.flags() & ~ItemIsEditable)
            self.tables_table.setItem(row, 0, name_item)
            
            # Status
            if table_name == 'qgis_projects' and exclude_qgis_projects:
                status_item = QTableWidgetItem("EXCLUDED")
                # Set green color for excluded items
                status_item.setForeground(QColor("#388e3c"))  # Green color
                # Make it bold
                font = QFont()
                font.setBold(True)
                status_item.setFont(font)
            else:
                status_item = QTableWidgetItem("WILL BE TRUNCATED")
                # Set red color for items to be truncated
                status_item.setForeground(QColor("#f44336"))  # Red color
                # Make it bold
                font = QFont()
                font.setBold(True)
                status_item.setFont(font)
                tables_to_truncate += 1
            
            status_item.setFlags(status_item.flags() & ~ItemIsEditable)
            self.tables_table.setItem(row, 1, status_item)
        
        # Update truncate button state
        self.truncate_btn.setEnabled(tables_to_truncate > 0)
        
        # Update status
        if tables_to_truncate > 0:
            self.status_label.setText(f"Ready to truncate {tables_to_truncate} table(s)")
        else:
            self.status_label.setText("No tables selected for truncation")    

    def truncate_tables(self):
        """Truncate tables with confirmation."""
        database_name = self.database_combo.currentText()
        schema_name = self.schema_combo.currentText()
        
        if not database_name:
            self.show_warning("Please select a database.")
            return
        
        if not schema_name:
            self.show_warning("Please select a schema.")
            return
        
        if not self.check_connection():
            return
        
        # Calculate tables to truncate
        exclude_qgis_projects = self.exclude_qgis_projects_cb.isChecked()
        excluded_tables = []
        tables_to_truncate = []
        
        for table_name in self.current_tables:
            if table_name == 'qgis_projects' and exclude_qgis_projects:
                excluded_tables.append(table_name)
            else:
                tables_to_truncate.append(table_name)
        
        if not tables_to_truncate:
            self.show_warning("No tables selected for truncation.")
            return
        
        # Show confirmation dialog
        dialog = TruncateConfirmationDialog(
            f"{database_name}.{schema_name}", 
            len(tables_to_truncate), 
            excluded_tables,
            self
        )
        result = dialog.exec()
        
        if result == DialogAccepted:
            # User confirmed - execute truncation
            self.emit_progress_started()
            self.emit_log(f"🗑️ TRUNCATING {len(tables_to_truncate)} table(s) in schema '{schema_name}' of database '{database_name}'")
            
            # Execute truncation via database manager
            if hasattr(self.db_manager, 'truncate_schema_tables'):
                self.db_manager.truncate_schema_tables(database_name, schema_name, tables_to_truncate)
            elif hasattr(self.db_manager, 'truncate_database_tables'):
                # Fallback: pass schema-qualified table names
                qualified_tables = [f"{schema_name}.{table}" for table in tables_to_truncate]
                self.db_manager.truncate_database_tables(database_name, qualified_tables)
            else:
                # Fallback error
                self.emit_log("❌ Error: Neither truncate_schema_tables nor truncate_database_tables method found in database manager")
                self.emit_progress_finished()
        else:
            self.emit_log("Table truncation cancelled by user.")
    
    def on_operation_finished(self, success, message):
        """Handle operation finished signal."""
        if "truncate" in message.lower():
            self.emit_progress_finished()
            
            if success:
                self.emit_log(f"✅ {message}")
                # Refresh tables after truncation
                self.refresh_tables()
            else:
                self.emit_log(f"❌ {message}")