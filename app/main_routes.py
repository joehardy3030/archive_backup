from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models.show_metadata import ArchiveItem, db
from app.api.archive_api import ArchiveAPI
from sqlalchemy import desc

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
        
        return render_template('show_detail.html',
                             item=item,
                             downloaded_files=downloaded_files,
                             total_files=total_files)
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
    """Get metadata for a specific identifier"""
    try:
        # Initialize Archive API
        archive_api = ArchiveAPI()
        
        # Get metadata from Archive.org
        metadata_response = archive_api.get_metadata(identifier)
        if not metadata_response:
            return jsonify({'error': 'Failed to fetch metadata from Archive.org'}), 404
        
        return jsonify(metadata_response)
        
    except Exception as e:
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