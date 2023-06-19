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
import defaultSuggestionRewritingPathData from '../mock-api/suggestionRewritingPath';
import SyntaxHighlighter from 'react-syntax-highlighter';
import { vs } from 'react-syntax-highlighter/dist/esm/styles/hljs';

const Item = styled(Paper)(({ theme }) => ({
  backgroundColor: theme.palette.mode === 'dark' ? '#1A2027' : '#fff',
  ...theme.typography.body2,
  padding: theme.spacing(1),
  textAlign: 'left',
  color: theme.palette.text.primary,
}));

const QuerySuggestionRewritingPath = NiceModal.create(({ queryId }) => {
  const modal = useModal();
  // Set up a state for rewritingPath
  const [suggestionRewritingPath, setSuggestionRewritingPath] = React.useState({rewritings:[]});
  // Set up a state for providing forceUpdate function
  const [, updateState] = React.useState();
  const forceUpdate = React.useCallback(() => updateState({}), []);
  
  // initial loading suggestion rewritings from server
  const getSuggestionRewritingPath = (_queryId) => {
    // post suggestionRewritingPath request to server
    axios.post('/suggestionRewritingPath', {queryId: _queryId})
    .then(function (response) {
      console.log('[/suggestionRewritingPath] -> response:');
      console.log(response);
      // update the state for suggestionRewritingPath
      setSuggestionRewritingPath(response.data);
    })
    .catch(function (error) {
      console.log('[/suggestionRewritingPath] -> error:');
      console.log(error);
      // mock the result
      console.log(defaultSuggestionRewritingPathData);
      setSuggestionRewritingPath(defaultSuggestionRewritingPathData);
    });
  };

  // call getSuggestionRewritePath() only once after initial rendering
  React.useEffect(() => {getSuggestionRewritingPath(queryId)}, []);
  
  return (
    <Dialog
      open={modal.visible}
      onClose={() => modal.hide()}
      TransitionProps={{
        onExited: () => modal.remove(),
      }}
    >
      <DialogTitle>Query Suggestion Rewriting Path</DialogTitle>
      <DialogContent>
        <DialogContentText>
          <Box sx={{ width: '100%' }}>
            <Stack spacing={2}>
              <Item>
                <SyntaxHighlighter language="sql" style={vs} wrapLongLines={true}>
                  {suggestionRewritingPath.original_sql}
                </SyntaxHighlighter>
              </Item>
              {suggestionRewritingPath.rewritings.map((rewriting) => (
                <Stack spacing={2}>
                  <Item>
                    <Stack direction="row" spacing={2} >
                      <Item>{rewriting.rule}</Item>
                      <Item>{rewriting.rule_user_email}</Item>
                      <Button variant="outlined">Add to mine</Button>
                    </Stack>
                  </Item>
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

export default QuerySuggestionRewritingPath;
