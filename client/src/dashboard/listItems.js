import * as React from 'react';
import {Link} from "react-router-dom";
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import ListSubheader from '@mui/material/ListSubheader';
import BorderColorIcon from '@mui/icons-material/BorderColor';
import HistoryIcon from '@mui/icons-material/History';
import NotesIcon from '@mui/icons-material/Notes';
import CloudDownloadIcon from '@mui/icons-material/CloudDownload';
import AssignmentIcon from '@mui/icons-material/Assignment';
import AppRegistrationIcon from '@mui/icons-material/AppRegistration';

export const mainListItems = (
  <React.Fragment>
    {/* <ListItemButton>
      <ListItemIcon>
        <DashboardIcon fontSize="large" />
      </ListItemIcon>
      <ListItemText primary="Dashboard" />
    </ListItemButton> */}
    <ListItemButton component={Link} to="/">
      <ListItemIcon>
        <NotesIcon fontSize="large" />
      </ListItemIcon>
      <ListItemText primary="Rewriting Rules" />
    </ListItemButton>
    <ListItemButton component={Link} to="/formulator">
      <ListItemIcon>
        <BorderColorIcon fontSize="large" />
      </ListItemIcon>
      <ListItemText primary="Rule Formulator" />
    </ListItemButton>
    <ListItemButton component={Link} to="/jdbc">
      <ListItemIcon>
        <CloudDownloadIcon fontSize="large" />
      </ListItemIcon>
      <ListItemText primary="JDBC Drivers" />
    </ListItemButton>
    <ListItemButton component={Link} to="/queries">
      <ListItemIcon>
        <HistoryIcon fontSize="large" />
      </ListItemIcon>
      <ListItemText primary="Query Logs" />
    </ListItemButton>
    <ListItemButton component={Link} to="/applications">
      <ListItemIcon>
        <AppRegistrationIcon fontSize="large" />
      </ListItemIcon>
      <ListItemText primary="Applications" />
    </ListItemButton>
  </React.Fragment>
);

export const secondaryListItems = (
  <React.Fragment>
    <ListSubheader component="div" inset>
      Saved reports
    </ListSubheader>
    <ListItemButton>
      <ListItemIcon>
        <AssignmentIcon />
      </ListItemIcon>
      <ListItemText primary="Current month" />
    </ListItemButton>
    <ListItemButton>
      <ListItemIcon>
        <AssignmentIcon />
      </ListItemIcon>
      <ListItemText primary="Last quarter" />
    </ListItemButton>
    <ListItemButton>
      <ListItemIcon>
        <AssignmentIcon />
      </ListItemIcon>
      <ListItemText primary="Year-end sale" />
    </ListItemButton>
  </React.Fragment>
);
