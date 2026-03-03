"""
Main dialog for KGR Toolbox.
"""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (QDockWidget, QVBoxLayout, QHBoxLayout, QWidget, QLabel, 
                                QTabWidget, QGroupBox, QProgressBar, QTextEdit, QPushButton)
from qgis.PyQt.QtGui import QFont

from .tabs import ConnectionTab, TemplatesTab, DatabasesTab, TruncateTablesTab, QGISProjectsTab, ArchiveProjectTab, CleanQGSTab
from .compat import AlignCenter, LeftDockWidgetArea


class KgrToolBoxDialog(QDockWidget):
    """Main dialog for KGR Toolbox."""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.dock_area = LeftDockWidgetArea
        
        # Connect main database manager signals
        self.db_manager.operation_finished.connect(self.on_operation_finished)
        self.db_manager.progress_updated.connect(self.on_progress_updated)
        
        self.setup_ui()
        self.connect_tab_signals()
    
    def setup_ui(self):
        """Setup the user interface."""
        self.setObjectName("KgrToolbox")
        
        # Main widget
        main_widget = QWidget()
        self.setWidget(main_widget)
        
        # Main layout
        layout = QVBoxLayout(main_widget)
        
        # Title
        title = QLabel("KGR Toolbox")
        title.setAlignment(AlignCenter)
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        title.setFont(font)
        layout.addWidget(title)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.connection_tab = ConnectionTab(self.db_manager, self)
        self.templates_tab = TemplatesTab(self.db_manager, self)
        self.databases_tab = DatabasesTab(self.db_manager, self)
        self.truncate_tab = TruncateTablesTab(self.db_manager, self)
        self.qgis_projects_tab = QGISProjectsTab(self.db_manager, self)
        self.archive_project_tab = ArchiveProjectTab(self.db_manager, self)
        self.clean_qgs_tab = CleanQGSTab(self.db_manager, self)

        # Add tabs to widget
        self.tab_widget.addTab(self.connection_tab, "Connection")
        self.tab_widget.addTab(self.templates_tab, "Templates")
        self.tab_widget.addTab(self.databases_tab, "Databases")
        self.tab_widget.addTab(self.qgis_projects_tab, "Fix QGIS Project Layers")
        self.tab_widget.addTab(self.truncate_tab, "Truncate Tables")
        self.tab_widget.addTab(self.archive_project_tab, "Archive Project")
        self.tab_widget.addTab(self.clean_qgs_tab, "Clean QGS Files")

        # Progress section
        self.setup_progress_section(layout)
    
    def setup_progress_section(self, layout):
        """Setup progress section."""
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        # Log area with clear button
        log_header_layout = QHBoxLayout()
        log_label = QLabel("Log Output:")
        log_label.setStyleSheet("font-weight: bold;")
        
        self.clear_logs_btn = QPushButton("Clear Logs")
        self.clear_logs_btn.setFixedWidth(100)
        self.clear_logs_btn.clicked.connect(self.clear_logs)
        
        log_header_layout.addWidget(log_label)
        log_header_layout.addStretch()
        log_header_layout.addWidget(self.clear_logs_btn)
        progress_layout.addLayout(log_header_layout)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(100)
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("Operation logs will appear here...")
        progress_layout.addWidget(self.log_text)
        
        layout.addWidget(progress_group)
    
    def clear_logs(self):
        """Clear the log text area."""
        self.log_text.clear()
    
    def connect_tab_signals(self):
        """Connect signals from all tabs."""
        # Connection tab signals
        self.connection_tab.connection_status_changed.connect(self.on_connection_status_changed)
        
        # Templates tab signals
        self.templates_tab.templates_refreshed.connect(self.on_templates_refreshed)
        
        # Databases tab signals
        self.databases_tab.databases_refreshed.connect(self.on_databases_refreshed)
        
        # Truncate tab signals
        self.truncate_tab.tables_truncated.connect(self.on_tables_truncated)
        
        # QGIS projects tab signals
        self.qgis_projects_tab.projects_found.connect(self.on_projects_found)
        
        # Archive project tab signals
        self.archive_project_tab.project_archived.connect(self.on_project_archived)
        
        # Clean QGS tab signals
        self.clean_qgs_tab.file_cleaned.connect(self.on_file_cleaned)


        # Connect all tab log signals to main log
        # Connect all tab log signals to main log
        tabs = [self.connection_tab, self.templates_tab, 
                self.databases_tab, self.truncate_tab, self.qgis_projects_tab, 
                self.archive_project_tab, self.clean_qgs_tab]
        
        for tab in tabs:
            tab.log_message.connect(self.log_message)
            tab.progress_started.connect(self.show_progress)
            tab.progress_finished.connect(self.hide_progress)
    
    def on_connection_status_changed(self, success, message):
        """Handle connection status change."""
        if success:
            # Auto-refresh data when connection is established
            self.refresh_all_data()
    
    def on_templates_refreshed(self, templates):
        """Handle templates refresh."""
        # Update databases tab with new templates
        self.databases_tab.refresh_templates(templates)
    
    def on_databases_refreshed(self, databases):
        """Handle databases refresh."""
        # Update templates tab with source databases
        self.templates_tab.refresh_source_databases(databases)
        # Update QGIS projects tab with databases
        self.qgis_projects_tab.refresh_qgis_databases(databases)
        # Update truncate tab with databases
        self.truncate_tab.refresh_databases(databases)
    
    def on_tables_truncated(self, database_name, table_count):
        """Handle tables truncated."""
        self.log_message(f"Successfully truncated {table_count} table(s) in database '{database_name}'")
    
    def on_projects_found(self, projects):
        """Handle QGIS projects found."""
        # Could be used for additional processing if needed
        pass
    
    def on_file_cleaned(self, cleaned_file_path):
        """Handle file cleaned signal."""
        import os
        filename = os.path.basename(cleaned_file_path)
        self.log_message(f"QGS file cleaned successfully: {filename}")

    def on_project_archived(self, archive_path):
        """Handle project archived."""
        self.log_message(f"Project archived successfully to: {archive_path}")
    
    def refresh_all_data(self):
        """Refresh all data across tabs."""
        if self.connection_tab.is_connected():
            self.databases_tab.refresh_databases()
            self.templates_tab.refresh_templates()
    
    def log_message(self, message):
        """Add message to log."""
        self.log_text.append(message)
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def show_progress(self):
        """Show progress bar."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
    
    def hide_progress(self):
        """Hide progress bar."""
        self.progress_bar.setVisible(False)
    
    def on_operation_finished(self, success, message):
        """Handle operation finished signal from database manager."""
        self.hide_progress()
        # The individual tabs handle their specific operation results
    
    def on_progress_updated(self, message):
        """Handle progress update signal from database manager."""
        self.log_message(message)
    
    def closeEvent(self, event):
        """Handle close event."""
        # Save settings from connection tab
        self.connection_tab.save_settings()
        event.accept()