import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Box,
  Button,
  TextField,
  Card,
  CardContent,
  CardActions,
  Alert,
  CircularProgress,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Paper,
  Stepper,
  Step,
  StepLabel,
} from '@mui/material';
import {
  Link as LinkIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  CloudDownload as CloudDownloadIcon,
} from '@mui/icons-material';
import axios from 'axios';

// API base URL - make sure this matches your backend server
const API_BASE_URL = 'http://127.0.0.1:8000';

// The known Rekordbox decryption key - updated to match the 64-character format
const DEFAULT_DB_KEY = '402fd482c38817c35ffa8ffb8c7d93143b749e7d315df7a81732a1ff43608497';

function RekordboxPage() {
  const [dbPath, setDbPath] = useState('/Users/nunocunha/Desktop/Cursor APPS/ttdb/master.db');
  const [dbKey, setDbKey] = useState(DEFAULT_DB_KEY);
  const [loading, setLoading] = useState(false);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(null);
  const [importStatus, setImportStatus] = useState({
    inProgress: false,
    completed: false,
    count: 0,
    error: null,
  });
  const [activeStep, setActiveStep] = useState(0);

  const steps = ['Connect to Rekordbox', 'Import Tracks', 'Analyze Music'];

  // Check connection on mount (simulated)
  useEffect(() => {
    const checkInitialConnection = async () => {
      try {
        // First check if the backend is running
        const response = await axios.get(`${API_BASE_URL}/api/health`);
        
        if (response.data.status === 'healthy') {
          console.log('Backend is running');
          
          // The connection itself will still need to be initiated manually
          // but at least we know the backend is available
        }
      } catch (error) {
        console.log('Backend not available yet:', error);
      }
    };
    
    checkInitialConnection();
  }, []);

  const handleDbPathChange = (event) => {
    setDbPath(event.target.value);
  };

  const handleDbKeyChange = (event) => {
    setDbKey(event.target.value);
  };

  const handleConnect = async () => {
    if (!dbPath) {
      setError('Please provide the database path');
      return;
    }
    
    // Make sure key is exactly 64 characters
    // This is a temporary fix to override server validation
    if (dbKey.length !== 64) {
      // If key is longer than 64 characters, truncate it
      if (dbKey.length > 64) {
        setDbKey(dbKey.substring(0, 64));
      } else {
        // If key is shorter, show error
        setError('Invalid database key format. Key should be 64 hex characters.');
        return;
      }
    }
    
    // Add client-side validation for key format
    if (!/^[0-9a-f]+$/i.test(dbKey)) {
      setError('Invalid database key format. Key should be 64 hex characters.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      console.log('Connecting to Rekordbox with path:', dbPath);
      console.log('Using key:', dbKey.substring(0, 5) + '...');
      console.log('Sending request to:', `${API_BASE_URL}/api/rekordbox/connect`);
      
      // Make sure we're sending the right key length
      const keyToSend = dbKey.length > 64 ? dbKey.substring(0, 64) : dbKey;
      
      // Call the backend API to test connection with the provided credentials
      const response = await axios.post(`${API_BASE_URL}/api/rekordbox/connect`, {
        db_path: dbPath,
        db_key: keyToSend
      });
      
      console.log('Connection response:', response.data);
      
      if (response.data.success) {
        console.log('Connection successful');
        setConnected(true);
        setActiveStep(1);
      } else {
        // Even if the response is a "success: false", we still have a message
        // Instead of throwing an error, display the detailed message
        setError(response.data.message || 'Failed to connect to Rekordbox database');
      }
    } catch (err) {
      console.error('Connection error:', err);
      // Display detailed error messages from the backend
      const errorMessage = 
        err.response?.data?.detail || // Specific FastAPI error
        err.response?.data?.message || // Other message formats
        err.message ||
        'Failed to connect to Rekordbox database. Please check your credentials.';
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleImportTracks = async () => {
    setImportStatus({
      inProgress: true,
      completed: false,
      count: 0,
      error: null,
    });

    try {
      // Call the backend API to import tracks
      const response = await axios.post(`${API_BASE_URL}/api/rekordbox/import`);
      
      // Updated to handle the correct response format
      if (response.data && response.data.count !== undefined) {
        setImportStatus({
          inProgress: false,
          completed: true,
          count: response.data.count,
          added: response.data.added,
          updated: response.data.updated,
          error: null,
        });
        setActiveStep(2);
      } else {
        // Handle unexpected response format
        throw new Error('Unexpected response format. Expected track import status information.');
      }
    } catch (err) {
      console.error('Import error:', err);
      // Display detailed error messages from the backend
      const errorMessage = 
        err.response?.data?.detail || // Specific FastAPI error
        err.response?.data?.message || // Other message formats
        err.message ||
        'Failed to import tracks. Please try again.';
      
      setImportStatus({
        inProgress: false,
        completed: false,
        count: 0,
        error: errorMessage,
      });
    }
  };
  
  const handleAnalyzeTracks = async () => {
    alert('This will analyze all tracks to extract audio features like BPM, key, and energy levels. This feature is coming soon!');
  };

  return (
    <Container maxWidth="md">
      <Box sx={{ pt: 4, pb: 6 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Rekordbox Integration
        </Typography>
        <Typography variant="body1" color="text.secondary" paragraph>
          Connect to your Rekordbox database to import and synchronize your tracks.
          This integration is non-destructive and will not modify your Rekordbox data.
        </Typography>

        <Box sx={{ my: 4 }}>
          <Stepper activeStep={activeStep} alternativeLabel>
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>
        </Box>

        <Paper sx={{ p: 3, mb: 4 }}>
          <Typography variant="h6" gutterBottom>
            1. Connect to Rekordbox Database
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            Provide the path to your Rekordbox master.db file and the decryption key.
          </Typography>

          <Box sx={{ mt: 2 }}>
            <TextField
              fullWidth
              label="Rekordbox Database Path"
              variant="outlined"
              placeholder="/path/to/rekordbox/master.db"
              value={dbPath}
              onChange={handleDbPathChange}
              margin="normal"
              disabled={connected}
              helperText="Example: /Users/username/Library/Pioneer/rekordbox/master.db"
            />
            <TextField
              fullWidth
              label="Database Key"
              variant="outlined"
              type="password"
              value={dbKey}
              onChange={handleDbKeyChange}
              margin="normal"
              disabled={connected}
              helperText={`The key should be 64 hexadecimal characters (current length: ${dbKey.length})`}
              error={dbKey.length !== 64}
            />

            {error && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {error}
              </Alert>
            )}

            {connected ? (
              <Alert severity="success" sx={{ mt: 2 }}>
                Successfully connected to Rekordbox database
              </Alert>
            ) : (
              <Box>
                <Button
                  variant="contained"
                  color="primary"
                  onClick={handleConnect}
                  disabled={loading}
                  startIcon={loading ? <CircularProgress size={20} /> : <LinkIcon />}
                  sx={{ mt: 2 }}
                >
                  {loading ? 'Connecting...' : 'Connect to Rekordbox'}
                </Button>
                <Typography variant="caption" display="block" sx={{ mt: 1, color: 'text.secondary' }}>
                  Using key format: 64 characters (previously required 96 characters)
                </Typography>
              </Box>
            )}
          </Box>
        </Paper>

        <Paper sx={{ p: 3, mb: 4 }}>
          <Typography variant="h6" gutterBottom>
            2. Import Tracks
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            Import your tracks from Rekordbox into TurntableIQ.
          </Typography>

          <Box sx={{ mt: 2 }}>
            {importStatus.completed ? (
              <Alert severity="success" sx={{ mt: 2 }}>
                Successfully imported {importStatus.count} tracks from Rekordbox
                {(importStatus.added !== undefined || importStatus.updated !== undefined) && (
                  <span> ({importStatus.added || 0} new, {importStatus.updated || 0} updated)</span>
                )}
              </Alert>
            ) : importStatus.error ? (
              <Alert severity="error" sx={{ mt: 2 }}>
                {importStatus.error}
              </Alert>
            ) : (
              <Button
                variant="contained"
                color="primary"
                onClick={handleImportTracks}
                disabled={!connected || importStatus.inProgress}
                startIcon={
                  importStatus.inProgress ? (
                    <CircularProgress size={20} />
                  ) : (
                    <CloudDownloadIcon />
                  )
                }
                sx={{ mt: 2 }}
              >
                {importStatus.inProgress ? 'Importing...' : 'Import Tracks'}
              </Button>
            )}
          </Box>
        </Paper>

        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            3. Analyze Music
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            Run advanced analysis on your imported tracks to extract musical features.
          </Typography>

          <Box sx={{ mt: 2 }}>
            <Button
              variant="contained"
              color="primary"
              disabled={!importStatus.completed}
              sx={{ mt: 2 }}
              onClick={handleAnalyzeTracks}
            >
              Start Analysis
            </Button>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
}

export default RekordboxPage;