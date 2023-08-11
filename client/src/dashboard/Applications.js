import * as React from 'react';
import axios from 'axios';
import AddIcon from '@mui/icons-material/Add';
import Button from '@mui/material/Button';
import Fab from '@mui/material/Fab';
import NiceModal from '@ebay/nice-modal-react';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Title from './Title';
import { Box } from '@mui/material';
import {userContext} from '../userContext';
import ManageApplicationModal from './ManageApplicationModal';
import ViewAssignedRules from './ViewAssignedRules';

export default function Applications() {
  // Set up a state for list of apps
  const [applications, setApplications] = React.useState([]);
  // Set up a state for providing forceUpdate function
  const [, updateState] = React.useState();
  const forceUpdate = React.useCallback(() => updateState({}), []);

  const user = React.useContext(userContext);

  // initial loading applications for the current user from server
  const listApplications = () => {
    console.log('[/listApplications] -> request:');
    console.log('  user_id: ' + user.id);
    // post listApplications request to server
    axios.post('/listApplications', { 'user_id': user.id })
        .then(function (response) {
            console.log('[/listApplications] -> response:');
            console.log(response);
            // update the state for list of applications
            setApplications(response.data);
            forceUpdate();
        })
        .catch(function (error) {
            console.log('[/listApplications] -> error:');
            console.log(error);
            forceUpdate();
        });
  };

  // call listApplications() only once after initial rendering
  React.useEffect(() => { listApplications() }, [user]);

  // handle click on view assigned rules for this app
  const viewAssignedRules = (app) => {
    NiceModal.show(ViewAssignedRules, {user_id: user.id, app: app})
    .then((res) => {
      console.log(res);
      listApplications(user);
    });
  }

  // handle click on the delete of a application
  const handleDelete = (app) => {
    // post deleteApplication request to server
    console.log(app)
    axios.post('/deleteApplication', {user_id: user.id, app: app})
    .then(function (response) {
      console.log('[/deleteApplication] -> response:');
      console.log(response);
      listApplications(user);
    })
    .catch(function (error) {
      console.log('[/deleteApplication] -> error:');
      console.log(error);
      listApplications(user);
    });
  };
  
  // handle click on add applications AND edit an application
  const manageAppModal = (app) => {
    NiceModal.show(ManageApplicationModal, {user_id: user.id, app: app})
    .then((res) => {
      console.log(res);
      listApplications(user);
    });
  };

  return (
    <React.Fragment>
      <Title>Applications</Title>
      <TableContainer sx={{ maxHeight: 500, maxWidth: 1400 }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Name</TableCell>
              <TableCell align="center">Assigned Rules</TableCell>
              <TableCell align="center">Edit</TableCell>
              <TableCell align="center">Delete</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {applications.map((app) => (
              <TableRow key={app.id}>
                <TableCell>{app.id}</TableCell>
                <TableCell>{app.name}</TableCell>
                <TableCell align="center">
                  <Button variant="outlined" color="primary" onClick={() => viewAssignedRules(app)} >View</Button>
                </TableCell>
                <TableCell align="center">
                  <Button variant="outlined" color="primary" onClick={() => manageAppModal(app)}>Edit</Button>
                </TableCell>
                <TableCell align="center">
                  <Button variant="outlined" color="error" onClick={() => handleDelete(app)}>Delete</Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <Box>
        <Fab size="small" color="primary" aria-label="add" onClick={() => manageAppModal()}>
          <AddIcon />
        </Fab>
      </Box>
    </React.Fragment>
  );
}