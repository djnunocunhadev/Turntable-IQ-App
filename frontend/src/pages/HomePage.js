import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Button,
  Grid,
  Card,
  CardContent,
  CardActions,
  CardMedia,
} from '@mui/material';
import {
  LibraryMusic as LibraryMusicIcon,
  Storage as StorageIcon,
  Tag as TagIcon,
} from '@mui/icons-material';

const features = [
  {
    title: 'Track Management',
    description: 'Organize and manage your music library with advanced metadata.',
    icon: <LibraryMusicIcon fontSize="large" />,
    link: '/tracks',
    buttonText: 'View Tracks',
  },
  {
    title: 'Rekordbox Integration',
    description: 'Seamlessly connect to your Rekordbox database for real-time sync.',
    icon: <StorageIcon fontSize="large" />,
    link: '/rekordbox',
    buttonText: 'Connect Rekordbox',
  },
  {
    title: 'Tag System',
    description: 'Create hierarchical tags to organize your music collection.',
    icon: <TagIcon fontSize="large" />,
    link: '/tracks',
    buttonText: 'Manage Tags',
  },
];

function HomePage() {
  return (
    <Container maxWidth="lg">
      <Box
        sx={{
          pt: 8,
          pb: 6,
          textAlign: 'center',
        }}
      >
        <Typography
          component="h1"
          variant="h2"
          color="text.primary"
          gutterBottom
        >
          Welcome to TurntableIQ
        </Typography>
        <Typography variant="h5" color="text.secondary" paragraph>
          The next-generation DJ library management system with seamless
          Rekordbox integration, advanced music analysis, and intelligent
          organization tools.
        </Typography>
        <Box
          sx={{
            mt: 4,
            display: 'flex',
            justifyContent: 'center',
            gap: 2,
          }}
        >
          <Button
            variant="contained"
            color="primary"
            size="large"
            component={RouterLink}
            to="/tracks"
          >
            View Library
          </Button>
          <Button
            variant="outlined"
            color="primary"
            size="large"
            component={RouterLink}
            to="/rekordbox"
          >
            Connect Rekordbox
          </Button>
        </Box>
      </Box>

      <Grid container spacing={4} sx={{ mb: 8 }}>
        {features.map((feature) => (
          <Grid item key={feature.title} xs={12} sm={6} md={4}>
            <Card
              sx={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                transition: 'transform 0.2s',
                '&:hover': {
                  transform: 'translateY(-5px)',
                },
              }}
            >
              <Box
                sx={{
                  p: 2,
                  display: 'flex',
                  justifyContent: 'center',
                  color: 'primary.main',
                }}
              >
                {feature.icon}
              </Box>
              <CardContent sx={{ flexGrow: 1 }}>
                <Typography gutterBottom variant="h5" component="h2" align="center">
                  {feature.title}
                </Typography>
                <Typography align="center">{feature.description}</Typography>
              </CardContent>
              <CardActions sx={{ justifyContent: 'center', pb: 2 }}>
                <Button
                  size="small"
                  color="primary"
                  component={RouterLink}
                  to={feature.link}
                >
                  {feature.buttonText}
                </Button>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Container>
  );
}

export default HomePage;