# <img src="icon.png" height="25"> KGR Toolbox

A QGIS plugin for managing PostgreSQL database templates and creating portable project archives.

The plugin will help to stay organized when working with multiple database projects and various database connections. Furthermore, it will support the work with PostgreSQL databases in terms of creating, copying and sharing data.

## Features

### PostgreSQL Template Management
- **Create Templates**: Generate database templates from existing PostgreSQL databases without data
- **Deploy Templates**: Create new databases from existing templates
- **Schema Preservation**: Maintain all database structure, constraints, and relationships

### Portable Project Archives
- **PostgreSQL to Geopackage**: Convert all PostgreSQL layers to a single portable geopackage
- **Complete Project Export**: Copy all project files including DCIM folders and media and updates source references

### QGIS Projects
- **Fix QGIS Project Layers**: Search and update database connection configuration in layers.
- **Service Mode**: Switch layers from explicit credentials (host/user/password) to a `pg_service.conf` service name — or the other way around
- **Layer Extent Reset**: Recalculate extents for all PostgreSQL layers in the current project after a migration
- **Clean QGS Files**: Remove username and password in case they have been saved within the project file
- **Clean pg_service.conf**: Remove credentials from PostgreSQL service configuration files with auto-detection of standard file locations

### PostgreSQL Database
- **Truncate Tables**: Truncate tables, to have a fresh start with duplicated databases


## Installation

### From QGIS Plugin Repository
1. Open QGIS
2. Go to `Plugins` → `Manage and Install Plugins`
3. Search for "KGR Toolbox"
4. Click `Install Plugin`

### Manual Installation
1. Download the latest release from [GitHub Releases] (https://github.com/csgis/postgresql-template-manager/releases)
2. Go to `Plugins` → `Manage and Install Plugins`
3. Upload the zip

## Usage
**For specific help to all actions click the help button in the upper right corner of each of the follwing tabs.**

#### Connection
##### Most of the actions need a database connection. Use a highly privileged user to work with templates and databases.
1. Open the KGR Toolbox plugin
2. Go to the **Database Connection** tab
3. Enter your PostgreSQL connection details
4. Click **Test Connection**

As long as "Connected" appears below the "Test connection" button, you can work in the other tabs (if a database connection is necessary).

#### Templates
When the database connection is enabled, you can choose a source (Source Database) from which you want to build a template in order to easily create different projects with the same data model in the future. The source must already be available within the established connection (choose from dropdown). Enter

#### Databases
When the database connection is enabled, you can create a new database in PostgreSQL based on an already existing database within this connection from a template (created in the tab before) or a regular database.

#### Fix QGIS Project Layers
In case your new database was copied from another destination or you want to change the user and password for your new database, you can change all connection parameters of the layers in the chosen project to the actual connection. Leave the fields empty that should stay the same.

**Service Mode:** Enter a service name (e.g. `production`) to switch all layers from explicit credentials to `service='production'`. This references your `pg_service.conf` file for credentials. The explicit connection fields (host, port, user, password, dbname) will be removed from the layer datasources. When the service name field is filled, the explicit fields are disabled.

**Explicit Mode:** Leave the service name empty and fill in the individual fields as before. If a layer currently uses a `service=` connection, it will be replaced with explicit parameters.

**Layer Extent Reset:** After migrating layers or fixing connection parameters, click "Reset PostgreSQL Layer Extents" to recalculate extents and refresh all PostgreSQL layers in the current project.

#### Truncate Tables
In case you created a new database from an existing database including all data, you can remove the old data from your new database. The structure of the database will be preserved, but the data will be permanently deleted in the chosen database.

#### Archive Project
In order to share your project with other people you can create a portable version of the database. All relevant files will be copied to a folder while all credentials and connection information to the original database will be removed. The complete folder can be shared and the recipient of the project can open the project in QGIS without any database connection, but still in the original structure of the project.

#### Clean QGS Files
To remove only the credentials, but to keep the database connection, you can choose any .qgs or .qgz-file from your computer. When opening the newly created .qgs-file you will be asked to enter the credentials manually.

**pg_service.conf Cleaning:** In the same tab you can also clean credentials from PostgreSQL service configuration files. Use "Auto-detect" to find your `pg_service.conf` in standard locations (`PGSERVICEFILE` environment variable, `%APPDATA%\postgresql\` on Windows, `~/.pg_service.conf` on Linux/macOS) or browse manually. Choose whether to remove passwords, users, or both, then preview and clean.




## Requirements

- QGIS 3.34 or higher (compatible with both QGIS 3.x and 4.x)
- PostgreSQL database with appropriate permissions
- Python 3.6+ (included with QGIS)

## Compatibility

The plugin is compatible with both Qt5 (QGIS 3.x) and Qt6 (QGIS 4.x) through a central compatibility layer (`compat.py`). No separate versions are needed.


## Troubleshooting

### Common Issues

**Connection Failed**
- Verify PostgreSQL server is running
- Check host, port, and credentials
- Ensure user has appropriate permissions

**Template Creation Failed**
- Ensure user has CREATEDB privileges
- Check database name doesn't already exist
- Verify sufficient disk space

**Archive Export Failed**
- Check write permissions in output folder
- Ensure sufficient disk space
- Verify QGIS project is saved

### Getting Help
- Check the [Issues](https://github.com/csgis/kgr_toolbox/issues) page
- Create a new issue with detailed description
- Include QGIS version, PostgreSQL version, and error messages

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](https://opensource.org/license/mit) file for details.
