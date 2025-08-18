from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, Response
from app.models.show_metadata import ArchiveItem, db
from app.api.archive_api import ArchiveAPI
from sqlalchemy import desc
from datetime import datetime
import os

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Main dashboard page"""
    try:
        # Get recent backups
        recent_backups = ArchiveItem.query.order_by(desc(ArchiveItem.created_at)).limit(10).all()
        
        # Get basic stats
        total_items = ArchiveItem.query.count()
        fully_backed_up = ArchiveItem.query.filter_by(is_backed_up=True).count()
        
        return render_template('index.html',
                             recent_backups=recent_backups,
                             total_shows=total_items,
                             fully_backed_up=fully_backed_up)
    except Exception as e:
        return render_template('index.html',
                             recent_backups=[],
                             total_shows=0,
                             fully_backed_up=0,
                             error=str(e))

@main_bp.route('/backup')
def backup_page():
    """Backup management page"""
    return render_template('backup.html')

@main_bp.route('/search')
def search_page():
    """Search page"""
    return render_template('search.html')

@main_bp.route('/show/<identifier>')
def show_detail(identifier):
    """Show detail page"""
    try:
        item = ArchiveItem.query.filter_by(identifier=identifier).first_or_404()
        
        # Count downloaded files
        downloaded_files = [f for f in item.files if f.is_downloaded]
        total_files = len(item.files)
        
        # Calculate progress percentage
        progress_percent = (len(downloaded_files) / total_files * 100) if total_files > 0 else 0
        
        return render_template('show_detail.html',
                             item=item,
                             downloaded_files=downloaded_files,
                             total_files=total_files,
                             progress_percent=progress_percent)
    except Exception as e:
        flash(f'Error loading show: {str(e)}', 'error')
        return redirect(url_for('main.index'))

@main_bp.route('/browse')
def browse():
    """Browse backed up shows"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Get search parameters
        search_term = request.args.get('search_term', '')
        creator = request.args.get('creator', '')
        year = request.args.get('year', '')
        
        # Build query
        query = ArchiveItem.query
        
        if search_term:
            query = query.filter(ArchiveItem.item_metadata.like(f'%{search_term}%'))
        
        if creator:
            query = query.filter(ArchiveItem.item_metadata.like(f'%{creator}%'))
        
        if year:
            query = query.filter(ArchiveItem.item_metadata.like(f'%"year":"{year}%'))
        
        # Order by created_at descending
        query = query.order_by(desc(ArchiveItem.created_at))
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Get unique creators and years (simplified - would need JSON extraction for production)
        creators = []
        years = []
        
        return render_template('browse.html',
                             items=pagination.items,
                             pagination=pagination,
                             creators=creators,
                             years=years,
                             search_term=search_term,
                             selected_creator=creator,
                             selected_year=year)
    except Exception as e:
        flash(f'Error browsing shows: {str(e)}', 'error')
        return render_template('browse.html',
                             items=[],
                             pagination=None,
                             creators=[],
                             years=[],
                             search_term='',
                             selected_creator='',
                             selected_year='')

@main_bp.route('/stats')
def stats():
    """Statistics page"""
    try:
        # Basic stats
        total_items = ArchiveItem.query.count()
        fully_backed_up = ArchiveItem.query.filter_by(is_backed_up=True).count()
        
        # Simplified stats (JSON querying would be database-specific)
        year_stats = []
        creator_stats = []
        
        # Recent backups
        recent_backups = ArchiveItem.query.filter(
            ArchiveItem.backup_date.isnot(None)
        ).order_by(desc(ArchiveItem.backup_date)).limit(10).all()
        
        return render_template('stats.html',
                             total_items=total_items,
                             fully_backed_up=fully_backed_up,
                             year_stats=year_stats,
                             creator_stats=creator_stats,
                             recent_backups=recent_backups)
    except Exception as e:
        flash(f'Error loading statistics: {str(e)}', 'error')
        return render_template('stats.html',
                             total_items=0,
                             fully_backed_up=0,
                             year_stats=[],
                             creator_stats=[],
                             recent_backups=[])

@main_bp.route('/api/quick_backup', methods=['POST'])
def quick_backup():
    """Quick backup endpoint for web interface"""
    try:
        data = request.get_json()
        identifier = data.get('identifier')
        
        if not identifier:
            return jsonify({'error': 'Identifier is required'}), 400
        
        # Initialize Archive API
        archive_api = ArchiveAPI()
        
        # Get metadata
        metadata_response = archive_api.get_metadata(identifier)
        if not metadata_response:
            return jsonify({'error': 'Failed to fetch metadata from Archive.org'}), 404
        
        # Check if already exists
        existing = ArchiveItem.query.filter_by(identifier=identifier).first()
        if existing:
            return jsonify({'error': 'Archive item already backed up', 'identifier': identifier}), 409
        
        # Create metadata
        from app.api.backup_routes import create_metadata_from_response
        archive_item = create_metadata_from_response(metadata_response)
        db.session.add(archive_item)
        db.session.commit()
        
        return jsonify({
            'message': 'Metadata backed up successfully',
            'identifier': identifier,
            'title': archive_item.title
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/metadata/<identifier>')
def get_metadata(identifier):
    """Get metadata for a specific identifier - checks local first, then Archive.org"""
    try:
        # Check if we have local metadata first
        local_item = ArchiveItem.query.filter_by(identifier=identifier).first()
        
        if local_item:
            # Return local metadata in the same format as Archive.org API
            metadata_dict = local_item.metadata_dict or {}
            
            # Add stats data to metadata if available
            if local_item.stats:
                metadata_dict['avg_rating'] = local_item.stats.avg_rating
                metadata_dict['num_reviews'] = local_item.stats.num_reviews
                metadata_dict['downloads'] = local_item.stats.downloads
                metadata_dict['downloads_week'] = local_item.stats.downloads_week
                metadata_dict['downloads_month'] = local_item.stats.downloads_month
            
            local_metadata = {
                'metadata': metadata_dict,
                'created': local_item.created,
                'd1': local_item.d1,
                'd2': local_item.d2,
                'dir': local_item.dir,
                'files_count': local_item.files_count,
                'item_last_updated': local_item.item_last_updated,
                'item_size': local_item.item_size,
                'server': local_item.server,
                'uniq': local_item.uniq,
                'workable_servers': local_item.workable_servers_list,
                'files': [file.to_dict() for file in local_item.files]
            }
            
            # Add local-specific fields
            local_metadata['is_local'] = True
            local_metadata['backup_date'] = local_item.backup_date.isoformat() if local_item.backup_date else None
            local_metadata['is_backed_up'] = local_item.is_backed_up
            
            return jsonify(local_metadata)
        
        # If not found locally, fetch from Archive.org
        archive_api = ArchiveAPI()
        metadata_response = archive_api.get_metadata(identifier)
        if not metadata_response:
            return jsonify({'error': 'Failed to fetch metadata from Archive.org'}), 404
        
        # Also fetch ratings from search API for Archive.org items
        try:
            search_url = f"{archive_api.base_url}services/search/v1/scrape?fields=avg_rating,num_reviews,stars,downloads,week,month&q=identifier:{identifier}"
            search_results = archive_api.get_search_results(search_url)
            
            if search_results and search_results.get('items') and len(search_results['items']) > 0:
                search_data = search_results['items'][0]
                # Add ratings to metadata
                if not metadata_response.get('metadata'):
                    metadata_response['metadata'] = {}
                metadata_response['metadata']['avg_rating'] = search_data.get('avg_rating')
                metadata_response['metadata']['num_reviews'] = search_data.get('num_reviews')
                metadata_response['metadata']['downloads'] = search_data.get('downloads')
                print(f"Added ratings to metadata: {search_data.get('avg_rating')} stars, {search_data.get('num_reviews')} reviews")
        except Exception as e:
            print(f"Warning: Could not fetch ratings for {identifier}: {str(e)}")
            # Continue without ratings - not critical
        
        # Mark as not local
        metadata_response['is_local'] = False
        return jsonify(metadata_response)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/update_ratings', methods=['POST'])
def update_all_ratings():
    """Update rating, stats, and review information for all existing backed-up shows"""
    try:
        from app.models.show_metadata import ArchiveItemStats, ArchiveItemReview
        
        archive_api = ArchiveAPI()
        items = ArchiveItem.query.all()
        updated_count = 0
        reviews_updated = 0
        
        for item in items:
            try:
                # Fetch fresh metadata to get current reviews
                metadata_response = archive_api.get_metadata(item.identifier)
                if metadata_response and metadata_response.get('metadata'):
                    # Update reviews from metadata API
                    reviews_data = metadata_response['metadata'].get('reviews', [])
                    
                    # Clear existing reviews
                    ArchiveItemReview.query.filter_by(archive_item_id=item.id).delete()
                    
                    # Add current reviews
                    for review_data in reviews_data:
                        review = ArchiveItemReview(
                            archive_item_id=item.id,
                            reviewbody=review_data.get('reviewbody'),
                            reviewtitle=review_data.get('reviewtitle'),
                            reviewer=review_data.get('reviewer'),
                            reviewdate=review_data.get('reviewdate'),
                            createdate=review_data.get('createdate'),
                            stars=review_data.get('stars'),
                            reviewer_itemname=review_data.get('reviewer_itemname')
                        )
                        db.session.add(review)
                        reviews_updated += 1
                
                # Fetch stats data from search API
                search_url = f"{archive_api.base_url}services/search/v1/scrape?fields=avg_rating,num_reviews,stars,downloads,week,month&q=identifier:{item.identifier}"
                search_results = archive_api.get_search_results(search_url)
                if search_results and search_results.get('items'):
                    search_data = search_results['items'][0]
                    
                    # Get or create stats record
                    stats = ArchiveItemStats.query.filter_by(archive_item_id=item.id).first()
                    if not stats:
                        stats = ArchiveItemStats(archive_item_id=item.id)
                        db.session.add(stats)
                    
                    # Update with search API data
                    stats.avg_rating = search_data.get('avg_rating')
                    stats.num_reviews = search_data.get('num_reviews')
                    stats.stars_list = search_data.get('stars', [])
                    stats.downloads = search_data.get('downloads')
                    stats.downloads_week = search_data.get('week')
                    stats.downloads_month = search_data.get('month')
                    stats.last_updated = datetime.utcnow()
                    
                    updated_count += 1
                    print(f"Updated stats for {item.identifier}: {search_data.get('avg_rating')} stars, {search_data.get('downloads')} downloads")
                    
            except Exception as e:
                print(f"Failed to update stats for {item.identifier}: {str(e)}")
                continue
        
        db.session.commit()
        
        return jsonify({
            'message': f'Updated stats and reviews for {updated_count} shows',
            'updated_count': updated_count,
            'reviews_updated': reviews_updated,
            'total_items': len(items)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@main_bp.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        
        # Check Archive.org connection
        archive_api = ArchiveAPI()
        test_url = archive_api.metadata_url('test')
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'archive_api': 'available',
            'timestamp': db.func.now()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500 

@main_bp.route('/play/<identifier>/<path:filename>')
def play_file(identifier, filename):
    """Serve audio files for playback"""
    try:
        # Security: Verify the file belongs to a backed up show
        item = ArchiveItem.query.filter_by(identifier=identifier).first_or_404()
        
        # Find the specific file
        file_record = None
        for file_obj in item.files:
            if file_obj.name == filename:
                file_record = file_obj
                break
        
        if not file_record:
            return jsonify({'error': f'File {filename} not found in database'}), 404
        
        # Check if file is downloaded and has local path
        if not file_record.is_downloaded:
            return jsonify({'error': f'File {filename} not downloaded yet'}), 404
        
        if not file_record.local_path:
            return jsonify({'error': f'File {filename} has no local path'}), 404
        
        # Get the full path
        files_storage_path = current_app.config.get('FILES_STORAGE_PATH', 'storage/files')
        
        if file_record.local_path:
            # Check if local_path already contains the storage path prefix
            if file_record.local_path.startswith('storage/files/'):
                # local_path already contains the storage path, use it directly
                file_path = file_record.local_path
            else:
                # local_path is relative to FILES_STORAGE_PATH
                file_path = os.path.join(files_storage_path, file_record.local_path)
        else:
            # Fallback: construct path based on identifier and filename
            file_path = os.path.join(files_storage_path, identifier, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': f'File not found on disk: {file_path}'}), 404
        
        # Determine content type
        content_type = 'audio/mpeg'  # Default
        if filename.lower().endswith('.flac'):
            content_type = 'audio/flac'
        elif filename.lower().endswith('.mp3'):
            content_type = 'audio/mpeg'
        elif filename.lower().endswith('.ogg'):
            content_type = 'audio/ogg'
        elif filename.lower().endswith('.wav'):
            content_type = 'audio/wav'
        
        # Support range requests for seeking
        def generate():
            with open(file_path, 'rb') as f:
                while True:
                    data = f.read(8192)  # 8KB chunks
                    if not data:
                        break
                    yield data
        
        response = Response(generate(), mimetype=content_type)
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Content-Length'] = str(os.path.getsize(file_path))
        response.headers['Cache-Control'] = 'public, max-age=3600'
        
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500 