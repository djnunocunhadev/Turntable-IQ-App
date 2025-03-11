#!/usr/bin/env python3
"""
TurntableIQ API with real Rekordbox database reader.
"""
import os
import json
import time
import sqlite3
import logging
import tempfile
import shutil
import struct
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from fastapi import FastAPI, Query, HTTPException, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import sys

# Import our application database module
from app_database import AppDatabase

# Global variables
app_db = None

# Initialize the application database
def get_app_db():
    global app_db
    if app_db is None:
        app_db = AppDatabase()
    return app_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set log level from environment variable
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logger.setLevel(getattr(logging, log_level))

# Create FastAPI app
app = FastAPI(
    title="TurntableIQ API",
    description="API for TurntableIQ DJ library management system",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In development, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Models
class ConnectionRequest(BaseModel):
    db_path: str
    db_key: str
    
class ConnectionResponse(BaseModel):
    success: bool
    message: str
    
class Tag(BaseModel):
    id: int
    name: str
    
class TrackBase(BaseModel):
    id: int
    title: str
    artist: str
    album: Optional[str] = None
    genre: Optional[str] = None
    duration: float
    file_path: str
    bpm: Optional[float] = None
    key: Optional[str] = None
    energy: Optional[float] = None
    rekordbox_id: Optional[int] = None
    created_at: str
    updated_at: str
    tags: List[Tag] = Field(default_factory=list)

# Rekordbox database handling
class RekordboxDatabase:
    """Class to handle the Rekordbox database connection and operations."""
    
    def __init__(self, db_path, db_key):
        self.db_path = db_path
        self.db_key = db_key
        self.conn = None
        self.temp_db_path = None
    
    def connect(self):
        """Connect to the Rekordbox database."""
        try:
            # First try to import pyrekordbox
            import_success = False
            try:
                import pyrekordbox
                self.pyrekordbox = pyrekordbox
                import_success = True
                logger.info("Using pyrekordbox for database access")
            except ImportError:
                logger.info("pyrekordbox not available, falling back to direct database access")
            
            # If pyrekordbox import failed or we're using direct access
            if not import_success:
                # Try to use sqlcipher3 directly
                try:
                    import sqlcipher3
                    logger.info("Using sqlcipher3 for direct database access")
                    
                    # Create a temporary copy of the database
                    self.temp_db_path = tempfile.mktemp(suffix='.db')
                    logger.info(f"Created temporary copy at {self.temp_db_path}")
                    shutil.copy2(self.db_path, self.temp_db_path)
                    
                    # Connect to the database
                    self.conn = sqlcipher3.connect(self.temp_db_path)
                    self.conn.execute(f"PRAGMA key = \"x'{self.db_key}'\"")
                    
                    # Verify connection by checking for tables
                    cursor = self.conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                    tables = cursor.fetchall()
                    
                    if tables:
                        table_names = ', '.join([table[0] for table in tables[:5]]) + f"... (total: {len(tables)})"
                        logger.info(f"Found tables: {table_names}")
                        
                        # Check if we can access the content table
                        cursor.execute("SELECT COUNT(*) FROM djmdContent;")
                        count = cursor.fetchone()[0]
                        logger.info(f"Found {count} tracks in database")
                        
                        # Try to get some track info
                        cursor.execute("SELECT ID, Title FROM djmdContent LIMIT 5;")
                        tracks = cursor.fetchall()
                        logger.info(f"Track count from SQL: {count}")
                        logger.info(f"Connection verification: Found {len(tracks)} tracks")
                        logger.info("SQLCipher connection is still valid")
                        return True
                    else:
                        logger.error("No tables found in database")
                        return False
                except Exception as e:
                    logger.error(f"Error with direct SQLCipher connection: {e}")
                    return False
            else:
                # Use pyrekordbox
                try:
                    # Connect using pyrekordbox
                    self.db = self.pyrekordbox.Database(self.db_path, self.db_key)
                    # Verify connection by getting tracks
                    tracks = list(self.db.tracks())
                    logger.info(f"Connected using pyrekordbox - found {len(tracks)} tracks")
                    return True
                except Exception as e:
                    logger.error(f"Error with pyrekordbox connection: {e}")
                    return False
        except Exception as e:
            logger.error(f"Error connecting to Rekordbox database: {e}")
            return False
    
    def extract_tracks(self, limit=None, offset=0):
        """
        Extract tracks from the Rekordbox database.
        
        Args:
            limit: Maximum number of tracks to extract (None for all)
            offset: Offset for pagination
            
        Returns:
            List of track dictionaries
        """
        # First try SQL method
        try:
            logger.info(f"Starting track extraction with connection type: SQLCipher={self.conn is not None}, pyrekordbox={hasattr(self, 'db')}")
            
            if self.conn:
                # SQL method
                return self._extract_tracks_from_sql(limit, offset)
            elif hasattr(self, 'db'):
                # pyrekordbox method
                return self._extract_tracks_from_pyrekordbox(limit, offset)
            else:
                logger.error("No valid connection method available")
                return []
        except Exception as e:
            logger.error(f"Error extracting tracks: {e}")
            return []
    
    def _extract_tracks_from_sql(self, limit=None, offset=0):
        """Extract tracks using direct SQL access."""
        if not self.conn:
            logger.error("No SQL connection available")
            return []
        
        tracks = []
        cursor = self.conn.cursor()
        
        try:
            # Get total tracks in database
            cursor.execute("SELECT COUNT(*) FROM djmdContent")
            total_tracks = cursor.fetchone()[0]
            logger.info(f"Total tracks in database: {total_tracks}")
            
            # Check available columns in the table
            cursor.execute("PRAGMA table_info(djmdContent)")
            columns = cursor.fetchall()
            logger.info(f"djmdContent table has {len(columns)} columns")
            
            # Log first 10 columns for debugging
            first_10_columns = columns[:10]
            logger.info(f"First 10 columns: {', '.join([f'{col[1]}({col[0]})' for col in first_10_columns])}")
            
            # Get a sample row to understand the data
            cursor.execute("SELECT * FROM djmdContent LIMIT 1")
            sample_row = cursor.fetchone()
            if sample_row:
                sample_values = sample_row[:10]  # First 10 values for readability
                logger.info(f"Sample row first 10 values: {sample_values}")
                
                # Log specific column values for debugging
                for i, col in enumerate(first_10_columns):
                    if i < len(sample_row):
                        logger.info(f"Column {col[1]} = {sample_row[i]}")
            
            # Build a query with appropriate columns based on whether they exist
            # Starting with a more comprehensive join to get all needed info
            limit_clause = f"LIMIT {limit} OFFSET {offset}" if limit is not None else ""
            
            # Try a comprehensive query with joins
            try:
                enhanced_query = f"""
                    SELECT c.ID, c.Title, c.Length, c.BPM, c.FolderPath, 
                           k.ScaleName as KeyName, g.Name as GenreName,
                           a.Name as ArtistName
                    FROM djmdContent c
                    LEFT JOIN djmdKey k ON c.KeyID = k.ID
                    LEFT JOIN djmdGenre g ON c.GenreID = g.ID
                    LEFT JOIN djmdArtist a ON c.ArtistID = a.ID
                    ORDER BY c.ID
                    {limit_clause}
                """
                
                logger.info("Executing enhanced query with key and genre joins")
                cursor.execute(enhanced_query)
                rows = cursor.fetchall()
                
                if rows:
                    logger.info(f"Successfully retrieved {len(rows)} tracks with key and genre info")
                    
                    tracks = []
                    for i, row in enumerate(rows):
                        if i < 5:
                            logger.info(f"Row {i} data: {row}")
                        
                        # Basic data extraction with proper error handling
                        track_id = row[0] if len(row) > 0 else i+1
                        title = row[1] or f"Track {i+1}" if len(row) > 1 else f"Track {i+1}"
                        
                        # Process duration - critically important!
                        raw_duration = row[2] if len(row) > 2 else 0
                        logger.info(f"Raw duration value for track '{title}': {raw_duration}")
                        
                        # Convert from frames to seconds, but treat as seconds if already large enough
                        if raw_duration is not None and raw_duration > 0:
                            if raw_duration < 1000:  # Small values are likely frames
                                # Use raw duration as is (in seconds)
                                duration = float(raw_duration)
                                logger.info(f"Using raw duration as seconds: {raw_duration} seconds")
                            else:  # Larger values might already be in milliseconds
                                duration = float(raw_duration) / 1000.0
                                logger.info(f"Converting from milliseconds: {raw_duration}/1000 = {duration:.2f} seconds")
                        else:
                            duration = 0
                            logger.info(f"Invalid duration value, setting to 0")
                        
                        # Process BPM
                        bpm_raw = row[3] or 0.0 if len(row) > 3 else 0.0
                        bpm = float(bpm_raw) / 100.0 if bpm_raw else 0.0
                        
                        # Get file path
                        file_path = row[4] or "" if len(row) > 4 else ""
                        
                        # Get key name
                        key_name = row[5] or "Unknown" if len(row) > 5 else "Unknown"
                        
                        # Get genre name
                        genre_name = row[6] or "Unknown Genre" if len(row) > 6 else "Unknown Genre"
                        
                        # Get artist name from database
                        artist_id = row[7] if len(row) > 7 else None
                        artist_name = get_artist_name(artist_id)
                        
                        # If artist is unknown but title contains artist info, extract it
                        album_name = "Unknown Album"
                        title_to_use = title
                        
                        # Many tracks are formatted as "Artist - Title"
                        if artist_name == "Unknown Artist" and " - " in title:
                            parts = title.split(" - ", 1)
                            artist_name = parts[0].strip()
                            title_to_use = parts[1].strip()
                        
                        # Create track dictionary
                        track = {
                            "id": track_id,
                            "title": title_to_use,
                            "artist": artist_name or "",
                            "album": album_name or "",
                            "genre": genre_name or "",
                            "duration": duration,
                            "file_path": file_path,
                            "bpm": bpm,
                            "key": key_name,
                            "rekordbox_id": track_id,  # Use the Rekordbox ID as a reference
                        }
                        
                        tracks.append(track)
                    
                    logger.info(f"Processed {len(tracks)} tracks with key and genre info")
                    return tracks
            except Exception as e:
                logger.error(f"Error with enhanced query: {e}")
                logger.info("Falling back to basic query without joins")
            
            # Use only columns we know exist (fallback)
            simplified_query = f"""
                SELECT ID, Title, Length, BPM, FolderPath, ArtistID
                FROM djmdContent
                ORDER BY ID
                {limit_clause}
            """
            
            logger.info("Executing query with verified columns")
            cursor.execute(simplified_query)
            rows = cursor.fetchall()
            
            if rows:
                logger.info(f"Successfully retrieved {len(rows)} tracks")
                
                tracks = []
                for i, row in enumerate(rows):
                    if i < 5:
                        logger.info(f"Row {i} data: {row}")
                    
                    # Basic data extraction with proper error handling
                    track_id = row[0] if len(row) > 0 else i+1
                    title = row[1] or f"Track {i+1}" if len(row) > 1 else f"Track {i+1}"
                    
                    # Process duration - critically important!
                    raw_duration = row[2] if len(row) > 2 else 0
                    logger.info(f"Raw duration value for track '{title}': {raw_duration}")
                    
                    # Convert from frames to seconds, but treat as seconds if already large enough
                    if raw_duration is not None and raw_duration > 0:
                        if raw_duration < 1000:  # Small values are likely frames
                            # Use raw duration as is (in seconds)
                            duration = float(raw_duration)
                            logger.info(f"Using raw duration as seconds: {raw_duration} seconds")
                        else:  # Larger values might already be in milliseconds
                            duration = float(raw_duration) / 1000.0
                            logger.info(f"Converting from milliseconds: {raw_duration}/1000 = {duration:.2f} seconds")
                    else:
                        duration = 0
                        logger.info(f"Invalid duration value, setting to 0")
                    
                    # Process BPM
                    bpm_raw = row[3] or 0.0 if len(row) > 3 else 0.0
                    bpm = float(bpm_raw) / 100.0 if bpm_raw else 0.0
                    
                    # Get file path
                    file_path = row[4] or "" if len(row) > 4 else ""
                    
                    # Process artist ID
                    artist_id = row[5] if len(row) > 5 else None
                    artist_name = get_artist_name(artist_id)
                    
                    # If artist is unknown but title contains artist info, extract it
                    album_name = "Unknown Album"
                    title_to_use = title
                    
                    # Many tracks are formatted as "Artist - Title"
                    if artist_name == "Unknown Artist" and " - " in title:
                        parts = title.split(" - ", 1)
                        artist_name = parts[0].strip()
                        title_to_use = parts[1].strip()
                    
                    # Create track dictionary
                    track = {
                        "id": track_id,
                        "title": title_to_use,
                        "artist": artist_name or "",
                        "album": album_name or "",
                        "genre": "Unknown Genre",
                        "duration": duration,
                        "file_path": file_path,
                        "bpm": bpm,
                        "key": "Unknown",
                        "rekordbox_id": track_id,  # Use the Rekordbox ID as a reference
                    }
                    
                    tracks.append(track)
                
                logger.info(f"Processed {len(tracks)} tracks from basic query")
                return tracks
            else:
                logger.warning("No rows found in database")
            
        except Exception as e:
            logger.error(f"Error with query: {e}")

        # Fallback to absolute minimal query if everything else fails
        try:
            logger.info("Trying minimal ID+Title query with key and genre lookups")
            
            # First get the tracks with basic info
            minimal_query = f"""
                SELECT ID, Title, Length, BPM, FolderPath, KeyID, GenreID, ArtistID
                FROM djmdContent
                ORDER BY ID
                {limit_clause if limit is not None else ""}
            """
            
            cursor.execute(minimal_query)
            rows = cursor.fetchall()
            
            if not rows:
                logger.info("No tracks retrieved, returning empty list")
                return []
            
            # Function to get key name from ID
            def get_key_name(key_id):
                try:
                    cursor.execute("SELECT ScaleName FROM djmdKey WHERE ID = ?", (key_id,))
                    result = cursor.fetchone()
                    return result[0] if result else "Unknown"
                except Exception as e:
                    logger.error(f"Error getting key name: {e}")
                    return "Unknown"
            
            # Function to get genre name from ID
            def get_genre_name(genre_id):
                try:
                    cursor.execute("SELECT Name FROM djmdGenre WHERE ID = ?", (genre_id,))
                    result = cursor.fetchone()
                    return result[0] if result else "Unknown Genre"
                except Exception as e:
                    logger.error(f"Error getting genre name: {e}")
                    return "Unknown Genre"
            
            def get_artist_name(artist_id):
                try:
                    if artist_id is None:
                        return "Unknown Artist"
                    cursor.execute("SELECT Name FROM djmdArtist WHERE ID = ?", (artist_id,))
                    result = cursor.fetchone()
                    return result[0] if result else "Unknown Artist"
                except Exception as e:
                    logger.error(f"Error getting artist name: {e}")
                    return "Unknown Artist"
            
            tracks = []
            for i, row in enumerate(rows):
                if i < 5:
                    logger.info(f"Row {i} data: {row}")
                
                # Extract basic data
                track_id = row[0] if len(row) > 0 else i+1
                title = row[1] or f"Track {i+1}" if len(row) > 1 else f"Track {i+1}"
                
                # Process duration
                raw_duration = row[2] if len(row) > 2 else 0
                
                # Convert based on value size
                if raw_duration is not None and raw_duration > 0:
                    if raw_duration < 1000:  # Likely in frames
                        duration = float(raw_duration)
                    else:  # Likely in milliseconds
                        duration = float(raw_duration) / 1000.0
                else:
                    duration = 0
                
                # Process BPM
                bpm_raw = row[3] or 0.0 if len(row) > 3 else 0.0
                bpm = float(bpm_raw) / 100.0 if bpm_raw else 0.0
                
                # Get file path
                file_path = row[4] or "" if len(row) > 4 else ""
                
                # Get names for IDs
                key_id = row[5] if len(row) > 5 else None
                key_name = get_key_name(key_id)
                
                genre_id = row[6] if len(row) > 6 else None
                genre_name = get_genre_name(genre_id)
                
                # Get artist ID and name
                artist_id = row[7] if len(row) > 7 else None
                artist_name = get_artist_name(artist_id)
                
                # Extract artist from title if possible
                title_to_use = title
                album_name = "Unknown Album"
                
                # Many tracks are formatted as "Artist - Title"
                if artist_name == "Unknown Artist" and " - " in title:
                    parts = title.split(" - ", 1)
                    artist_name = parts[0].strip()
                    title_to_use = parts[1].strip()
                
                # Create track dictionary
                track = {
                    "id": track_id,
                    "title": title_to_use,
                    "artist": artist_name or "",
                    "album": album_name or "",
                    "genre": genre_name or "",
                    "duration": float(duration),  # Keep original conversion
                    "file_path": file_path,
                    "bpm": bpm,
                    "key": key_name,
                    "rekordbox_id": track_id,  # Use the Rekordbox ID as a reference
                }
                
                tracks.append(track)
            
            logger.info(f"Processed {len(tracks)} tracks using minimal query with key and genre lookups")
            return tracks
        except Exception as e:
            logger.error(f"Error with minimal query: {e}")
            return []
    
    def close(self):
        """Close the database connection and clean up temporary files."""
        try:
            if self.conn:
                self.conn.close()
                self.conn = None
            
            if self.temp_db_path and os.path.exists(self.temp_db_path):
                try:
                    os.unlink(self.temp_db_path)
                    logger.info(f"Removed temporary database file: {self.temp_db_path}")
                except Exception as e:
                    logger.error(f"Error removing temporary database file: {e}")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")

# API Routes

@app.get("/")
def read_root():
    """Root endpoint."""
    return {
        "app": "TurntableIQ API",
        "version": "0.1.0",
        "status": "Running"
    }

@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/api/tracks")
def get_tracks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: str = Query(None),
    db: AppDatabase = Depends(get_app_db)
):
    """
    Get a list of tracks.
    
    Args:
        skip: Number of tracks to skip (for pagination)
        limit: Maximum number of tracks to return
        search: Optional search term to filter tracks
        
    Returns:
        List of tracks
    """
    tracks, total = db.get_tracks(skip, limit, search)
    return {
        "items": tracks,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@app.get("/api/tracks/{track_id}")
def get_track(track_id: int, db: AppDatabase = Depends(get_app_db)):
    """Get details of a specific track."""
    track = db.get_track(track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    return track

@app.post("/api/rekordbox/connect", response_model=ConnectionResponse)
def connect_rekordbox(request: ConnectionRequest):
    """
    Connect to a Rekordbox database.
    
    Args:
        request: Connection request containing database path and key
    
    Returns:
        Connection response indicating success or failure
    """
    db_path = request.db_path
    db_key = request.db_key
    
    logger.info(f"Attempting connection to: {db_path}")
    logger.info(f"Using key: {db_key[:5]}...")
    
    # Validate database path
    if not os.path.exists(db_path):
        return ConnectionResponse(
            success=False,
            message=f"Database file not found at: {db_path}"
        )
    
    # Validate key format
    if not db_key or len(db_key) != 64:
        logger.info(f"Key length: {len(db_key) if db_key else 0} characters")
        return ConnectionResponse(
            success=False,
            message="Invalid encryption key format. Expected 64 character hex string."
        )
    
    # Try to connect
    logger.info(f"Using key: {db_key[:5]}...")
    logger.info(f"Attempting to connect to database at {db_path}")
    
    rb_db = RekordboxDatabase(db_path, db_key)
    
    if rb_db.connect():
        # Store connection parameters in environment for later use
        os.environ["REKORDBOX_DB_PATH"] = db_path
        os.environ["REKORDBOX_DB_KEY"] = db_key
        
        return ConnectionResponse(
            success=True,
            message="Successfully connected to Rekordbox database"
        )
    else:
        return ConnectionResponse(
            success=False,
            message="Failed to connect to Rekordbox database. Check path and encryption key."
        )

@app.post("/api/rekordbox/import")
def import_rekordbox_tracks(db: AppDatabase = Depends(get_app_db)):
    """
    Import tracks from Rekordbox database into our application.
    
    Returns:
        Status message
    """
    try:
        # Get Rekordbox database path and key from environment variables
        rb_db_path = os.environ.get("REKORDBOX_DB_PATH")
        rb_db_key = os.environ.get("REKORDBOX_DB_KEY")
        
        if not rb_db_path or not rb_db_key:
            return {
                "success": False,
                "message": "Rekordbox database not connected. Please connect first."
            }
        
        # Connect to Rekordbox database
        rb_db = RekordboxDatabase(rb_db_path, rb_db_key)
        if not rb_db.connect():
            return {
                "success": False,
                "message": "Failed to connect to Rekordbox database."
            }
        
        # Extract tracks
        tracks = rb_db.extract_tracks()
        
        # Close the Rekordbox database
        rb_db.close()
        
        if not tracks:
            return {
                "success": False,
                "message": "No tracks found in Rekordbox database."
            }
        
        # Import tracks into our database
        added, updated = db.import_tracks_from_rekordbox(tracks)
        
        return {
            "success": True,
            "message": f"Successfully imported {len(tracks)} tracks from Rekordbox",
            "count": len(tracks),
            "added": added,
            "updated": updated
        }
    except Exception as e:
        logger.error(f"Failed to import tracks: {e}")
        return {
            "success": False,
            "message": f"Failed to import tracks: {str(e)}"
        }

class Playlist(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    track_count: int = 0
    is_folder: bool = False
    tracks: List[int] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

@app.get("/api/playlists")
def get_playlists(db: AppDatabase = Depends(get_app_db)):
    """Get all playlists."""
    playlists = db.get_playlists()
    return {
        "items": playlists,
        "total": len(playlists)
    }

@app.post("/api/rekordbox/import-playlists")
def import_rekordbox_playlists(db: AppDatabase = Depends(get_app_db)):
    """Import playlists from Rekordbox."""
    # Implementation similar to import_rekordbox_tracks
    return {
        "success": True,
        "message": "Playlist import not yet implemented"
    }

@app.get("/api/database/stats")
def get_database_stats(db: AppDatabase = Depends(get_app_db)):
    """Get database statistics."""
    return db.get_database_stats()

@app.post("/api/database/vacuum")
def vacuum_database(db: AppDatabase = Depends(get_app_db)):
    """Optimize the database by running VACUUM."""
    db.vacuum()
    return {
        "success": True,
        "message": "Database optimized successfully"
    }

if __name__ == "__main__":
    import uvicorn
    
    # Ensure we have a database connection
    get_app_db()
    
    # Run the server
    uvicorn.run(app, host="127.0.0.1", port=8000)