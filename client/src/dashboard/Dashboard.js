import * as React from 'react';
import axios from 'axios';
import Avatar from '@mui/material/Avatar';
import { styled, createTheme, ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import MuiDrawer from '@mui/material/Drawer';
import Box from '@mui/material/Box';
import MuiAppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import List from '@mui/material/List';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Badge from '@mui/material/Badge';
import Container from '@mui/material/Container';
import Grid from '@mui/material/Grid';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Link from '@mui/material/Link';
import MenuIcon from '@mui/icons-material/Menu';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import NotificationsIcon from '@mui/icons-material/Notifications';
import { mainListItems, secondaryListItems } from './listItems';
import { Routes, Route, UNSAFE_RouteContext } from "react-router-dom";
import RewritingRules from './RewritingRules';
import RuleFormulator from './RuleFormulator';
import QueryLogs from './QueryLogs';
import JDBCDrivers from './JDBCDrivers';
import GoogleIcon from '@mui/icons-material/Google';
import { googleLogout, useGoogleLogin } from '@react-oauth/google';
// user context
import {userContext} from '../userContext';

function Copyright(props) {
  return (
    <Typography variant="body2" color="text.secondary" align="center" {...props}>
      {'Copyright © '}
      <Link color="inherit" href="https://querybooster.ics.uci.edu/">
        QueryBooster
      </Link>{' '}
      {new Date().getFullYear()}
      {'.'}
    </Typography>
  );
}

const drawerWidth = 240;

const AppBar = styled(MuiAppBar, {
  shouldForwardProp: (prop) => prop !== 'open',
})(({ theme, open }) => ({
  zIndex: theme.zIndex.drawer + 1,
  transition: theme.transitions.create(['width', 'margin'], {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.leavingScreen,
  }),
  ...(open && {
    marginLeft: drawerWidth,
    width: `calc(100% - ${drawerWidth}px)`,
    transition: theme.transitions.create(['width', 'margin'], {
      easing: theme.transitions.easing.sharp,
      duration: theme.transitions.duration.enteringScreen,
    }),
  }),
}));

const Drawer = styled(MuiDrawer, { shouldForwardProp: (prop) => prop !== 'open' })(
  ({ theme, open }) => ({
    '& .MuiDrawer-paper': {
      position: 'relative',
      whiteSpace: 'nowrap',
      width: drawerWidth,
      transition: theme.transitions.create('width', {
        easing: theme.transitions.easing.sharp,
        duration: theme.transitions.duration.enteringScreen,
      }),
      boxSizing: 'border-box',
      ...(!open && {
        overflowX: 'hidden',
        transition: theme.transitions.create('width', {
          easing: theme.transitions.easing.sharp,
          duration: theme.transitions.duration.leavingScreen,
        }),
        width: theme.spacing(7),
        [theme.breakpoints.up('sm')]: {
          width: theme.spacing(9),
        },
      }),
    },
  }),
);

const mdTheme = createTheme();

function DashboardContent() {
  const [user, setUser] = React.useState({});
  const [open, setOpen] = React.useState(true);
  const toggleDrawer = () => {
    setOpen(!open);
  };

  // Set up a state for providing forceUpdate function
  const [, updateState] = React.useState();
  const forceUpdate = React.useCallback(() => updateState({}), []);

  const login = useGoogleLogin({
    onSuccess: (res) => {
      console.log('[Google Login Success] res: ', res);
      axios.get(`https://www.googleapis.com/oauth2/v1/userinfo?access_token=${res.access_token}`, {
                    headers: {
                        Authorization: `Bearer ${res.access_token}`,
                        Accept: 'application/json'
                    }
                })
                .then((res) => {
                    console.log('[Get Google Profile Success] res.data: ', res.data);
                    // post createUser request to server
                    axios.post('/createUser', {id: res.data.id, email: res.data.email})
                    .then(function (response) {
                      console.log('[/createUser] -> response:');
                      console.log(response);
                    })
                    .catch(function (error) {
                      console.log('[/createUser] -> error:');
                      console.log(error);
                    });
                    setUser(res.data);
                    forceUpdate();
                })
                .catch((err) => console.log(err));
    },
    onError: (error) => console.log('[Google Login Error] error: ', error)
  });

  const logout = () => {
    googleLogout();
    setUser({});
    forceUpdate();
};

  React.useEffect(() => {}, []);

  return (
    <userContext.Provider value={user}>
      <ThemeProvider theme={mdTheme}>
        <Box sx={{ display: 'flex' }}>
          <CssBaseline />
          <AppBar position="absolute" open={open}>
            <Toolbar
              sx={{
                pr: '24px', // keep right padding when drawer closed
              }}
            >
              <IconButton
                edge="start"
                color="inherit"
                aria-label="open drawer"
                onClick={toggleDrawer}
                sx={{
                  marginRight: '36px',
                  ...(open && { display: 'none' }),
                }}
              >
                <MenuIcon />
              </IconButton>
              <Typography
                component="h1"
                variant="h6"
                color="inherit"
                noWrap
                sx={{ flexGrow: 1 }}
              >
                QueryBooster
              </Typography>
              {user.email ? (
                <Stack direction="row" spacing={2}>
                  <div>Welcome, {user.name}! </div>
                  <Avatar referrerpolicy="no-referrer" alt={user.name} src={user.picture} />
                  <Button
                  color="secondary"
                  variant="contained"
                  onClick={logout}
                  >
                    Sign out
                  </Button>
                </Stack>
                ) : (
                <Button 
                  color="secondary" 
                  variant="contained" 
                  startIcon={<GoogleIcon />}
                  onClick={() => login()}
                >
                  Sign in with Google
                </Button>
              )}
              {/* <IconButton color="inherit">
                <Badge badgeContent={4} color="secondary">
                  <NotificationsIcon />
                </Badge>
              </IconButton> */}
            </Toolbar>
          </AppBar>
          <Drawer variant="permanent" open={open}>
            <Toolbar
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'flex-end',
                px: [1],
              }}
            >
              <IconButton onClick={toggleDrawer}>
                <ChevronLeftIcon />
              </IconButton>
            </Toolbar>
            <Divider />
            <List component="nav">
              {mainListItems}
              {/* <Divider sx={{ my: 1 }} />
              {secondaryListItems} */}
            </List>
          </Drawer>
          <Box
            component="main"
            sx={{
              backgroundColor: (theme) =>
                theme.palette.mode === 'light'
                  ? theme.palette.grey[100]
                  : theme.palette.grey[900],
              flexGrow: 1,
              height: '100vh',
              overflow: 'auto',
            }}
          >
            <Toolbar />
            <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
              <Grid container spacing={3}>
                {/* Rewriting Rules */}
                <Grid item xs={12}>
                  <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column' }}>
                    <Routes>
                      {/* <RewritingRules /> */}
                      <Route exact path="/" element={<RewritingRules />} />
                      <Route path="/formulator" element={<RuleFormulator />} />
                      <Route path="/jdbc" element={<JDBCDrivers />} />
                      <Route path="/queries" element={<QueryLogs />} />
                    </Routes>
                  </Paper>
                </Grid>
              </Grid>
              <Copyright sx={{ pt: 4 }} />
            </Container>
          </Box>
        </Box>
      </ThemeProvider>
    </userContext.Provider>
  );
}

export default function Dashboard() {
  return <DashboardContent />;
}
