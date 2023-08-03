import * as React from 'react';
import axios from 'axios';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Dialog from '@mui/material/Dialog';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Grid from '@mui/material/Grid';
import Link from '@mui/material/Link';
import NiceModal, { useModal } from '@ebay/nice-modal-react';
import { Link as RouterLink} from "react-router-dom";
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import defaultRecommendRuleData from '../mock-api/recommendRule';
import defaultRulesData from '../mock-api/listRules';
import { FormLabel } from '@mui/material';
import RuleGraph from './RuleGraph';

const EditRewritingRule = NiceModal.create(({user_id, rule, rule_id}) => {
  const modal = useModal();
  // Set up states for a rewriting rule
  const [name, setName] = React.useState(rule.name);
  const [pattern, setPattern] = React.useState(rule.pattern);
  const [constraints, setConstraints] = React.useState(rule.constraints);
  const [rewrite, setRewrite] = React.useState(rule.rewrite);
  const [actions, setActions] = React.useState(rule.actions);
  // Set up states for an example rewriting pair
  const [q0, setQ0] = React.useState("");
  const [q1, setQ1] = React.useState("");

  const onNameChange = (event) => {
    setName(event.target.value);
  };

  const onPatternChange = (event) => {
    setPattern(event.target.value);
  };

  const onConstraintsChange = (event) => {
    setConstraints(event.target.value);
  };

  const onRewriteChange = (event) => {
    setRewrite(event.target.value);
  };

  const onActionsChange = (event) => {
    setActions(event.target.value);
  };

  const onQ0Change = (event) => {
    setQ0(event.target.value);
  };

  const onQ1Change = (event) => {
    setQ1(event.target.value);
  };

  const onFormulate = () => {
    if (q0 != "" && q1 != "") {
      // post recommendRule request to server
      axios.post('/recommendRule', {'q0': q0, 'q1': q1})
      .then(function (response) {
        console.log('[/recommendRule] -> response:');
        console.log(response);
        // update the states for pattern and rewrite
        setPattern(response.data['pattern']);
        setRewrite(response.data['rewrite']);
      })
      .catch(function (error) {
        console.log('[/recommendRule] -> error:');
        console.log(error);
        // mock the result
        console.log(defaultRecommendRuleData);
        setPattern(defaultRecommendRuleData['pattern']);
        setRewrite(defaultRecommendRuleData['rewrite']);
      });
    }
  };

  const onEdit = () => {
    if (pattern != "" && rewrite != "") {
      // post addRule request to server
      const request = {
        'rule': {
          'name': name,
          'pattern': pattern,
          'constraints': constraints,
          'rewrite': rewrite,
          'actions': actions
        },
        'user_id': user_id,
        'id': rule_id
      };
      console.log('[/editRule] -> request:');
      console.log(request);
      axios.post('/editRule', request)
      .then(function (response) {
        console.log('[/editRule] -> response:');
        console.log(response);
        modal.resolve(response);
        modal.hide();
      })
      .catch(function (error) {
        console.log('[/editRule] -> error:');
        console.log(error);
        // mock add rule to defaultRulesData
        defaultRulesData.push(
          {
            "id": 22,
            "key": "replace_strpos_upper",
            "name": "Replace Strpos Upper",
            "pattern": "STRPOS(UPPER(<x>),'<y>')>0",
            "constraints": "IS(y)=CONSTANT and\nTYPE(y)=STRING",
            "rewrite": "<x> ILIKE '%<y>%'",
            "actions": "",
            "enabled_apps": []
          }
        );
        modal.resolve(error);
        modal.hide();
      });
    }
  };

  // handle click on show rule graph button
  const showRuleGraph = () => {
    NiceModal.show(RuleGraph, {rewriteExample: {'q0': q0, 'q1': q1}})
    .then((res) => {
      console.log(res);
    });
  };

  React.useEffect(() => {}, []);

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
      <DialogTitle>Add Rewriting Rule</DialogTitle>
        <DialogContent>
        <Grid sx={{ flexGrow: 1 }} container spacing={2}>
            <Grid item xs={12} sm={12} md={12} lg={12} xl={12}>
              <Grid container justifyContent="center" spacing={2}>
                <Grid item xs={12} sm={12} md={12} lg={12} xl={12}>
                  <Box width="100%"/>
                </Grid>
                <Grid item xs={12} sm={12} md={12} lg={12} xl={12}>
                  <TextField required id="name" label="Name" fullWidth value={name} onChange={onNameChange} />
                </Grid>
                <Grid item xs={12} sm={12} md={12} lg={12} xl={12}>
                  <Grid container justifyContent="center" spacing={2}>
                    <Grid item xs={6} sm={6} md={6} lg={6} xl={6}>
                      <TextField required id="pattern" label="Pattern" multiline fullWidth value={pattern} onChange={onPatternChange} />
                    </Grid>
                    <Grid item xs={6} sm={6} md={6} lg={6} xl={6}>
                      <TextField required id="rewrite" label="Rewrite" multiline fullWidth value={rewrite} onChange={onRewriteChange} />
                    </Grid>
                  </Grid>
                </Grid>
                <Grid item xs={12} sm={12} md={12} lg={12} xl={12}>
                  <Grid container justifyContent="center" spacing={2}>
                    <Grid item xs={6} sm={6} md={6} lg={6} xl={6}>
                      <TextField id="constraints" label="Constraints" multiline fullWidth value={constraints} onChange={onConstraintsChange} />
                    </Grid>
                    <Grid item xs={6} sm={6} md={6} lg={6} xl={6}>
                      <TextField id="actions" label="Actions" multiline fullWidth value={actions} onChange={onActionsChange} />
                    </Grid>
                  </Grid>
                </Grid>
                <Grid item xs={12} sm={12} md={12} lg={12} xl={12}>
                  <Button type="submit" variant="contained" color="primary" onClick={onEdit}>Edit</Button>
                </Grid>
                <Grid item xs={12} sm={12} md={12} lg={12} xl={12}>
                  <Box width="100%"/>
                </Grid>
                <Divider />
                <Grid item xs={12} sm={12} md={12} lg={12} xl={12}>
                  <Box width="100%"/>
                </Grid>
                <Grid item xs={12} sm={12} md={12} lg={12} xl={12}>
                  <FormLabel>Formulating a Rule using Rewriting Example</FormLabel>
                </Grid>
                <Grid item xs={6} sm={6} md={6} lg={6} xl={6}>
                  <TextField id="q0" label="Original SQL" multiline fullWidth onChange={onQ0Change} value={q0} />
                </Grid>
                <Grid item xs={6} sm={6} md={6} lg={6} xl={6}>
                  <TextField id="q1" label="Rewritten SQL" multiline fullWidth onChange={onQ1Change} value={q1} />
                </Grid>
                <Grid item xs={12} sm={12} md={12} lg={12} xl={12}>
                  <Stack direction="row" spacing={2}>
                    <Button variant="contained" color="primary" onClick={onFormulate}>Formulate</Button>
                    <Button variant="outlined" color="primary" onClick={showRuleGraph}>Rule Graph</Button>
                    <Link component={RouterLink} to="/formulator" onClick={()=>{modal.hide()}}>Use more examples</Link>
                  </Stack>
                </Grid>
              </Grid>
            </Grid>
          </Grid>
        </DialogContent>
    </Dialog>
  );
});

export default EditRewritingRule;
