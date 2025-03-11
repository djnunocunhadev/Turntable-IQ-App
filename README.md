# Turntable-IQ

Turntable-IQ is a DJ library management system with Rekordbox integration, designed to help DJs organize, analyze, and manage their music collections.

## Features

- **Rekordbox Integration**: Connect directly to your Rekordbox database to import tracks
- **Track Management**: Organize and manage your music library with advanced metadata
- **Playlist Management**: Create and manage playlists for your DJ sets
- **Tag System**: Create hierarchical tags to organize your music collection

## Project Structure

The project is divided into two main parts:

### Backend (Python/FastAPI)

- RESTful API built with FastAPI
- SQLite database for storing application data
- Rekordbox database reader for importing tracks

### Frontend (React/Material-UI)

- Modern UI built with React and Material-UI
- Responsive design for desktop and mobile
- Dark theme for DJ-friendly usage

## Setup Instructions

### Prerequisites

- Python 3.8+
- Node.js 14+
- npm or yarn
- Rekordbox database file (master.db)

### Backend Setup

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

5. Create a `.env` file based on `.env.example` and set your Rekordbox database path and key.

6. Start the backend server:
   ```
   PYTHONPATH=. python simple_app.py
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Start the development server:
   ```
   npm start
   ```

4. The application will be available at `http://localhost:3000`

## Rekordbox Integration

To connect to your Rekordbox database:

1. Find your Rekordbox database file (usually located at `~/Library/Pioneer/rekordbox/master.db` on macOS or `C:\Users\[username]\AppData\Roaming\Pioneer\rekordbox\master.db` on Windows)
2. Use the default decryption key or provide your own if you have a custom key
3. Navigate to the Rekordbox page in the application and enter the database path and key
4. Click "Connect to Rekordbox" to establish the connection
5. Once connected, you can import your tracks into Turntable-IQ

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Pioneer DJ for creating Rekordbox
- The open-source community for providing the tools and libraries used in this project