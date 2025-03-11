# Turntable IQ

A powerful music library management tool for DJs that integrates with Rekordbox.

## Features

- **Rekordbox Integration**: Import tracks and playlists directly from your Rekordbox database
- **Track Management**: Browse, search, and organize your music collection
- **User-friendly Interface**: Modern and intuitive UI for easy navigation
- **Performance Optimized**: Fast and responsive, even with large libraries

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React.js with Material UI
- **Database**: SQLite with SQLCipher support for encrypted Rekordbox databases

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js 14+
- npm 6+
- Rekordbox database file (optional)

### Installation

#### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the backend server:
   ```bash
   PYTHONPATH=. python simple_app.py
   ```

#### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install JavaScript dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm start
   ```

4. Open your browser and visit:
   ```
   http://localhost:3000
   ```

## Connecting to Rekordbox

1. Find your Rekordbox database file (usually named `master.db`)
2. Launch the application and use the connection dialog to point to your database
3. Use the provided encryption key or input your own if you've modified it
4. Once connected, you can import tracks and playlists from Rekordbox

## Development

To contribute or customize:

- Backend API is available at `http://localhost:8000`
- Frontend development server runs at `http://localhost:3000`
- API documentation is available at `http://localhost:8000/docs`

## License

[MIT License](LICENSE)