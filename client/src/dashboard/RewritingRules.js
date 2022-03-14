import * as React from 'react';
import axios from 'axios';
import Link from '@mui/material/Link';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Switch from '@mui/material/Switch';
import Title from './Title';


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

    // post updateRule request to server
    axios.post('/updateRule', rule)
    .then(function (response) {
      console.log('[/updateRule] -> response:');
      console.log(response);
    })
    .catch(function (error) {
      console.log('[/updateRule] -> error:');
      console.log(error);
    });
  };

  return (
    <React.Fragment>
      <Title>Rewriting Rules</Title>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>ID</TableCell>
            <TableCell>Name</TableCell>
            <TableCell>Formula</TableCell>
            <TableCell align="right">Enabled</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rules.map((rule) => (
            <TableRow key={rule.id}>
              <TableCell>{rule.id}</TableCell>
              <TableCell>{rule.name}</TableCell>
              <TableCell>{rule.formula}</TableCell>
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
      {/* <Link color="primary" href="#" onClick={preventDefault} sx={{ mt: 3 }}>
        See more orders
      </Link> */}
    </React.Fragment>
  );
}
