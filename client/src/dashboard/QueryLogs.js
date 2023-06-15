import * as React from 'react';
import axios from 'axios';
import NiceModal from '@ebay/nice-modal-react';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Title from './Title';
import defaultQueriesData from '../mock-api/listQueries';
import QueryRewritingPath from './QueryRewritingPath';
import SyntaxHighlighter from 'react-syntax-highlighter';
import { vs } from 'react-syntax-highlighter/dist/esm/styles/hljs';
import {userContext} from '../userContext';


export default function QueryLogs() {
  // Set up a state for list of queries
  const [queries, setQueries] = React.useState([]);
  // Set up a state for providing forceUpdate function
  const [, updateState] = React.useState();
  const forceUpdate = React.useCallback(() => updateState({}), []);

  const user = React.useContext(userContext);

  // initial loading queries from server
  const listQueries = (_page) => {
    // post listQueries request to server
    axios.post('/listQueries', {page: _page, 'user_id': user.id})
      .then(function (response) {
        console.log('[/listQueries] -> response:');
        console.log(response);
        // update the state for list of queries
        setQueries(response.data);
      })
      .catch(function (error) {
        console.log('[/listQueries] -> error:');
        console.log(error);
        // mock the result
        console.log(defaultQueriesData);
        setQueries(defaultQueriesData);
      });
  };

  // call listQueries() only once after initial rendering
  React.useEffect(() => {listQueries(0)}, []);
  
  // handle click on a query
  const selectQuery = (query) => {
    console.log(query);
    NiceModal.show(QueryRewritingPath, {queryId: query.id});
  };

  return (
    <React.Fragment>
      <Title>Query Logs</Title>
      <TableContainer sx={{ maxHeight: 500, maxWidth: 1400 }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>App</TableCell>
              <TableCell>Timestamp</TableCell>
              <TableCell>Rewritten</TableCell>
              <TableCell>Before Latency(s)</TableCell>
              <TableCell>After Latency(s)</TableCell>
              <TableCell>SQL</TableCell>
              <TableCell>Suggestion</TableCell>
              <TableCell>Suggested Latency(s)</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {queries.map((query) => (
              <TableRow key={query.id} onClick={() => selectQuery(query)}>
                <TableCell>{query.id}</TableCell>
                <TableCell>{query.app_name}</TableCell>
                <TableCell>{query.timestamp}</TableCell>
                <TableCell>{query.boosted}</TableCell>
                <TableCell>{query.before_latency/1000}</TableCell>
                <TableCell>{query.after_latency/1000}</TableCell>
                <TableCell>
                  <SyntaxHighlighter language="sql" style={vs} wrapLongLines={true}>
                    {query.sql}
                  </SyntaxHighlighter>
                </TableCell>
                <TableCell>{query.suggestion}</TableCell>
                <TableCell>{query.suggested_latency/1000}</TableCell>
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
