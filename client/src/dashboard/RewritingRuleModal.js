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
import InputLabel from '@mui/material/InputLabel';
import FormControl from '@mui/material/FormControl';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import RuleGraph from './RuleGraph';
import AceEditor from "react-ace";
import { diffChars } from 'diff';
import { format } from 'sql-formatter';
import "ace-builds/src-noconflict/theme-textmate";
import "ace-builds/src-noconflict/mode-mysql";
import "ace-builds/src-noconflict/mode-pgsql";
import "ace-builds/src-noconflict/ext-language_tools";

const RewritingRuleModal = NiceModal.create(({user_id, rule=null, query=null}) => {
  const modal = useModal();
  // Set up query language used for query editor
  const [queryOptions, setQueryOptions] = React.useState(["mysql", "pgsql"])
  const [queryLanguage, setQueryLanguage] = React.useState("mysql")
  // Set up states for a rewriting rule
  const isNewRule = !rule;
  const hasQuery = !!query;
  const [name, setName] = React.useState(isNewRule ? "" : rule.name);
  const [pattern, setPattern] = React.useState(isNewRule ? "" : rule.pattern);
  const [constraints, setConstraints] = React.useState(isNewRule ? "" : rule.constraints);
  const [rewrite, setRewrite] = React.useState(isNewRule ? "" : rule.rewrite);
  const [actions, setActions] = React.useState(isNewRule ? "" : rule.actions);
  // Set up states for an example rewriting pair
  const [q0, setQ0] = React.useState(hasQuery ? query[0] : "");
  const [q1, setQ1] = React.useState(hasQuery ? query[1] : "");
  //set compare marker
  const [q0Markers, setq0Markers] = React.useState([]);
  const [q1Markers, setq1Markers] = React.useState([]);

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

  const onQ0Change = (newQ0Value) => {
    setQ0(newQ0Value);
  };

  const onQ1Change = (newQ1Value) => {
    setQ1(newQ1Value);
  };

  const handleSelectChange = (event) => {
    setQueryLanguage(event.target.value);
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

  const onAddOrEdit = () => {
    if (pattern != "" && rewrite != "") {
      // post saveRule request to server
      const request = {
        'rule': {
          'name': name,
          'pattern': pattern,
          'constraints': constraints,
          'rewrite': rewrite,
          'actions': actions,
          'id': isNewRule ? -1 : rule.id
        },
        'user_id': user_id
      };
      console.log('[/saveRule] -> request:');
      console.log(request);
      axios.post('/saveRule', request)
      .then(function (response) {
        console.log('[/saveRule] -> response:');
        console.log(response);
        modal.resolve(response);
        modal.hide();
      })
      .catch(function (error) {
        console.log('[/saveRule] -> error:');
        console.log(error);

        if (isNewRule) {
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
        } else {
          // mock update rule to defaultRulesData
          const index = defaultRulesData.findIndex(r => r.id === rule.id);
          if (index !== -1) {
            defaultRulesData[index] = {
              ...defaultRulesData[index],
              name: name,
              pattern: pattern,
              constraints: constraints,
              rewrite: rewrite,
              actions: actions
            };
          }
        }
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

  //resize query editor
  const onLoad = (editor) => {
    editor.on('change', (arg, activeEditor) => {
      const aceEditor = activeEditor;
      const curHeight = aceEditor.getSession().getScreenLength() *
        (aceEditor.renderer.lineHeight + aceEditor.renderer.scrollBar.getWidth());
      const newHeight = (curHeight < 100) ? 100 : curHeight;
      aceEditor.container.style.height = `${newHeight}px`;
      aceEditor.resize();
    });
  };

  const onBeautifyQuery = () => {
    const sqlLanguage = (queryLanguage === 'pgsql') ? "postgresql" : queryLanguage;
    const q0Format = format(q0, {"language": sqlLanguage,
                                  "tabWidth": 1});
    const q1Format = format(q1, { "language": sqlLanguage,
                                  "tabWidth": 1});

    const newLine = [];           
    let curPos = 0;

    const q0Lines = (q0Format === "") ? "" : q0Format.split('\n');
    const q1Lines = (q1Format === "") ? "" : q1Format.split('\n');

    let q0Pos = 0;
    let q1Pos = 0;
    let newq0 = '';
    let newq1 = '';

    // Align two queries
    while (q0Pos < q0Lines.length && q1Pos < q1Lines.length) {
      const diffs = diffChars(q0Lines[q0Pos], q1Lines[q1Pos]);
      // console.log(q0Lines[q0Pos], q1Lines[q1Pos]);
      // console.log(diffs);
      if (diffs.length == 1 && ! diffs[0].added && ! diffs[0].removed) {
        newq0 += q0Lines[q0Pos] + '\n';
        newq1 += q1Lines[q1Pos] + '\n';
        q0Pos += 1;
        q1Pos += 1;
      } else {
        if (diffs.filter(diff => (! diff.added && ! diff.removed && !(/^\s*$/.test(diff.value)))).length > 0) {
          newq0 += q0Lines[q0Pos] + '\n';
          newq1 += q1Lines[q1Pos] + '\n';
          q0Pos += 1;
          q1Pos += 1;
        } else {
          newq0 += q0Lines[q0Pos] + '\n';
          newq1 += ' \n';
          q0Pos += 1;
        }
      }
    }

    setQ0(newq0);
    setQ1(newq1);
  }

  function findDistanceToSpaces(inputString, currentPosition) {
    // Special case: if current character is a space
    const isSpace = (inputString[currentPosition] === ' ');
    let prevSpaceIndex = isSpace ? inputString.lastIndexOf(' ', currentPosition-1) : inputString.lastIndexOf(' ', currentPosition);
    let nextSpaceIndex = isSpace ? inputString.indexOf(' ', currentPosition+1) : inputString.indexOf(' ', currentPosition);

    if (nextSpaceIndex === -1){
      nextSpaceIndex = inputString.length;
    };
  
    // Calculate the distance to the previous and next space characters
    const distanceToPrevSpace = currentPosition - prevSpaceIndex;
    const distanceToNextSpace = nextSpaceIndex - currentPosition;
  
    return {
      distanceToPrevSpace,
      distanceToNextSpace,
    };
  };

  const updateMarkers = () => {
    // Clear previous markers
    setq0Markers([]);
    setq1Markers([]);

    const q0Lines = (q0 === "") ? "" : q0.split('\n');
    const q1Lines = (q1 === "") ? "" : q1.split('\n');

    if ( q0 !== "") {
      // const indexes0 = [...q0.matchAll(new RegExp('\n', 'g'))].map(a => a.index);
      // const indexes1 = [...q1.matchAll(new RegExp('\n', 'g'))].map(a => a.index);
      // console.log(indexes0, indexes1); 

      // getDiffByLine(0, q0, q1);
      // Check on each code line's difference and update marker for each line
      q0Lines.forEach((line, index) => {
        const q1Line = (q1Lines === "" || q1Lines.length <= index) ? "" : q1Lines[index];
        getDiffByLine(index, line, q1Line);
      });
    }
  }

  const getDiffByLine = (index, q0Line, q1Line) => {
    // Get every character difference using diff library

    // diffs is an array of elements form like: { count: length_of_difference(int), added: is_added(bool/undefined), removed: is_removed(bool/undefined), value: difference_string(string) }
    // e.g: [ 0: {count: 32, added: undefined, removed: true, value: "this is the string being removed"},
    //        1: {count: 30, added: true, removed: undefined, value: "this is the string being added"},
    //        2: {count: 33, added: undefined, removed: undefined, value: "this is the string without change"}]
    const diffs = diffChars(q0Line, q1Line);

    const newq0Markers = [];
    const newq1Markers = [];

    // Variables used to track marker position 
    let q0Index = 0;
    let q1Index = 0;
    let prevRemv = false;
    let canReplace = false;

    // Loop through each difference
    diffs.forEach((diff) => {
      // Get the length of current difference
      const valueLength = diff.value.length;

      if (canReplace){
        // Detect can replace: will switch the last marker to replace-marker
        if (diff.added) {
          // If current difference is an add operation: combine this add to last marker
          newq0Markers[newq0Markers.length - 1].endCol = q0Index;
          newq1Markers[newq1Markers.length - 1].endCol = q1Index + valueLength;
          q1Index += valueLength;
        } else if (diff.removed) {
          // If current difference is an remove operation: combine this remove to last marker
          newq0Markers[newq0Markers.length - 1].endCol = q0Index + valueLength;
          newq1Markers[newq1Markers.length - 1].endCol = q1Index;
          q0Index += valueLength;
        } else {
          // If current part has no difference: no marker change
          q0Index += valueLength;
          q1Index += valueLength;
          if (!(/^\s*$/.test(diff.value))){
            // Check if all space
            canReplace = false;
          }
        }
        prevRemv = false;
      } else {
        if (diff.added) {
          if(prevRemv) {
            // Replace: pop all previous removed-marker
            const lastq0Remv = newq0Markers.pop();
            const lastq1Remv = newq1Markers.pop();

            // Push new replaced-marker for both q0 and q1
            newq1Markers.push({
              startRow: index,
              startCol: q1Index,
              endRow: index,
              endCol: q1Index + valueLength,
              className: "replace-marker",
            });
            newq0Markers.push({
              startRow: index,
              startCol: lastq0Remv.startCol,
              endRow: index,
              endCol: lastq0Remv.endCol,
              className: "replace-marker",
            });
            // Set canReplace to true
            canReplace = true;
          } else {
            // Detect the position for the entire word: seperated by spaces
            const q0WordDiff = findDistanceToSpaces(q0Line, q0Index);
            const q1WordDiff = findDistanceToSpaces(q1Line, q1Index);
            // Normal Add operation, add marker for the entire word for both q0 and q1
            newq0Markers.push({
              startRow: index,
              startCol: q0Index - q0WordDiff.distanceToPrevSpace + 1,
              endRow: index,
              endCol: q0Index + q0WordDiff.distanceToNextSpace,
              className: "add-all-marker",
            });
            newq1Markers.push({
              startRow: index,
              startCol: q1Index - q1WordDiff.distanceToPrevSpace + 1,
              endRow: index,
              endCol: q1Index + q1WordDiff.distanceToNextSpace,
              className: "add-all-marker",
            });
            // Highlight added character position
            newq1Markers.push({
              startRow: index,
              startCol: q1Index,
              endRow: index,
              endCol: q1Index + valueLength,
              className: "add-position-marker",
            });
          }
          q1Index += valueLength;
          prevRemv = false;
        } else if (diff.removed) {
          // Normal remove operation: push remove marker to both q0 and q1
          newq0Markers.push({
            startRow: index,
            startCol: q0Index,
            endRow: index,
            endCol: q0Index + valueLength,
            className: "remove-marker",
          });
          newq1Markers.push({
            startRow: index,
            startCol: q1Index - 1,
            endRow: index,
            endCol: q1Index,
            className: "remove-marker",
          });
          q0Index += valueLength;
          prevRemv = true;
        } else {
          // No add, remove, replace detected: no marker change, just update position
          q0Index += valueLength;
          q1Index += valueLength;
          prevRemv = false;
        }
      }
    });

    // Resolve marker overlap
    newq0Markers.sort((a, b) => a.className.localeCompare(b.className));
    newq1Markers.sort((a, b) => a.className.localeCompare(b.className));

    // Set New Markers for current line
    setq0Markers(q0Markers => [...q0Markers, ...newq0Markers]);
    setq1Markers(q1Markers => [...q1Markers, ...newq1Markers]);
  }

  React.useEffect(() => {updateMarkers();}, [q0, q1]);

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
      <DialogTitle>{isNewRule ? "Add Rewriting Rule" : "Edit Rewriting Rule"}</DialogTitle>
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
                  <Button type="submit" variant="contained" color="primary" onClick={onAddOrEdit}>Save</Button>
                </Grid>
                <Grid item xs={12} sm={12} md={12} lg={12} xl={12}>
                  <Box width="100%"/>
                </Grid>
                <Divider />
                <Grid item xs={12} sm={12} md={12} lg={12} xl={12}>
                  <Grid container justifyContent="flex-start" alignItems="center" spacing={1}>
                    <Grid item xs={4} sm={4} md={4} lg={4} xl={4}>
                      <FormLabel>Formulating a Rule using Rewriting Example</FormLabel>
                    </Grid>
                    <Grid item xs={3} sm={3} md={3} lg={3} xl={3}>
                      <Button variant="outlined" color="primary" onClick={onBeautifyQuery}>Beautify both Queries</Button>
                    </Grid>
                    <Grid item xs={2} sm={2} md={2} lg={2} xl={2}>
                      <FormControl fullWidth>
                        <InputLabel>Select SQL Dialect</InputLabel>
                        <Select label="Select SQL Dialect" value={queryLanguage} onChange={handleSelectChange}>
                          {queryOptions.map((queryOption) => (
                              <MenuItem value={queryOption}>{queryOption}</MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                    </Grid>
                  </Grid>
                </Grid>
                <Grid item xs={6} sm={6} md={6} lg={6} xl={6}>
                  <AceEditor
                    placeholder="Original SQL"
                    mode={queryLanguage}
                    theme="textmate"
                    width='100%'
                    height='100px'
                    onLoad={onLoad}
                    markers={q0Markers}
                    fontSize={14}
                    showPrintMargin={false}
                    wrapEnabled={true}
                    showGutter={true}
                    highlightActiveLine={false}
                    value={q0}
                    onChange={onQ0Change}  
                    setOptions={{
                    enableBasicAutocompletion: false,
                    enableLiveAutocompletion: true,
                    enableSnippets: false,
                    showLineNumbers: false,
                    tabSize: 2,
                  }}/>
                </Grid>
                <Grid item xs={6} sm={6} md={6} lg={6} xl={6}>
                  <AceEditor
                    placeholder="Rewritten SQL"
                    mode={queryLanguage}
                    theme="textmate"
                    width='100%'
                    height='100px'
                    onLoad={onLoad}
                    markers={q1Markers}
                    fontSize={14}
                    showPrintMargin={false}
                    wrapEnabled={true}
                    showGutter={true}
                    highlightActiveLine={false}
                    value={q1}
                    onChange={onQ1Change}
                    setOptions={{
                    enableBasicAutocompletion: false,
                    enableLiveAutocompletion: true,
                    enableSnippets: false,
                    showLineNumbers: false,
                    tabSize: 2,
                  }}/>
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

export default RewritingRuleModal;
