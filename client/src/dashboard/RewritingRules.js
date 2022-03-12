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

// Generate Rewriting Rules Data
function createData(id, key, name, formula, enabled) {
  return { id, key, name, formula, enabled };
}

const rows = [
  createData(
    0,
    'REMOVE_CAST',
    'Remove Cast',
    'CAST(<exp> AS <type>) => <exp>',
    true,
  ),
  createData(
    1,
    'REPLACE_STRPOS',
    'Replace Strpos',
    'STRPOS(LOWER(<exp>), \'<literal>\') > 0 => <exp> ILIKE \'%<literal>%\'',
    true,
  ),
  createData(
    2,
    'USE_INDEX',
    'Use Index',
    'BitmapScan(tweets idx_tweets_monthly_created_at)',
    true,
  ),
];

function preventDefault(event) {
  event.preventDefault();
}

export default function RewrittingRules() {
  // use state {row[0].key: row[0].enabled, row[1].key: row[1].enabled, ...}
  const switchState = rows.reduce((acc, cur) => ({ ...acc, [cur.key]: cur.enabled }), {});
  const [state, setState] = React.useState(switchState);

  const handleChange = (event, id) => {
    
    // change the data rows according to switch checked
    const row = rows.find((row) => {return row.id === id});
    row.enabled = event.target.checked;
    console.log("[handleChange] row {" + row.id + "}.enabled = " + row.enabled);
    
    // set the state based on the changed data
    const switchState = rows.reduce((acc, cur) => ({ ...acc, [cur.key]: cur.enabled }), {});
    setState(switchState);

    // post updateRule request to server
    axios.post('/updateRule', row)
    .then(function (response) {
      console.log(response);
    })
    .catch(function (error) {
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
          {rows.map((row) => (
            <TableRow key={row.id}>
              <TableCell>{row.id}</TableCell>
              <TableCell>{row.name}</TableCell>
              <TableCell>{row.formula}</TableCell>
              <TableCell align="right">
                <Switch
                  checked={state[row.key]}
                  onChange={(event) => handleChange(event, row.id)}
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
