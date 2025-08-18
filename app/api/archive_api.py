import requests
import json
import urllib.parse
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
import os
import time

class ArchiveAPI:
    """Python implementation of the Archive.org API client, mirroring the Swift ArchiveAPI.swift"""
    
    def __init__(self, timeout: int = 10000):
        self.base_url = "https://archive.org/"
        self.timeout = timeout / 1000  # Convert to seconds
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ArchiveBackup/1.0 (Python/Flask Archive.org Backup Client)'
        })
    
    def metadata_url(self, identifier: str) -> str:
        """Build metadata URL for a given identifier"""
        return f"{self.base_url}metadata/{identifier}"
    
    def download_url(self, identifier: Optional[str] = None, filename: Optional[str] = None) -> Optional[str]:
        """Build download URL for a given identifier and filename"""
        if not identifier:
            return None
        
        url = f"{self.base_url}download/{identifier}"
        if filename:
            url += f"/{filename}"
        
        # URL encode the string
        encoded_url = urllib.parse.quote(url, safe=':/?#[]@!$&\'()*+,;=')
        return encoded_url
    
    def date_range_url(self, year: int, month: int, sbd_only: bool = False, collection: str = "GratefulDead") -> str:
        """Build date range search URL"""
        and_string = "%20AND%20"
        date_string = "date%3A%5B"
        to_string = "%20TO%20"
        
        url = f"{self.base_url}services/search/v1/scrape?"
        url += "fields=identifier,date,venue,transferer,source,coverage,stars,avg_rating,num_reviews,collection,creator&"
        
        # Check if this is a creator-based search
        if self._is_creator_based(collection):
            url += f"q=creator%3A%22{collection}%22"
        else:
            # Original collection-based search
            if sbd_only:
                url += f"q=collection%3A%28{collection}%20AND%20stream_only%29"
            else:
                url += f"q=collection%3A%28{collection}%29"
        
        url += and_string
        url += date_string
        
        month_string = f"{month:02d}"
        url += f"{year}-{month_string}-01"
        url += to_string
        
        # Calculate last day of month
        if month in [1, 3, 5, 7, 8, 10, 12]:
            last_day = 31
        elif month in [4, 6, 9, 11]:
            last_day = 30
        elif month == 2:
            last_day = 28  # Not handling leap years for simplicity
        else:
            last_day = 30
        
        url += f"{year}-{month_string}-{last_day:02d}"
        url += "%5D"
        
        print(f"[ArchiveAPI] Date range URL: {url}")
        return url
    
    def date_range_year_url(self, year: int, sbd_only: bool = False, collection: str = "GratefulDead") -> str:
        """Build year range search URL"""
        first_day_month = "01-01"
        last_day_month = "12-31"
        and_string = "%20AND%20"
        date_string = "date%3A%5B"
        to_string = "%20TO%20"
        
        url = f"{self.base_url}services/search/v1/scrape?"
        url += "fields=identifier,date,venue,transferer,source,coverage,stars,avg_rating,num_reviews,collection,creator&"
        
        # Check if this is a creator-based search
        if self._is_creator_based(collection):
            url += f"q=creator%3A%22{collection}%22"
        else:
            # Original collection-based search
            if sbd_only:
                url += f"q=collection%3A%28{collection}%20AND%20stream_only%29"
            else:
                url += f"q=collection%3A%28{collection}%29"
        
        url += and_string
        url += date_string
        url += f"{year}-{first_day_month}"
        url += to_string
        url += f"{year}-{last_day_month}"
        url += "%5D"
        
        print(f"[ArchiveAPI] Year range URL: {url}")
        return url
    
    def year_range_total_url(self, year: int, sbd_only: bool = False, collection: str = "GratefulDead") -> str:
        """Build year range total count URL"""
        first_day_month = "01-01"
        last_day_month = "12-31"
        and_string = "%20AND%20"
        date_string = "date%3A%5B"
        to_string = "%20TO%20"
        
        url = f"{self.base_url}advancedsearch.php?"
        
        # Check if this is a creator-based search
        if self._is_creator_based(collection):
            url += f"q=creator%3A%22{collection}%22"
        else:
            # Original collection-based search
            if sbd_only:
                url += f"q=collection%3A%28{collection}%20AND%20stream_only%29"
            else:
                url += f"q=collection%3A%28{collection}%29"
        
        url += and_string
        url += date_string
        url += f"{year}-{first_day_month}"
        url += to_string
        url += f"{year}-{last_day_month}"
        url += "%5D"
        url += "&output=json&rows=0"
        
        print(f"[ArchiveAPI] Year total URL: {url}")
        return url
    
    def search_term_url(self, search_term: Optional[str] = None, venue: Optional[str] = None, 
                       min_rating: Optional[str] = None, start_year: Optional[str] = None,
                       end_year: Optional[str] = None, sbd_only: Optional[bool] = None,
                       collection: str = "GratefulDead") -> str:
        """Build search URL with various search parameters"""
        start_month_day = "01-01"
        end_month_day = "12-31"
        
        # Build query components
        query_parts = []
        
        # Check if this is a creator-based search
        if self._is_creator_based(collection):
            if sbd_only:
                query_parts.append(f"creator:\"{collection}\" AND collection:stream_only")
            else:
                query_parts.append(f"creator:\"{collection}\"")
        else:
            # Original collection-based search
            if sbd_only:
                query_parts.append(f"collection:({collection}%20AND%20stream_only)")
            else:
                query_parts.append(f"collection:{collection}")
        
        # Add search term
        if search_term:
            st_plus = search_term.replace(" ", "+")
            query_parts.append(st_plus)
        
        # Add date range
        start_year_val = start_year if start_year else "1965"
        end_year_val = end_year if end_year else "2025"
        query_parts.append(f"date:[{start_year_val}-{start_month_day} TO {end_year_val}-{end_month_day}]")
        
        # Add rating filter
        if min_rating:
            query_parts.append(f"(avg_rating:[{min_rating} TO 5.0])")
        
        # Add venue filter
        if venue:
            vu_plus = venue.replace(" ", "+")
            query_parts.append(f"(venue:{vu_plus})")
        
        # Build final URL
        fields = "identifier,date,venue,transferer,source,coverage,stars,avg_rating,num_reviews,collection,creator"
        query_string = " AND ".join(query_parts)
        
        url = f"{self.base_url}services/search/v1/scrape?fields={fields}&q={query_string}"
        
        print(f"[ArchiveAPI] Search URL: {url}")
        return url
    
    def get_metadata(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a show identifier"""
        url = self.metadata_url(identifier)
        start_time = time.time()
        
        print(f"[ArchiveAPI] Requesting metadata from URL: {url} at {self._timestamp()}")
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            duration = time.time() - start_time
            
            print(f"[ArchiveAPI] get_metadata for URL: {url} took {duration:.3f} seconds.")
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[ArchiveAPI] Error {response.status_code} for URL {url}")
                return None
                
        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            print(f"[ArchiveAPI] Error for URL {url}: {str(e)}")
            print(f"[ArchiveAPI] get_metadata for URL: {url} took {duration:.3f} seconds.")
            return None
    
    def get_search_results(self, url: str) -> Optional[Dict[str, Any]]:
        """Get search results from Archive.org"""
        start_time = time.time()
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            duration = time.time() - start_time
            
            print(f"[ArchiveAPI] get_search_results for URL: {url} took {duration:.3f} seconds.")
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[ArchiveAPI] Error {response.status_code} for URL {url}")
                return None
                
        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            print(f"[ArchiveAPI] Error for URL {url}: {str(e)}")
            print(f"[ArchiveAPI] get_search_results for URL: {url} took {duration:.3f} seconds.")
            return None
    
    def get_total_results(self, url: str) -> Optional[Dict[str, Any]]:
        """Get total count results from Archive.org"""
        try:
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[ArchiveAPI] Error {response.status_code} for URL {url}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"[ArchiveAPI] Error for URL {url}: {str(e)}")
            return None
    
    def download_file(self, identifier: str, filename: str, 
                     progress_callback: Optional[Callable[[float], None]] = None) -> Optional[str]:
        """Download a file from Archive.org"""
        download_url = self.download_url(identifier, filename)
        if not download_url:
            print(f"[ArchiveAPI] Could not build download URL for {identifier}/{filename}")
            return None
        
        try:
            # Create local storage directory
            storage_dir = os.path.join("storage", "files", identifier)
            os.makedirs(storage_dir, exist_ok=True)
            
            # Support nested paths present in some collections (e.g., dac2025-08-01.mk4/dac2025-08-01.mk4.d1t01.mp3)
            # Sanitize and normalize the relative path to prevent path traversal
            sanitized_filename = (filename or "").replace("\\", "/").lstrip("/")
            normalized_rel_path = os.path.normpath(sanitized_filename)
            if normalized_rel_path.startswith(".."):
                print(f"[ArchiveAPI] Unsafe filename detected, refusing to write outside storage: {filename}")
                return None

            local_path = os.path.join(storage_dir, normalized_rel_path)

            # Ensure any intermediate directories exist for nested paths
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            print(f"[ArchiveAPI] Starting download from {download_url} to {local_path}")
            
            with self.session.get(download_url, stream=True, timeout=self.timeout) as response:
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            if progress_callback and total_size > 0:
                                progress = downloaded / total_size
                                progress_callback(progress)
            
            print(f"[ArchiveAPI] Download completed. File saved to: {local_path}")
            return local_path
            
        except requests.exceptions.RequestException as e:
            print(f"[ArchiveAPI] Download failed with error: {str(e)} for URL: {download_url}")
            return None
        except OSError as e:
            # Handle filesystem errors (e.g., invalid path, permission issues)
            print(f"[ArchiveAPI] Filesystem error saving {identifier}/{filename}: {e}")
            return None
    
    def _is_creator_based(self, collection: str) -> bool:
        """Check if collection uses creator-based search"""
        creator_based_collections = ["etree", "PhilLeshAndFriends", "BobWeir"]
        return collection in creator_based_collections
    
    def _timestamp(self) -> str:
        """Get current timestamp in HH:mm:ss.SSS format"""
        return datetime.now().strftime("%H:%M:%S.%f")[:-3] 