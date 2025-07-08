# Archive Backup System

A Python/Flask-based backup system for Archive.org content, designed to create local backups of shows, metadata, and audio files from Archive.org when the main service is unavailable.

## Features

- **Full API Compatibility**: Python implementation that mirrors the Swift ArchiveAPI.swift functionality
- **Metadata Backup**: Store show metadata including title, venue, date, creator, ratings, etc.
- **File Backup**: Download and store audio files (MP3, FLAC, SHN, etc.)
- **Search Integration**: Search both local backups and Archive.org
- **Web Interface**: Modern Bootstrap-based web UI for management
- **REST API**: Complete API endpoints for programmatic access
- **Database Storage**: SQLite/PostgreSQL support for metadata
- **Background Jobs**: Celery integration for long-running backup tasks

## Quick Start

### Prerequisites

- Python 3.8+
- Flask 2.0+
- SQLite or PostgreSQL
- Redis (optional, for background tasks)

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd archive_backup
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize the database**:
   ```bash
   python app.py deploy
   ```

4. **Run the application**:
   ```bash
   python app.py
   ```

5. **Access the web interface**:
   Open http://localhost:5000 in your browser

## API Endpoints

### Backup Operations

- `POST /api/backup/metadata/<identifier>` - Backup metadata for a show
- `POST /api/backup/files/<identifier>` - Backup files for a show
- `POST /api/backup/full/<identifier>` - Full backup (metadata + files)
- `GET /api/backup/status/<identifier>` - Check backup status
- `GET /api/backup/list` - List all backups

### Search Operations

- `GET /api/search/archive` - Search Archive.org directly
- `GET /api/search/local` - Search local backups
- `GET /api/search/hybrid` - Search both local and Archive.org
- `GET /api/search/date_range` - Search by date range
- `GET /api/search/year_total` - Get year totals

### Example Usage

#### Backup a Show

```bash
# Backup metadata only
curl -X POST http://localhost:5000/api/backup/metadata/gd1977-05-08.sbd.hicks.4982.sbeok.shnf

# Full backup with files
curl -X POST http://localhost:5000/api/backup/full/gd1977-05-08.sbd.hicks.4982.sbeok.shnf

# Check status
curl http://localhost:5000/api/backup/status/gd1977-05-08.sbd.hicks.4982.sbeok.shnf
```

#### Search Examples

```bash
# Search Archive.org
curl "http://localhost:5000/api/search/archive?search_term=Dark+Star&venue=Fillmore"

# Search local backups
curl "http://localhost:5000/api/search/local?search_term=Dark+Star&min_rating=4.0"

# Search by date range
curl "http://localhost:5000/api/search/date_range?year=1977&month=5&collection=GratefulDead"
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL=sqlite:///archive_backup.db
# DATABASE_URL=postgresql://user:pass@localhost/archive_backup

# Security
SECRET_KEY=your-secret-key-here

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Flask environment
FLASK_CONFIG=development
```

### Collection Configuration

The system supports different Archive.org collections:

- **GratefulDead** (default)
- **etree** (creator-based)
- **PhilLeshAndFriends** (creator-based)
- **BobWeir** (creator-based)

## Database Schema

### ShowMetadata Table

- `identifier` - Archive.org identifier (unique)
- `title` - Show title
- `date` - Show date
- `venue` - Performance venue
- `creator` - Content creator
- `collection` - Archive.org collection(s)
- `source` - Source information
- `avg_rating` - Average rating
- `is_backed_up` - Full backup status
- `created_at` - Backup creation date

### ShowFile Table

- `name` - Filename
- `format` - File format (MP3, FLAC, etc.)
- `size` - File size
- `local_path` - Local storage path
- `is_downloaded` - Download status
- `md5` - MD5 hash

## Web Interface

The web interface provides:

- **Dashboard**: Overview of backup status and statistics
- **Browse**: Browse backed up shows with filtering
- **Search**: Search Archive.org and local backups
- **Backup Manager**: Manage backup operations
- **Statistics**: Detailed backup statistics

## Background Tasks (Optional)

For long-running backup operations, configure Celery:

1. **Install Redis**:
   ```bash
   # macOS
   brew install redis
   # Ubuntu
   sudo apt-get install redis-server
   ```

2. **Start Celery worker**:
   ```bash
   celery -A app.celery worker --loglevel=info
   ```

## File Storage

Files are stored in the `storage/` directory:

```
storage/
├── metadata/          # JSON metadata files
└── files/            # Downloaded audio files
    └── <identifier>/ # Show-specific directories
```

## Archive.org API Mirroring

This project mirrors the Swift ArchiveAPI.swift functionality:

| Swift Method | Python Method | Description |
|-------------|---------------|-------------|
| `metadataURL()` | `metadata_url()` | Build metadata URLs |
| `downloadURL()` | `download_url()` | Build download URLs |
| `dateRangeURL()` | `date_range_url()` | Build date range search URLs |
| `searchTermURL()` | `search_term_url()` | Build search URLs |
| `getIARequestMetadata()` | `get_metadata()` | Get show metadata |
| `getIADownload()` | `download_file()` | Download files |

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Database Migrations

```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### Adding New Collections

To add support for new Archive.org collections:

1. Update `CREATOR_BASED_COLLECTIONS` in `config/config.py`
2. Test search functionality with the new collection
3. Update documentation

## Production Deployment

### Using Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Using Docker

```bash
docker build -t archive-backup .
docker run -p 5000:5000 archive-backup
```

### Environment Setup

- Use PostgreSQL for production
- Configure Redis for background tasks
- Set up proper logging
- Use environment variables for sensitive data

## Troubleshooting

### Common Issues

1. **Database connection errors**:
   - Check `DATABASE_URL` in `.env`
   - Ensure database is running

2. **Archive.org API timeouts**:
   - Increase timeout in `config/config.py`
   - Check internet connection

3. **File download failures**:
   - Check storage permissions
   - Verify disk space

### Logs

Check application logs for detailed error information:

```bash
tail -f logs/archive_backup.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Archive.org](https://archive.org) for providing the data
- [Flask](https://flask.palletsprojects.com/) web framework
- [Bootstrap](https://getbootstrap.com/) for the UI
- Original Swift implementation inspiration

## Support

For issues and questions:

- Create an issue on GitHub
- Check the troubleshooting section
- Review the API documentation
