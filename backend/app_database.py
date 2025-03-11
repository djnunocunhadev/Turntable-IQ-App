#!/usr/bin/env python3
"""
Database module for the TurntableIQ application.
This module handles all database operations for the application's own database,
separate from the Rekordbox database.
"""

import os
import sqlite3
import logging
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'library.db')

# Thread-local storage for database connections
thread_local = threading.local()

class AppDatabase:
    """Class to handle all database operations for the application."""
    
    def __init__(self, db_path=DEFAULT_DB_PATH):
        """Initialize the database connection."""
        self.db_path = db_path
        
    def _get_connection(self):
        """Get a thread-local database connection."""
        if not hasattr(thread_local, 'connection') or thread_local.connection is None:
            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Connect to the database
            thread_local.connection = sqlite3.connect(self.db_path)
            thread_local.connection.row_factory = sqlite3.Row  # Return rows as dictionaries
            
            # Initialize the database schema
            self._initialize_schema()
            
        return thread_local.connection
    
    def _get_cursor(self):
        """Get a cursor from the thread-local connection."""
        connection = self._get_connection()
        if not hasattr(thread_local, 'cursor') or thread_local.cursor is None:
            thread_local.cursor = connection.cursor()
        return thread_local.cursor
    
    def connect(self) -> bool:
        """Connect to the database."""
        try:
            # Get a connection to ensure it's initialized
            self._get_connection()
            logger.info(f"Connected to application database at {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"Error connecting to application database: {e}")
            return False
    
    def _initialize_schema(self):
        """Initialize the database schema if it doesn't exist."""
        try:
            # Create tracks table
            self._get_cursor().execute('''
                CREATE TABLE IF NOT EXISTS tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    artist TEXT,
                    album TEXT,
                    genre TEXT,
                    duration REAL,
                    file_path TEXT,
                    bpm REAL,
                    key TEXT,
                    energy REAL,
                    rekordbox_id INTEGER,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            
            # Create playlists table
            self._get_cursor().execute('''
                CREATE TABLE IF NOT EXISTS playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    parent_id INTEGER,
                    is_folder BOOLEAN DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (parent_id) REFERENCES playlists (id)
                )
            ''')
            
            # Create playlist_tracks table (many-to-many relationship)
            self._get_cursor().execute('''
                CREATE TABLE IF NOT EXISTS playlist_tracks (
                    playlist_id INTEGER,
                    track_id INTEGER,
                    position INTEGER,
                    PRIMARY KEY (playlist_id, track_id),
                    FOREIGN KEY (playlist_id) REFERENCES playlists (id),
                    FOREIGN KEY (track_id) REFERENCES tracks (id)
                )
            ''')
            
            # Create tags table
            self._get_cursor().execute('''
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                )
            ''')
            
            # Create track_tags table (many-to-many relationship)
            self._get_cursor().execute('''
                CREATE TABLE IF NOT EXISTS track_tags (
                    track_id INTEGER,
                    tag_id INTEGER,
                    PRIMARY KEY (track_id, tag_id),
                    FOREIGN KEY (track_id) REFERENCES tracks (id),
                    FOREIGN KEY (tag_id) REFERENCES tags (id)
                )
            ''')
            
            # Create indexes for performance
            self._get_cursor().execute('CREATE INDEX IF NOT EXISTS idx_tracks_rekordbox_id ON tracks (rekordbox_id)')
            self._get_cursor().execute('CREATE INDEX IF NOT EXISTS idx_tracks_title ON tracks (title)')
            self._get_cursor().execute('CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks (artist)')
            
            self._get_connection().commit()
            logger.info("Database schema initialized")
        except Exception as e:
            logger.error(f"Error initializing database schema: {e}")
            raise
    
    def close(self):
        """Close the database connection."""
        if self._get_connection():
            self._get_connection().close()
            logger.info("Database connection closed")
    
    # Track operations
    
    def add_track(self, track_data: Dict[str, Any]) -> int:
        """Add a track to the database."""
        try:
            # Make sure required fields are present
            if "title" not in track_data:
                raise ValueError("Track title is required")
            
            # Set created_at and updated_at timestamps
            now = datetime.now().isoformat()
            track_data["created_at"] = now
            track_data["updated_at"] = now
            
            # Check if track with same rekordbox_id already exists
            existing_track_id = None
            if "rekordbox_id" in track_data and track_data["rekordbox_id"]:
                query = "SELECT id FROM tracks WHERE rekordbox_id = ?"
                self._get_cursor().execute(query, (track_data["rekordbox_id"],))
                result = self._get_cursor().fetchone()
                if result:
                    existing_track_id = result[0]
            
            if existing_track_id:
                # Update existing track
                return self.update_track(existing_track_id, track_data)
            else:
                # Insert new track
                columns = ", ".join(track_data.keys())
                placeholders = ", ".join(["?"] * len(track_data))
                query = f"INSERT INTO tracks ({columns}) VALUES ({placeholders})"
                
                values = list(track_data.values())
                
                self._get_cursor().execute(query, values)
                self._get_connection().commit()
                
                # Get the ID of the inserted track
                track_id = self._get_cursor().lastrowid
                logger.info(f"Added track {track_id}")
                
                return track_id
        except Exception as e:
            # Only rollback if we have a valid connection
            if self._get_connection() is not None:
                self._get_connection().rollback()
            logger.error(f"Error adding track: {e}")
            raise
    
    def update_track(self, track_id: int, track_data: Dict[str, Any]) -> int:
        """
        Update a track in the database.
        
        Args:
            track_id: The ID of the track to update
            track_data: Dictionary containing track data to update
            
        Returns:
            The ID of the updated track
        """
        try:
            # Set updated_at timestamp
            track_data['updated_at'] = datetime.now().isoformat()
            
            # Build the update query
            set_clause = ', '.join([f'{key} = ?' for key in track_data.keys()])
            query = f'UPDATE tracks SET {set_clause} WHERE id = ?'
            
            # Execute the query
            self._get_cursor().execute(query, list(track_data.values()) + [track_id])
            self._get_connection().commit()
            
            logger.info(f"Updated track {track_id}")
            return track_id
        except Exception as e:
            self._get_connection().rollback()
            logger.error(f"Error updating track: {e}")
            raise
    
    def get_track(self, track_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a track from the database.
        
        Args:
            track_id: The ID of the track to get
            
        Returns:
            Dictionary containing track data, or None if not found
        """
        try:
            self._get_cursor().execute('SELECT * FROM tracks WHERE id = ?', (track_id,))
            track = self._get_cursor().fetchone()
            
            if track:
                # Convert to dictionary
                track_dict = dict(track)
                
                # Get tags for this track
                self._get_cursor().execute('''
                    SELECT t.id, t.name 
                    FROM tags t 
                    JOIN track_tags tt ON t.id = tt.tag_id 
                    WHERE tt.track_id = ?
                ''', (track_id,))
                tags = [{'id': row['id'], 'name': row['name']} for row in self._get_cursor().fetchall()]
                track_dict['tags'] = tags
                
                return track_dict
            return None
        except Exception as e:
            logger.error(f"Error getting track {track_id}: {e}")
            return None
    
    def get_tracks(self, skip: int = 0, limit: int = 100, search: Optional[str] = None) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get tracks from the database with pagination and optional search.
        
        Args:
            skip: Number of tracks to skip
            limit: Maximum number of tracks to return
            search: Optional search term to filter tracks
            
        Returns:
            Tuple of (list of track dictionaries, total count)
        """
        try:
            # Build the query
            query = 'SELECT * FROM tracks'
            count_query = 'SELECT COUNT(*) FROM tracks'
            params = []
            
            # Add search condition if provided
            if search:
                search_term = f'%{search}%'
                query += ''' WHERE (
                    title LIKE ? OR 
                    artist LIKE ? OR 
                    album LIKE ? OR 
                    genre LIKE ?
                )'''
                count_query += ''' WHERE (
                    title LIKE ? OR 
                    artist LIKE ? OR 
                    album LIKE ? OR 
                    genre LIKE ?
                )'''
                params.extend([search_term, search_term, search_term, search_term])
            
            # Add pagination
            query += ' ORDER BY id LIMIT ? OFFSET ?'
            params.extend([limit, skip])
            
            # Get total count
            self._get_cursor().execute(count_query, params[:4] if search else [])
            total_count = self._get_cursor().fetchone()[0]
            
            # Get tracks
            self._get_cursor().execute(query, params)
            tracks = [dict(row) for row in self._get_cursor().fetchall()]
            
            # Get tags for each track
            for track in tracks:
                self._get_cursor().execute('''
                    SELECT t.id, t.name 
                    FROM tags t 
                    JOIN track_tags tt ON t.id = tt.tag_id 
                    WHERE tt.track_id = ?
                ''', (track['id'],))
                tags = [{'id': row['id'], 'name': row['name']} for row in self._get_cursor().fetchall()]
                track['tags'] = tags
            
            logger.info(f"Retrieved {len(tracks)} tracks (skip={skip}, limit={limit}, total={total_count})")
            return tracks, total_count
        except Exception as e:
            logger.error(f"Error getting tracks: {e}")
            return [], 0
    
    def delete_track(self, track_id: int) -> bool:
        """
        Delete a track from the database.
        
        Args:
            track_id: The ID of the track to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete from track_tags first (foreign key constraint)
            self._get_cursor().execute('DELETE FROM track_tags WHERE track_id = ?', (track_id,))
            
            # Delete from playlist_tracks (foreign key constraint)
            self._get_cursor().execute('DELETE FROM playlist_tracks WHERE track_id = ?', (track_id,))
            
            # Delete the track
            self._get_cursor().execute('DELETE FROM tracks WHERE id = ?', (track_id,))
            self._get_connection().commit()
            
            logger.info(f"Deleted track {track_id}")
            return True
        except Exception as e:
            self._get_connection().rollback()
            logger.error(f"Error deleting track {track_id}: {e}")
            return False
    
    def import_tracks_from_rekordbox(self, rekordbox_tracks: List[Dict[str, Any]]) -> Tuple[int, int]:
        """Import tracks from Rekordbox."""
        added = 0
        updated = 0
        
        try:
            # Ensure we have a connection
            connection = self._get_connection()
            cursor = self._get_cursor()
            
            # Start a transaction
            connection.execute('BEGIN TRANSACTION')
            
            # Get existing rekordbox_ids for faster lookup
            cursor.execute('SELECT id, rekordbox_id FROM tracks WHERE rekordbox_id IS NOT NULL')
            existing_tracks = {row['rekordbox_id']: row['id'] for row in cursor.fetchall()}
            
            for track in rekordbox_tracks:
                # Skip tracks without a rekordbox_id
                if 'rekordbox_id' not in track or not track['rekordbox_id']:
                    continue
                
                # Remove tags field as it's not a column in the tracks table
                track_data = track.copy()
                if 'tags' in track_data:
                    del track_data['tags']
                
                # Check if track already exists
                if track['rekordbox_id'] in existing_tracks:
                    # Update existing track
                    self.update_track(existing_tracks[track['rekordbox_id']], track_data)
                    updated += 1
                else:
                    # Add new track
                    self.add_track(track_data)
                    added += 1
            
            # Commit the transaction
            connection.commit()
            logger.info(f"Imported {added} new tracks and updated {updated} existing tracks from Rekordbox")
            return added, updated
        except Exception as e:
            # Only rollback if we have a valid connection
            connection = getattr(thread_local, 'connection', None)
            if connection is not None:
                connection.rollback()
            logger.error(f"Error importing tracks from Rekordbox: {e}")
            raise
    
    # Playlist operations
    
    def add_playlist(self, playlist_data: Dict[str, Any]) -> int:
        """
        Add a playlist to the database.
        
        Args:
            playlist_data: Dictionary containing playlist data
            
        Returns:
            The ID of the newly inserted playlist
        """
        try:
            # Extract tracks from playlist_data if present
            tracks = playlist_data.pop('tracks', []) if 'tracks' in playlist_data else []
            
            # Set timestamps if not provided
            now = datetime.now().isoformat()
            if 'created_at' not in playlist_data:
                playlist_data['created_at'] = now
            if 'updated_at' not in playlist_data:
                playlist_data['updated_at'] = now
            
            # Insert the playlist
            columns = ', '.join(playlist_data.keys())
            placeholders = ', '.join(['?' for _ in playlist_data])
            query = f'INSERT INTO playlists ({columns}) VALUES ({placeholders})'
            
            self._get_cursor().execute(query, list(playlist_data.values()))
            playlist_id = self._get_cursor().lastrowid
            
            # Add tracks to the playlist
            if tracks:
                self._add_tracks_to_playlist(playlist_id, tracks)
            
            self._get_connection().commit()
            logger.info(f"Added playlist {playlist_id}: {playlist_data.get('name', 'Unknown')}")
            return playlist_id
        except Exception as e:
            self._get_connection().rollback()
            logger.error(f"Error adding playlist: {e}")
            raise
    
    def _add_tracks_to_playlist(self, playlist_id: int, track_ids: List[int]):
        """Add tracks to a playlist."""
        for position, track_id in enumerate(track_ids):
            self._get_cursor().execute(
                'INSERT INTO playlist_tracks (playlist_id, track_id, position) VALUES (?, ?, ?)',
                (playlist_id, track_id, position)
            )
    
    def get_playlists(self) -> List[Dict[str, Any]]:
        """
        Get all playlists from the database.
        
        Returns:
            List of playlist dictionaries
        """
        try:
            self._get_cursor().execute('SELECT * FROM playlists ORDER BY name')
            playlists = [dict(row) for row in self._get_cursor().fetchall()]
            
            # Get track count for each playlist
            for playlist in playlists:
                self._get_cursor().execute(
                    'SELECT COUNT(*) FROM playlist_tracks WHERE playlist_id = ?', 
                    (playlist['id'],)
                )
                playlist['track_count'] = self._get_cursor().fetchone()[0]
                
                # Get track IDs for this playlist
                self._get_cursor().execute(
                    'SELECT track_id FROM playlist_tracks WHERE playlist_id = ? ORDER BY position',
                    (playlist['id'],)
                )
                playlist['tracks'] = [row[0] for row in self._get_cursor().fetchall()]
            
            logger.info(f"Retrieved {len(playlists)} playlists")
            return playlists
        except Exception as e:
            logger.error(f"Error getting playlists: {e}")
            return []
    
    def import_playlists_from_rekordbox(self, rekordbox_playlists: List[Dict[str, Any]]) -> int:
        """
        Import playlists from Rekordbox into the application database.
        
        Args:
            rekordbox_playlists: List of playlist dictionaries from Rekordbox
            
        Returns:
            Number of playlists imported
        """
        imported = 0
        
        try:
            # Start a transaction
            self._get_connection().execute('BEGIN TRANSACTION')
            
            # Get mapping of rekordbox_id to local track_id
            self._get_cursor().execute('SELECT id, rekordbox_id FROM tracks WHERE rekordbox_id IS NOT NULL')
            rekordbox_to_local = {row['rekordbox_id']: row['id'] for row in self._get_cursor().fetchall()}
            
            for playlist in rekordbox_playlists:
                # Map rekordbox track IDs to local track IDs
                if 'tracks' in playlist:
                    local_tracks = []
                    for rb_track_id in playlist['tracks']:
                        if rb_track_id in rekordbox_to_local:
                            local_tracks.append(rekordbox_to_local[rb_track_id])
                    
                    playlist['tracks'] = local_tracks
                
                # Add the playlist
                self.add_playlist(playlist)
                imported += 1
            
            # Commit the transaction
            self._get_connection().commit()
            logger.info(f"Imported {imported} playlists from Rekordbox")
            return imported
        except Exception as e:
            self._get_connection().rollback()
            logger.error(f"Error importing playlists from Rekordbox: {e}")
            raise
    
    # Tag operations
    
    def add_tag(self, name: str) -> int:
        """
        Add a tag to the database.
        
        Args:
            name: The name of the tag
            
        Returns:
            The ID of the newly inserted tag
        """
        try:
            # Check if tag already exists
            self._get_cursor().execute('SELECT id FROM tags WHERE name = ?', (name,))
            existing = self._get_cursor().fetchone()
            if existing:
                return existing['id']
            
            # Insert the tag
            self._get_cursor().execute('INSERT INTO tags (name) VALUES (?)', (name,))
            self._get_connection().commit()
            
            tag_id = self._get_cursor().lastrowid
            logger.info(f"Added tag {tag_id}: {name}")
            return tag_id
        except Exception as e:
            self._get_connection().rollback()
            logger.error(f"Error adding tag: {e}")
            raise
    
    def add_tag_to_track(self, track_id: int, tag_id: int) -> bool:
        """
        Add a tag to a track.
        
        Args:
            track_id: The ID of the track
            tag_id: The ID of the tag
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if association already exists
            self._get_cursor().execute(
                'SELECT 1 FROM track_tags WHERE track_id = ? AND tag_id = ?', 
                (track_id, tag_id)
            )
            if self._get_cursor().fetchone():
                return True
            
            # Add the association
            self._get_cursor().execute(
                'INSERT INTO track_tags (track_id, tag_id) VALUES (?, ?)',
                (track_id, tag_id)
            )
            self._get_connection().commit()
            
            logger.info(f"Added tag {tag_id} to track {track_id}")
            return True
        except Exception as e:
            self._get_connection().rollback()
            logger.error(f"Error adding tag to track: {e}")
            return False
    
    def get_tags(self) -> List[Dict[str, Any]]:
        """
        Get all tags from the database.
        
        Returns:
            List of tag dictionaries
        """
        try:
            self._get_cursor().execute('SELECT id, name FROM tags ORDER BY name')
            tags = [dict(row) for row in self._get_cursor().fetchall()]
            
            logger.info(f"Retrieved {len(tags)} tags")
            return tags
        except Exception as e:
            logger.error(f"Error getting tags: {e}")
            return []
    
    # Database maintenance
    
    def vacuum(self):
        """Optimize the database by running VACUUM."""
        try:
            self._get_cursor().execute('VACUUM')
            logger.info("Database optimized with VACUUM")
        except Exception as e:
            logger.error(f"Error optimizing database: {e}")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the database.
        
        Returns:
            Dictionary containing database statistics
        """
        stats = {}
        
        try:
            # Get track count
            self._get_cursor().execute('SELECT COUNT(*) FROM tracks')
            stats['track_count'] = self._get_cursor().fetchone()[0]
            
            # Get playlist count
            self._get_cursor().execute('SELECT COUNT(*) FROM playlists')
            stats['playlist_count'] = self._get_cursor().fetchone()[0]
            
            # Get tag count
            self._get_cursor().execute('SELECT COUNT(*) FROM tags')
            stats['tag_count'] = self._get_cursor().fetchone()[0]
            
            # Get database size
            stats['database_size'] = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            
            logger.info(f"Database stats: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}