import * as React from 'react';
import axios from 'axios';
import AddIcon from '@mui/icons-material/Add';
import Box from '@mui/material/Box';
import Button from "@mui/material/Button";
import Divider from '@mui/material/Divider';
import FormLabel from '@mui/material/FormLabel';
import Grid from '@mui/material/Grid';
import MenuItem from '@mui/material/MenuItem';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Title from './Title';
import Typography from '@mui/material/Typography';

import databaseOptions from '../constants/databaseOptions';
import defaultRulesData from '../mock-api/listRules';
import defaultRecommendRulesData from '../mock-api/recommendRules';

import NiceModal from '@ebay/nice-modal-react';
import RulesGraph from './RulesGraph';

import FullLayout from './FullLayout';


export default function RuleFormulator() {

  // Set up states for rewriting examples
  const [examples, setExamples] = React.useState([{q0:"", q1:""}]);
  const [database, setDatabase] = React.useState("postgresql");

  const onDatabaseChange = (event) => {
    setDatabase(event.target.value);
  };

  const onAddExample = () => {
    setExamples(current => [...current, {q0:"", q1:""}]);
  };

  const onDeleteExample = (index) => {
    setExamples([
      ...examples.slice(0, index),
      ...examples.slice(index + 1)
    ]);
  };

  const onQ0Change = (event, index) => {
    const newExamples = examples.map((example, i) => {
      if (index === i) {
        return { ...example, 'q0': event.target.value };
      } else {
        return example;
      }
    });
    setExamples(newExamples);
  };

  const onQ1Change = (event, index) => {
    const newExamples = examples.map((example, i) => {
      if (index === i) {
        return { ...example, 'q1': event.target.value };
      } else {
        return example;
      }
    });
    setExamples(newExamples);
  };

  const onFormulate = () => {
    if (examples.length >= 1 && examples[0].q0 != "" && examples[0].q1 != "") {
      console.log('[/recommendRules] -> request:');
      console.log({'examples': examples, 'database': database});
      // post recommendRule request to server
      axios.post('/recommendRules', {'examples': examples, 'database': database})
      .then(function (response) {
        console.log('[/recommendRules] -> response:');
        console.log(response);
        // update the states for rules
        setRules(response.data);
      })
      .catch(function (error) {
        console.log('[/recommendRules] -> error:');
        console.log(error);
        // mock the result
        console.log(defaultRecommendRulesData);
        setRules(defaultRecommendRulesData);
      });
    }
  };

  const showRuleGraph = () => {
    NiceModal.show(RulesGraph, {rewriteExamples: examples, database: database})
    .then((res) => {
      console.log(res);
    });
  };

  // Set up states for rewriting rules
  const [rules, setRules] = React.useState([]);

  const onPatternChange = (event, index) => {
    const newRules = rules.map((rule, i) => {
      if (index === i) {
        return { ...rule, 'pattern': event.target.value };
      } else {
        return rule;
      }
    });
    setRules(newRules);
  };

  const onRewriteChange = (event, index) => {
    const newRules = rules.map((rule, i) => {
      if (index === i) {
        return { ...rule, 'rewrite': event.target.value };
      } else {
        return rule;
      }
    });
    setRules(newRules);
  };

  const onNameChange = (event, index) => {
    const newRules = rules.map((rule, i) => {
      if (index === i) {
        return { ...rule, 'name': event.target.value };
      } else {
        return rule;
      }
    });
    setRules(newRules);
  };

  const onConstraintsChange = (event, index) => {
    const newRules = rules.map((rule, i) => {
      if (index === i) {
        return { ...rule, 'constraints': event.target.value };
      } else {
        return rule;
      }
    });
    setRules(newRules);
  };

  const onActionsChange = (event, index) => {
    const newRules = rules.map((rule, i) => {
      if (index === i) {
        return { ...rule, 'actions': event.target.value };
      } else {
        return rule;
      }
    });
    setRules(newRules);
  };

  const onAdd = (rule) => {
    if (rule['pattern'] != "" && rule['rewrite'] != "") {
      console.log('[/addRule] -> request:');
      console.log({
        'name': rule['name'], 
        'pattern': rule['pattern'], 
        'constraints': rule['constraints'], 
        'rewrite': rule['rewrite'], 
        'actions': rule['actions'], 
        'database': database
      });
      // post addRule request to server
      axios.post('/addRule', 
        {
          'name': rule['name'], 
          'pattern': rule['pattern'], 
          'constraints': rule['constraints'], 
          'rewrite': rule['rewrite'], 
          'actions': rule['actions'], 
          'database': database
        }
      )
      .then(function (response) {
        console.log('[/addRule] -> response:');
        console.log(response);
      })
      .catch(function (error) {
        console.log('[/addRule] -> error:');
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
            "enabled": false
          }
        );
      });
    }
  };

  React.useEffect(() => {}, [examples, rules]);

  return (
    <FullLayout>
      <Title>Rule Formulator</Title>
      <Grid sx={{ flexGrow: 1 }} container alignItems="top" spacing={2}>
        <Grid item xs={12} sm={12} md={12} lg={12} xl={12}>
          <Grid container justifyContent="center" alignItems="center" spacing={2}>
            <Grid item xs={5} sm={5} md={5} lg={5} xl={5}>
              <Box width="100%">
                <Typography variant="h6" gutterBottom>
                  Rewriting Examples
                </Typography>
              </Box>
              <Divider />
            </Grid>
            <Grid item xs={2} sm={2} md={2} lg={2} xl={2}/>
            <Grid item xs={5} sm={5} md={5} lg={5} xl={5}>
              <Box width="100%">
                <Typography variant="h6" gutterBottom>
                Formulated Rules
                </Typography>
              </Box>
              <Divider />
            </Grid>
          </Grid>
        </Grid>
        <Grid item xs={12} sm={12} md={12} lg={12} xl={12}>
          <Grid container justifyContent="center" alignItems="center" spacing={2}>
            <Grid item xs={5} sm={5} md={5} lg={5} xl={5}>
              <Grid container justifyContent="center" alignItems="center" spacing={2}>
                {examples.map((example, index) => (
                  <>
                    <Grid item xs={12} sm={12} md={12} lg={12} xl={12}>
                      <Stack direction="row" spacing={2}>
                        <FormLabel>Example #{index+1}</FormLabel>
                        {index > 0 && <Button variant="outlined" color="error" onClick={() => onDeleteExample(index)} >Delete</Button>}
                      </Stack>
                    </Grid>
                    <Grid item xs={6} sm={6} md={6} lg={6} xl={6}>
                      <TextField label="Original SQL" multiline fullWidth onChange={(event) => onQ0Change(event, index)} value={example.q0} />
                    </Grid>
                    <Grid item xs={6} sm={6} md={6} lg={6} xl={6}>
                      <TextField label="Rewritten SQL" multiline fullWidth onChange={(event) => onQ1Change(event, index)} value={example.q1} />
                    </Grid>
                    <Grid item xs={12} sm={12} md={12} lg={12} xl={12}>
                      <Box width="100%"/>
                    </Grid>
                  </>
                ))}
                <Grid item xs={12} sm={12} md={12} lg={12} xl={12}>
                  <Button variant="outlined" startIcon={<AddIcon />} onClick={onAddExample}>
                    Add Example
                  </Button>
                </Grid>
              </Grid>
            </Grid>
            <Grid item xs={2} sm={2} md={2} lg={2} xl={2}>
              <Grid container direction="column" justifyContent="center" alignItems="center" spacing={2}>
                <Grid item/>
                <Grid item>
                  <TextField required select label="Database" fullWidth value={database} onChange={onDatabaseChange} >
                    {databaseOptions.map((option) => (
                      <MenuItem key={option.value} value={option.value}>
                        {option.label}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>
                <Grid item>
                  <Stack direction="column" spacing={2}>
                    <Button variant="contained" color="primary" onClick={onFormulate}>Formulate</Button>
                    <Button variant="outlined" color="primary" onClick={showRuleGraph}>Rule Graph</Button>
                  </Stack>
                </Grid>
                <Grid item/>
              </Grid>
            </Grid>
            <Grid item xs={5} sm={5} md={5} lg={5} xl={5}>
              <Grid container justifyContent="center" alignItems="center" spacing={2}>
                {rules.map((rule, index) => (
                  <>
                    <Grid item xs={12} sm={12} md={12} lg={12} xl={12}>
                      <Stack direction="row" spacing={2}>
                        <FormLabel>Rule #{index+1}</FormLabel>
                        <Button type="submit" variant="contained" color="primary" onClick={() => onAdd(rule)}>Add</Button>
                      </Stack>
                    </Grid>
                    <Grid item xs={12} sm={12} md={12} lg={12} xl={12}>
                      <Grid container justifyContent="center" spacing={2}>
                        <Grid item xs={7} sm={7} md={7} lg={7} xl={7}>
                          <TextField required label="Pattern" multiline fullWidth value={rule.pattern} onChange={(event) => onPatternChange(event, index)} />
                        </Grid>
                        <Grid item xs={5} sm={5} md={5} lg={5} xl={5}>
                          <TextField required label="Rewrite" multiline fullWidth value={rule.rewrite} onChange={(event) => onRewriteChange(event, index)} />
                        </Grid>
                        <Grid item xs={4} sm={4} md={4} lg={4} xl={4}>
                          <TextField required label="Name" fullWidth value={rule.name} onChange={(event) => onNameChange(event, index)} />
                        </Grid>
                        <Grid item xs={4} sm={4} md={4} lg={4} xl={4}>
                          <TextField label="Constraints" multiline fullWidth value={rule.constraints} onChange={(event) => onConstraintsChange(event, index)} />
                        </Grid>
                        <Grid item xs={4} sm={4} md={4} lg={4} xl={4}>
                          <TextField label="Actions" multiline fullWidth value={rule.actions} onChange={(event) => onActionsChange(event, index)} />
                        </Grid>
                      </Grid>
                    </Grid>
                    <Grid item xs={12} sm={12} md={12} lg={12} xl={12}>
                      <Box width="100%"/>
                    </Grid>
                  </>
                ))}
              </Grid>
            </Grid>
          </Grid>
        </Grid>
      </Grid>
      </FullLayout>
  );
}
