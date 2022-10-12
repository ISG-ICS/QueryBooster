import * as React from 'react';
import axios from 'axios';
import Link from '@mui/material/Link';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Switch from '@mui/material/Switch';
import Title from './Title';
import defaultRulesData from '../mock-api/listRules';
import SyntaxHighlighter from 'react-syntax-highlighter';
import { vs } from 'react-syntax-highlighter/dist/esm/styles/hljs';


export default function RewrittingRules() {
  // Set up a state for list of rules
  const [rules, setRules] = React.useState([]);
  // Set up a state for providing forceUpdate function
  const [, updateState] = React.useState();
  const forceUpdate = React.useCallback(() => updateState({}), []);

  // initial loading rules from server
  const listRules = () => {
    // post listRules request to server
    axios.post('/listRules', {})
      .then(function (response) {
        console.log('[/listRules] -> response:');
        console.log(response);
        // update the state for list of rules
        setRules(response.data);
      })
      .catch(function (error) {
        console.log('[/listRules] -> error:');
        console.log(error);
        // mock the result
        console.log(defaultRulesData);
        setRules(defaultRulesData);
      });
  };

  // call listRules() only once after initial rendering
  React.useEffect(() => {listRules()}, []);
  
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
              <TableCell>Constraints</TableCell>
              <TableCell>Rewrite</TableCell>
              <TableCell>Actions</TableCell>
              <TableCell align="right">Enabled</TableCell>
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
                    {rule.constraints}
                  </SyntaxHighlighter>
                </TableCell>
                <TableCell>
                  <SyntaxHighlighter language="sql" style={vs} wrapLongLines={true}>
                    {rule.rewrite}
                  </SyntaxHighlighter>
                </TableCell>
                <TableCell>
                  <SyntaxHighlighter language="sql" style={vs} wrapLongLines={true}>
                    {rule.actions}
                  </SyntaxHighlighter>
                </TableCell>
                <TableCell align="right">
                  <Switch
                    checked={rule.enabled}
                    onChange={(event) => handleChange(event, rule)}
                    inputProps={{ 'aria-label': 'controlled' }}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      {/* <Link color="primary" href="#" onClick={preventDefault} sx={{ mt: 3 }}>
        See more orders
      </Link> */}
    </React.Fragment>
  );
}
