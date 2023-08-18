import * as React from 'react';
import axios from 'axios';
import Dialog from '@mui/material/Dialog';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import NiceModal, { useModal } from '@ebay/nice-modal-react';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import SyntaxHighlighter from 'react-syntax-highlighter';
import { vs } from 'react-syntax-highlighter/dist/esm/styles/hljs';
import {userContext} from '../userContext';


const ViewAssignedRules = NiceModal.create(({user_id, app}) => {
  const modal = useModal();
  // Set up a state for list of rules
  const [rules, setRules] = React.useState([]);

  // Set up a state for providing forceUpdate function
  const [, updateState] = React.useState();
  const forceUpdate = React.useCallback(() => updateState({}), []);

  const user = React.useContext(userContext);

  // initial loading rules from server
  const listRules = () => {
    console.log('[/listRules] -> request:');
    console.log('  user_id: ' + user_id);
    // post listRules request to server
    axios.post('/listRules', {'user_id': user_id, 'app_id': app.id})
      .then(function (response) {
        console.log('[/listRules] -> response:');
        console.log(response);
        // update the state for list of rules
        setRules(response.data);
        forceUpdate();
      })
      .catch(function (error) {
        console.log('[/listRules] -> error:');
        console.log(error);
      });
  };

  // call listRules() only once after initial rendering
  React.useEffect(() => {listRules()}, [user_id, app.id]);

    return (
        <Dialog
          open={modal.visible}
          onClose={() => modal.hide()}
          TransitionProps={{
            onExited: () => modal.remove(),
          }}
          fullWidth
          maxWidth={'lg'}
        >
          <DialogTitle>Assigned Rules for {app.name}</DialogTitle>
            <DialogContent>
              <TableContainer sx={{ maxHeight: 500, maxWidth: 1400 }}>
                <Table stickyHeader size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>ID</TableCell>
                            <TableCell>Name</TableCell>
                            <TableCell>Pattern</TableCell>
                            <TableCell>Rewrite</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                    {rules.map((rule) => (
                        <TableRow key={rule.id}>
                        <TableCell>{rule.id}</TableCell>
                        <TableCell>{rule.name}</TableCell>
                        <TableCell>
                            <SyntaxHighlighter language="sql" style={vs} wrapLongLines={true}>
                            {rule.pattern}
                            </SyntaxHighlighter>
                        </TableCell>
                        <TableCell>
                            <SyntaxHighlighter language="sql" style={vs} wrapLongLines={true}>
                            {rule.rewrite}
                            </SyntaxHighlighter>
                        </TableCell>
                        </TableRow>
                    ))}
                    </TableBody>
                </Table>
              </TableContainer>
           </DialogContent>
        </Dialog>
    );
});

export default ViewAssignedRules;