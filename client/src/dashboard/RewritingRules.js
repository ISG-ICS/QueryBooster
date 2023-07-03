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
import defaultRulesData from '../mock-api/listRules';
import SyntaxHighlighter from 'react-syntax-highlighter';
import { vs } from 'react-syntax-highlighter/dist/esm/styles/hljs';
import { Box } from '@mui/material';
import AddRewritingRule from './AddRewritingRule';
import AppTagCell from './ApplicationTag';
import {userContext} from '../userContext';


export default function RewrittingRules() {
  // Set up a state for list of rules
  const [rules, setRules] = React.useState([]);
  // Set up a state for providing forceUpdate function
  const [, updateState] = React.useState();
  const forceUpdate = React.useCallback(() => updateState({}), []);

  const user = React.useContext(userContext);

  // initial loading rules from server
  const listRules = () => {
    console.log('[/listRules] -> request:');
    console.log('  user_id: ' + user.id);
    // post listRules request to server
    axios.post('/listRules', {'user_id': user.id})
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
        // mock the result
        console.log(defaultRulesData);
        setRules(defaultRulesData);
        forceUpdate();
      });
  };

  // call listRules() only once after initial rendering
  React.useEffect(() => {listRules()}, [user]);
  
  // handle change on the switch of a rule
  const handleChange = (event, rule) => {
    
    // enable/disable the rule according to the switch checked
    rule.enabled = event.target.checked;

    // ! this will not re-render because the reference of rules has not changed.
    setRules(rules); 
    // ! use the forceUpdate() function instead to force re-rendering.
    forceUpdate();

    // post switchRule request to server
    axios.post('/switchRule', {id: rule.id, key: rule.key, enabled: rule.enabled})
    .then(function (response) {
      console.log('[/switchRule] -> response:');
      console.log(response);
    })
    .catch(function (error) {
      console.log('[/switchRule] -> error:');
      console.log(error);
    });
  };

  // handle click on the delete of a rule
  const handleDelete = (rule) => {

    // post deleteRule request to server
    axios.post('/deleteRule', {id: rule.id, key: rule.key})
    .then(function (response) {
      console.log('[/deleteRule] -> response:');
      console.log(response);
      listRules();
    })
    .catch(function (error) {
      console.log('[/deleteRule] -> error:');
      console.log(error);
      // mock delete rule from defaultRulesData
      const delIndex = defaultRulesData.findIndex(obj => {
        return obj.id === rule.id;
      });
      if (delIndex !== -1) {
        const removed = defaultRulesData.splice(delIndex, 1);
        console.log('removed successfully:');
        console.log(removed);
      }
      listRules();
    });
  };

  // handle click on add rewriting rule button
  const addRewritingRule = () => {
    NiceModal.show(AddRewritingRule, {user_id: user.id})
    .then((res) => {
      console.log(res);
      listRules();
    });
  };

  return (
    <React.Fragment>
      <Title>Rewriting Rules</Title>
      <TableContainer sx={{ maxHeight: 500, maxWidth: 1400 }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Pattern</TableCell>
              <TableCell>Rewrite</TableCell>
              <TableCell align="right">Enabled Apps</TableCell>
              <TableCell align="center">Delete</TableCell>
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
                <TableCell align="right">
                  {/* <Switch
                    checked={rule.enabled}
                    onChange={(event) => handleChange(event, rule)}
                    inputProps={{ 'aria-label': 'controlled' }} /> */}
                  <AppTagCell ruleId={rule.id} tags={rule.enabled_apps} />
                </TableCell>
                <TableCell align="center">
                  <Button variant="outlined" color="error" onClick={() => handleDelete(rule)} >Delete</Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      {/* <Link color="primary" href="#" onClick={preventDefault} sx={{ mt: 3 }}>
          See more orders
         </Link> */}
      <Box>
        <Fab size="small" color="primary" aria-label="add" onClick={() => addRewritingRule()}>
          <AddIcon />
        </Fab>
      </Box>
    </React.Fragment>
  );
}
