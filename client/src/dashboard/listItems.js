import * as React from 'react';
import {Link} from "react-router-dom";
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import ListSubheader from '@mui/material/ListSubheader';
import DashboardIcon from '@mui/icons-material/Dashboard';
import NotesIcon from '@mui/icons-material/Notes';
import CloudDownloadIcon from '@mui/icons-material/CloudDownload';
import AssignmentIcon from '@mui/icons-material/Assignment';

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
    <ListItemButton component={Link} to="/jdbc">
      <ListItemIcon>
        <CloudDownloadIcon fontSize="large" />
      </ListItemIcon>
      <ListItemText primary="JDBC Drivers" />
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
