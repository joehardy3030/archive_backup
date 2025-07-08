from flask import Blueprint, request, jsonify
from app.api.archive_api import ArchiveAPI
from app.models.show_metadata import ArchiveItem, db
from sqlalchemy import or_, and_

search_bp = Blueprint('search', __name__)

@search_bp.route('/archive', methods=['GET'])
def search_archive():
    """Search Archive.org directly (proxy to Archive.org API)"""
    try:
        # Get search parameters
        search_term = request.args.get('search_term')
        venue = request.args.get('venue')
        min_rating = request.args.get('min_rating')
        start_year = request.args.get('start_year')
        end_year = request.args.get('end_year')
        sbd_only = request.args.get('sbd_only', 'false').lower() == 'true'
        collection = request.args.get('collection', 'GratefulDead')
        
        # Initialize Archive API
        archive_api = ArchiveAPI()
        
        # Build search URL
        search_url = archive_api.search_term_url(
            search_term=search_term,
            venue=venue,
            min_rating=min_rating,
            start_year=start_year,
            end_year=end_year,
            sbd_only=sbd_only,
            collection=collection
        )
        
        # Get results from Archive.org
        results = archive_api.get_search_results(search_url)
        
        if not results:
            return jsonify({'error': 'Failed to fetch search results from Archive.org'}), 500
        
        return jsonify({
            'results': results,
            'source': 'archive.org',
            'search_url': search_url
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@search_bp.route('/local', methods=['GET'])
def search_local():
    """Search locally backed up archive items"""
    try:
        # Get search parameters
        search_term = request.args.get('search_term')
        venue = request.args.get('venue')
        min_rating = request.args.get('min_rating', type=float)
        start_year = request.args.get('start_year', type=int)
        end_year = request.args.get('end_year', type=int)
        creator = request.args.get('creator')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Build query
        query = ArchiveItem.query
        
        # Apply filters - search within JSON metadata
        if search_term:
            query = query.filter(ArchiveItem.item_metadata.like(f'%{search_term}%'))
        
        if venue:
            query = query.filter(ArchiveItem.item_metadata.like(f'%{venue}%'))
        
        if min_rating is not None:
            # Note: For precise JSON filtering, would need database-specific JSON operators
            query = query.filter(ArchiveItem.item_metadata.like(f'%"avg_rating":"{min_rating}%'))
        
        if start_year:
            query = query.filter(ArchiveItem.item_metadata.like(f'%"year":"{start_year}%'))
        
        if end_year:
            query = query.filter(ArchiveItem.item_metadata.like(f'%"year":"{end_year}%'))
        
        if creator:
            query = query.filter(ArchiveItem.item_metadata.like(f'%{creator}%'))
        
        # Order by created_at descending
        query = query.order_by(ArchiveItem.created_at.desc())
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Format results
        results = []
        for item in pagination.items:
            downloaded_files = len([f for f in item.files if f.is_downloaded])
            results.append({
                'identifier': item.identifier,
                'title': item.title,
                'date': item.date,
                'venue': item.venue,
                'creator': item.creator,
                'avg_rating': item.avg_rating,
                'num_reviews': item.num_reviews,
                'collection': item.collection,
                'metadata': item.metadata_dict,
                'is_backed_up': item.is_backed_up,
                'backup_date': item.backup_date.isoformat() if item.backup_date else None,
                'total_files': len(item.files),
                'downloaded_files': downloaded_files
            })
        
        return jsonify({
            'results': {
                'items': results
            },
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            },
            'source': 'local'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@search_bp.route('/date_range', methods=['GET'])
def search_date_range():
    """Search Archive.org by date range"""
    try:
        # Get parameters
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        sbd_only = request.args.get('sbd_only', 'false').lower() == 'true'
        collection = request.args.get('collection', 'GratefulDead')
        
        if not year:
            return jsonify({'error': 'Year parameter is required'}), 400
        
        # Initialize Archive API
        archive_api = ArchiveAPI()
        
        # Build search URL
        if month:
            search_url = archive_api.date_range_url(year, month, sbd_only, collection)
        else:
            search_url = archive_api.date_range_year_url(year, sbd_only, collection)
        
        # Get results from Archive.org
        results = archive_api.get_search_results(search_url)
        
        if not results:
            return jsonify({'error': 'Failed to fetch search results from Archive.org'}), 500
        
        return jsonify({
            'results': results,
            'source': 'archive.org',
            'search_url': search_url,
            'year': year,
            'month': month
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@search_bp.route('/year_total', methods=['GET'])
def get_year_total():
    """Get total count for a year"""
    try:
        # Get parameters
        year = request.args.get('year', type=int)
        sbd_only = request.args.get('sbd_only', 'false').lower() == 'true'
        collection = request.args.get('collection', 'GratefulDead')
        
        if not year:
            return jsonify({'error': 'Year parameter is required'}), 400
        
        # Initialize Archive API
        archive_api = ArchiveAPI()
        
        # Build search URL
        search_url = archive_api.year_range_total_url(year, sbd_only, collection)
        
        # Get results from Archive.org
        results = archive_api.get_total_results(search_url)
        
        if not results:
            return jsonify({'error': 'Failed to fetch total results from Archive.org'}), 500
        
        return jsonify({
            'results': results,
            'source': 'archive.org',
            'search_url': search_url,
            'year': year
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@search_bp.route('/local_stats', methods=['GET'])
def get_local_stats():
    """Get statistics about locally backed up archive items"""
    try:
        # Total backed up items
        total_items = ArchiveItem.query.count()
        
        # Fully backed up items (with files)
        fully_backed_up = ArchiveItem.query.filter_by(is_backed_up=True).count()
        
        # Basic stats (JSON querying would be database-specific)
        year_stats = []
        creator_stats = []
        
        # Total file count (simplified)
        file_stats = {
            'total_files': 0,
            'downloaded_files': 0
        }
        
        return jsonify({
            'total_items': total_items,
            'fully_backed_up': fully_backed_up,
            'backup_percentage': (fully_backed_up / total_items * 100) if total_items > 0 else 0,
            'year_stats': year_stats,
            'creator_stats': creator_stats,
            'file_stats': file_stats
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@search_bp.route('/hybrid', methods=['GET'])
def search_hybrid():
    """Search both local and Archive.org, showing local results first"""
    try:
        # Get search parameters
        search_term = request.args.get('search_term')
        venue = request.args.get('venue')
        min_rating = request.args.get('min_rating')
        start_year = request.args.get('start_year')
        end_year = request.args.get('end_year')
        sbd_only = request.args.get('sbd_only', 'false').lower() == 'true'
        collection = request.args.get('collection', 'GratefulDead')
        
        # Search local first
        local_results = []
        
        # Build local query
        query = ArchiveItem.query
        
        # Apply filters (simplified for JSON metadata)
        if search_term:
            query = query.filter(ArchiveItem.item_metadata.like(f'%{search_term}%'))
        
        if venue:
            query = query.filter(ArchiveItem.item_metadata.like(f'%{venue}%'))
        
        if min_rating:
            query = query.filter(ArchiveItem.item_metadata.like(f'%"avg_rating":"{min_rating}%'))
        
        if start_year:
            query = query.filter(ArchiveItem.item_metadata.like(f'%"year":"{start_year}%'))
        
        if end_year:
            query = query.filter(ArchiveItem.item_metadata.like(f'%"year":"{end_year}%'))
        
        # Get local results
        local_items = query.order_by(ArchiveItem.created_at.desc()).limit(20).all()
        
        for item in local_items:
            downloaded_files = len([f for f in item.files if f.is_downloaded])
            local_results.append({
                'identifier': item.identifier,
                'title': item.title,
                'date': item.date,
                'venue': item.venue,
                'creator': item.creator,
                'avg_rating': item.avg_rating,
                'num_reviews': item.num_reviews,
                'collection': item.collection,
                'metadata': item.metadata_dict,
                'is_backed_up': item.is_backed_up,
                'backup_date': item.backup_date.isoformat() if item.backup_date else None,
                'total_files': len(item.files),
                'downloaded_files': downloaded_files,
                'result_source': 'local'
            })
        
        # Search Archive.org
        archive_api = ArchiveAPI()
        search_url = archive_api.search_term_url(
            search_term=search_term,
            venue=venue,
            min_rating=min_rating,
            start_year=start_year,
            end_year=end_year,
            sbd_only=sbd_only,
            collection=collection
        )
        
        archive_results = archive_api.get_search_results(search_url)
        
        # Get local identifiers to avoid duplicates
        local_identifiers = set(result['identifier'] for result in local_results)
        
        # Add Archive.org results that aren't already local
        combined_results = local_results.copy()
        
        if archive_results and 'items' in archive_results:
            for item in archive_results['items']:
                if item.get('identifier') not in local_identifiers:
                    item['result_source'] = 'archive.org'
                    item['is_backed_up'] = False
                    combined_results.append(item)
        
        return jsonify({
            'results': {
                'items': combined_results
            },
            'local_count': len(local_results),
            'archive_count': len(combined_results) - len(local_results),
            'source': 'hybrid',
            'search_url': search_url
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500