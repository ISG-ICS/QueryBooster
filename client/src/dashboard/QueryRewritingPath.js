import * as React from 'react';
import axios from 'axios';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import { styled } from '@mui/material/styles';
import NiceModal, { useModal } from '@ebay/nice-modal-react';
import Title from './Title';
import defaultRewritingPathData from '../mock-api/rewritingPath';
import SyntaxHighlighter from 'react-syntax-highlighter';
import { vs } from 'react-syntax-highlighter/dist/esm/styles/hljs';

const Item = styled(Paper)(({ theme }) => ({
  backgroundColor: theme.palette.mode === 'dark' ? '#1A2027' : '#fff',
  ...theme.typography.body2,
  padding: theme.spacing(1),
  textAlign: 'left',
  color: theme.palette.text.primary,
}));

const QueryRewritingPath = NiceModal.create(({ queryId }) => {
  const modal = useModal();
  // Set up a state for rewritingPath
  const [rewritingPath, setRewritingPath] = React.useState({rewritings:[]});
  // Set up a state for providing forceUpdate function
  const [, updateState] = React.useState();
  const forceUpdate = React.useCallback(() => updateState({}), []);
  
  // initial loading rewritings from server
  const getRewritingPath = (_queryId) => {
    // post rewritingPath request to server
    axios.post('/rewritingPath', {queryId: _queryId})
    .then(function (response) {
      console.log('[/rewritingPath] -> response:');
      console.log(response);
      // update the state for rewritingPath
      setRewritingPath(response.data);
    })
    .catch(function (error) {
      console.log('[/rewritingPath] -> error:');
      console.log(error);
      // mock the result
      console.log(defaultRewritingPathData);
      setRewritingPath(defaultRewritingPathData);
    });
  };

  // call rewritePath() only once after initial rendering
  React.useEffect(() => {getRewritingPath({queryId})}, []);
  
  return (
    <Dialog
      open={modal.visible}
      onClose={() => modal.hide()}
      TransitionProps={{
        onExited: () => modal.remove(),
      }}
    >
      <DialogTitle>Query Rewriting Path</DialogTitle>
      <DialogContent>
        <DialogContentText>
          <Box sx={{ width: '100%' }}>
            <Stack spacing={2}>
              <Item>
                <SyntaxHighlighter language="sql" style={vs} wrapLongLines={true}>
                  {rewritingPath.original_sql}
                </SyntaxHighlighter>
              </Item>
              {rewritingPath.rewritings.map((rewriting) => (
                <Stack spacing={2}>
                  <Item>{rewriting.rule}</Item>
                  <Item>
                    <SyntaxHighlighter language="sql" style={vs} wrapLongLines={true}>
                      {rewriting.rewritten_sql}
                    </SyntaxHighlighter>
                  </Item>
                </Stack>
              ))}
            </Stack>
          </Box>
        </DialogContentText>
      </DialogContent>
    </Dialog>
  );
});

export default QueryRewritingPath;
