from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

db = SQLAlchemy()

class ArchiveItem(db.Model):
    """Complete Archive.org item model - direct replication of API response"""
    __tablename__ = 'archive_items'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    
    # Top-level API response fields
    identifier = Column(String(255), unique=True, nullable=False, index=True)
    created = Column(Integer)  # Unix timestamp
    d1 = Column(String(255))  # Primary data server
    d2 = Column(String(255))  # Secondary data server
    dir = Column(String(500))  # Item directory path
    files_count = Column(Integer)  # Number of files
    item_last_updated = Column(Integer)  # Unix timestamp
    item_size = Column(BigInteger)  # Total size in bytes
    server = Column(String(255))  # Server hosting the item
    uniq = Column(BigInteger)  # Unique identifier
    workable_servers = Column(Text)  # JSON array of available servers
    
    # Full metadata as JSON (direct replication)
    item_metadata = Column(Text)  # Complete metadata JSON
    
    # Backup specific fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_backed_up = Column(Boolean, default=False)
    backup_date = Column(DateTime)
    
    # Relationships
    files = relationship("ArchiveFile", back_populates="archive_item", cascade="all, delete-orphan")
    
    def __init__(self, identifier: str, **kwargs):
        self.identifier = identifier
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @property
    def metadata_dict(self) -> Optional[Dict[str, Any]]:
        """Get metadata as dictionary"""
        if self.item_metadata:
            try:
                return json.loads(self.item_metadata)
            except json.JSONDecodeError:
                return {}
        return {}
    
    @metadata_dict.setter
    def metadata_dict(self, value: Optional[Dict[str, Any]]):
        """Set metadata from dictionary"""
        if value:
            self.item_metadata = json.dumps(value)
        else:
            self.item_metadata = None
    
    @property
    def workable_servers_list(self) -> Optional[List[str]]:
        """Get workable servers as list"""
        if self.workable_servers:
            try:
                return json.loads(self.workable_servers)
            except json.JSONDecodeError:
                return []
        return []
    
    @workable_servers_list.setter
    def workable_servers_list(self, value: Optional[List[str]]):
        """Set workable servers from list"""
        if value:
            self.workable_servers = json.dumps(value)
        else:
            self.workable_servers = None
    
    # Convenience properties for common metadata fields
    @property
    def title(self) -> Optional[str]:
        metadata = self.metadata_dict
        title = metadata.get('title')
        if isinstance(title, list):
            return title[0] if title else None
        return title
    
    @property
    def creator(self) -> Optional[str]:
        metadata = self.metadata_dict
        creator = metadata.get('creator')
        if isinstance(creator, list):
            return creator[0] if creator else None
        return creator
    
    @property
    def date(self) -> Optional[str]:
        metadata = self.metadata_dict
        return metadata.get('date')
    
    @property
    def venue(self) -> Optional[str]:
        metadata = self.metadata_dict
        return metadata.get('venue')
    
    @property
    def collection(self) -> Optional[List[str]]:
        metadata = self.metadata_dict
        collection = metadata.get('collection')
        if isinstance(collection, list):
            return collection
        elif isinstance(collection, str):
            return [collection]
        return None
    
    @property
    def avg_rating(self) -> Optional[float]:
        metadata = self.metadata_dict
        rating = metadata.get('avg_rating')
        if rating:
            try:
                return float(rating)
            except (ValueError, TypeError):
                return None
        return None
    
    @property
    def num_reviews(self) -> Optional[int]:
        metadata = self.metadata_dict
        reviews = metadata.get('num_reviews')
        if reviews:
            try:
                return int(reviews)
            except (ValueError, TypeError):
                return None
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization (Archive.org format)"""
        return {
            'identifier': self.identifier,
            'created': self.created,
            'd1': self.d1,
            'd2': self.d2,
            'dir': self.dir,
            'files_count': self.files_count,
            'item_last_updated': self.item_last_updated,
            'item_size': self.item_size,
            'metadata': self.metadata_dict,
            'server': self.server,
            'uniq': self.uniq,
            'workable_servers': self.workable_servers_list,
            'files': [file.to_dict() for file in self.files],
            # Backup fields
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_backed_up': self.is_backed_up,
            'backup_date': self.backup_date.isoformat() if self.backup_date else None
        }

class ArchiveFile(db.Model):
    """Complete Archive.org file model - direct replication of files array"""
    __tablename__ = 'archive_files'
    
    id = Column(Integer, primary_key=True)
    archive_item_id = Column(Integer, ForeignKey('archive_items.id'), nullable=False)
    
    # Core Archive.org file fields (exact replication)
    name = Column(String(500))
    source = Column(String(255))  # "original", "derivative", etc.
    format = Column(String(100))  # "VBR MP3", "FLAC", etc.
    mtime = Column(String(50))  # Unix timestamp as string
    size = Column(String(50))  # File size in bytes as string
    md5 = Column(String(64))
    crc32 = Column(String(50))
    sha1 = Column(String(64))
    
    # Audio/Video specific fields
    length = Column(String(50))  # Duration
    height = Column(String(50))  # Video height
    width = Column(String(50))  # Video width
    track = Column(String(50))  # Track number
    album = Column(String(500))  # Album name
    artist = Column(String(500))  # Artist name
    title = Column(String(500))  # Track title
    bitrate = Column(String(50))  # Bitrate
    creator = Column(String(500))  # Creator
    
    # Additional Archive.org fields
    private = Column(Boolean, default=False)  # Private file flag
    rotation = Column(String(50))  # Image rotation
    summation = Column(String(50))  # Checksum type
    
    # Backup specific fields
    local_path = Column(String(1000))  # Path to locally stored file
    is_downloaded = Column(Boolean, default=False)
    download_date = Column(DateTime)
    
    # Relationships
    archive_item = relationship("ArchiveItem", back_populates="files")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization (Archive.org format)"""
        result = {
            'name': self.name,
            'source': self.source,
            'format': self.format,
            'mtime': self.mtime,
            'size': self.size,
            'md5': self.md5,
            'crc32': self.crc32,
            'sha1': self.sha1,
            'private': self.private,
            'summation': self.summation
        }
        
        # Add optional fields only if they exist
        if self.length:
            result['length'] = self.length
        if self.height:
            result['height'] = self.height
        if self.width:
            result['width'] = self.width
        if self.track:
            result['track'] = self.track
        if self.album:
            result['album'] = self.album
        if self.artist:
            result['artist'] = self.artist
        if self.title:
            result['title'] = self.title
        if self.bitrate:
            result['bitrate'] = self.bitrate
        if self.creator:
            result['creator'] = self.creator
        if self.rotation:
            result['rotation'] = self.rotation
        
        # Add backup fields for internal use
        result['local_path'] = self.local_path
        result['is_downloaded'] = self.is_downloaded
        result['download_date'] = self.download_date.isoformat() if self.download_date else None
        
        return result

class BackupJob(db.Model):
    __tablename__ = 'backup_jobs'
    
    id = Column(Integer, primary_key=True)
    identifier = Column(String(255), nullable=False)
    job_type = Column(String(100), nullable=False)  # 'metadata', 'files', 'full'
    status = Column(String(50), default='pending')  # 'pending', 'running', 'completed', 'failed'
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    celery_task_id = Column(String(255))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'identifier': self.identifier,
            'job_type': self.job_type,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'celery_task_id': self.celery_task_id
        }

# Legacy aliases for backward compatibility
ShowMetadata = ArchiveItem
ShowFile = ArchiveFile
ShowMP3 = ArchiveFile  # Remove ShowMP3 as it's redundant