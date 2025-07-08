from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import IntegrityError
from app.models.show_metadata import db, ArchiveItem, ArchiveFile, BackupJob
from app.api.archive_api import ArchiveAPI
from datetime import datetime
import json
import os

backup_bp = Blueprint('backup', __name__)

@backup_bp.route('/metadata/<identifier>', methods=['POST'])
def backup_metadata(identifier):
    """Backup metadata for a specific show identifier"""
    try:
        # Initialize Archive API
        archive_api = ArchiveAPI()
        
        # Get metadata from Archive.org
        metadata_response = archive_api.get_metadata(identifier)
        if not metadata_response:
            return jsonify({'error': 'Failed to fetch metadata from Archive.org'}), 404
        
        # Check if metadata already exists
        existing_metadata = ArchiveItem.query.filter_by(identifier=identifier).first()
        
        if existing_metadata:
            # Update existing metadata
            update_metadata_from_response(existing_metadata, metadata_response)
            db.session.commit()
            return jsonify({
                'message': 'Metadata updated successfully',
                'identifier': identifier,
                'action': 'updated'
            })
        else:
            # Create new metadata
            show_metadata = create_metadata_from_response(metadata_response)
            db.session.add(show_metadata)
            db.session.commit()
            
            return jsonify({
                'message': 'Metadata backed up successfully',
                'identifier': identifier,
                'action': 'created'
            })
    
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'error': 'Database integrity error'}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@backup_bp.route('/files/<identifier>', methods=['POST'])
def backup_files(identifier):
    """Backup files for a specific show identifier"""
    try:
        # Get archive item
        archive_item = ArchiveItem.query.filter_by(identifier=identifier).first()
        if not archive_item:
            return jsonify({'error': 'Archive item not found. Please backup metadata first.'}), 404
        
        # Initialize Archive API
        archive_api = ArchiveAPI()
        
        # Get file list from metadata
        metadata_response = archive_api.get_metadata(identifier)
        if not metadata_response or 'files' not in metadata_response:
            return jsonify({'error': 'Failed to fetch file list from Archive.org'}), 404
        
        files = metadata_response['files']
        downloaded_files = []
        failed_files = []
        
        # Filter for audio files (mp3, flac, etc.)
        audio_extensions = ['.mp3', '.flac', '.wav', '.ogg', '.shn']
        audio_files = [f for f in files if any(f.get('name', '').lower().endswith(ext) for ext in audio_extensions)]
        
        for file_info in audio_files:
            filename = file_info.get('name')
            if not filename:
                continue
            
            # Check if file already downloaded
            existing_file = ArchiveFile.query.filter_by(
                archive_item_id=archive_item.id,
                name=filename
            ).first()
            
            if existing_file and existing_file.is_downloaded:
                continue
            
            # Download file
            local_path = archive_api.download_file(identifier, filename)
            
            if local_path:
                # Create or update file record
                if existing_file:
                    existing_file.local_path = local_path
                    existing_file.is_downloaded = True
                    existing_file.download_date = datetime.utcnow()
                else:
                    archive_file = create_file_from_info(file_info, archive_item.id)
                    archive_file.local_path = local_path
                    archive_file.is_downloaded = True
                    archive_file.download_date = datetime.utcnow()
                    db.session.add(archive_file)
                
                downloaded_files.append(filename)
            else:
                failed_files.append(filename)
        
        # Update archive item backup status
        archive_item.is_backed_up = True
        archive_item.backup_date = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'File backup completed',
            'identifier': identifier,
            'downloaded_files': downloaded_files,
            'failed_files': failed_files,
            'total_downloaded': len(downloaded_files),
            'total_failed': len(failed_files)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@backup_bp.route('/full/<identifier>', methods=['POST'])
def backup_full(identifier):
    """Backup both metadata and files for a specific show identifier"""
    try:
        # First backup metadata
        metadata_result = backup_metadata(identifier)
        if metadata_result[1] not in [200, 201]:
            return metadata_result
        
        # Then backup files
        files_result = backup_files(identifier)
        return files_result
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@backup_bp.route('/status/<identifier>', methods=['GET'])
def backup_status(identifier):
    """Get backup status for a specific show identifier"""
    try:
        archive_item = ArchiveItem.query.filter_by(identifier=identifier).first()
        if not archive_item:
            return jsonify({
                'identifier': identifier,
                'metadata_backed_up': False,
                'files_backed_up': False,
                'backup_date': None
            })
        
        # Count downloaded files
        total_files = len(archive_item.files)
        downloaded_files = len([f for f in archive_item.files if f.is_downloaded])
        
        return jsonify({
            'identifier': identifier,
            'metadata_backed_up': True,
            'files_backed_up': archive_item.is_backed_up,
            'backup_date': archive_item.backup_date.isoformat() if archive_item.backup_date else None,
            'total_files': total_files,
            'downloaded_files': downloaded_files,
            'archive_item': archive_item.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@backup_bp.route('/list', methods=['GET'])
def list_backups():
    """List all backed up shows"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        pagination = ArchiveItem.query.order_by(ArchiveItem.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        backups = []
        for item in pagination.items:
            downloaded_files = len([f for f in item.files if f.is_downloaded])
            backups.append({
                'identifier': item.identifier,
                'title': item.title,
                'date': item.date,
                'venue': item.venue,
                'creator': item.creator,
                'is_backed_up': item.is_backed_up,
                'backup_date': item.backup_date.isoformat() if item.backup_date else None,
                'total_files': len(item.files),
                'downloaded_files': downloaded_files
            })
        
        return jsonify({
            'backups': backups,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@backup_bp.route('/jobs', methods=['GET'])
def list_backup_jobs():
    """List backup jobs"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        pagination = BackupJob.query.order_by(BackupJob.started_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        jobs = [job.to_dict() for job in pagination.items]
        
        return jsonify({
            'jobs': jobs,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def create_metadata_from_response(api_response):
    """Create ArchiveItem object from Archive.org response"""
    identifier = api_response.get('metadata', {}).get('identifier', '')
    
    archive_item = ArchiveItem(identifier=identifier)
    
    # Set top-level API fields
    archive_item.created = api_response.get('created')
    archive_item.d1 = api_response.get('d1')
    archive_item.d2 = api_response.get('d2')
    archive_item.dir = api_response.get('dir')
    archive_item.files_count = api_response.get('files_count')
    archive_item.item_last_updated = api_response.get('item_last_updated')
    archive_item.item_size = api_response.get('item_size')
    archive_item.server = api_response.get('server')
    archive_item.uniq = api_response.get('uniq')
    archive_item.workable_servers_list = api_response.get('workable_servers', [])
    
    # Store complete metadata as JSON
    archive_item.metadata_dict = api_response.get('metadata', {})
    
    # Add files
    files = api_response.get('files', [])
    for file_info in files:
        archive_file = create_file_from_info(file_info, None)  # Will be set when archive_item is saved
        archive_item.files.append(archive_file)
    
    return archive_item

def update_metadata_from_response(archive_item, api_response):
    """Update existing ArchiveItem object from Archive.org response"""
    
    # Update top-level API fields
    archive_item.created = api_response.get('created')
    archive_item.d1 = api_response.get('d1')
    archive_item.d2 = api_response.get('d2')
    archive_item.dir = api_response.get('dir')
    archive_item.files_count = api_response.get('files_count')
    archive_item.item_last_updated = api_response.get('item_last_updated')
    archive_item.item_size = api_response.get('item_size')
    archive_item.server = api_response.get('server')
    archive_item.uniq = api_response.get('uniq')
    archive_item.workable_servers_list = api_response.get('workable_servers', [])
    
    # Update complete metadata as JSON
    archive_item.metadata_dict = api_response.get('metadata', {})
    archive_item.updated_at = datetime.utcnow()

def create_file_from_info(file_info, archive_item_id):
    """Create ArchiveFile object from file info"""
    archive_file = ArchiveFile()
    archive_file.archive_item_id = archive_item_id
    
    # Core Archive.org fields
    archive_file.name = file_info.get('name')
    archive_file.source = file_info.get('source')
    archive_file.format = file_info.get('format')
    archive_file.mtime = file_info.get('mtime')
    archive_file.size = file_info.get('size')
    archive_file.md5 = file_info.get('md5')
    archive_file.crc32 = file_info.get('crc32')
    archive_file.sha1 = file_info.get('sha1')
    
    # Optional fields
    archive_file.length = file_info.get('length')
    archive_file.height = file_info.get('height')
    archive_file.width = file_info.get('width')
    archive_file.track = file_info.get('track')
    archive_file.album = file_info.get('album')
    archive_file.artist = file_info.get('artist')
    archive_file.title = file_info.get('title')
    archive_file.bitrate = file_info.get('bitrate')
    archive_file.creator = file_info.get('creator')
    archive_file.private = file_info.get('private', False)
    archive_file.rotation = file_info.get('rotation')
    archive_file.summation = file_info.get('summation')
    
    return archive_file 