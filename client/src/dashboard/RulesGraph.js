import * as React from 'react';
import axios from 'axios';
import dagre from 'dagre';
import Dialog from '@mui/material/Dialog';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Divider from '@mui/material/Divider';
import NiceModal, { useModal } from '@ebay/nice-modal-react';
import Paper from '@mui/material/Paper';
import Popover from '@mui/material/Popover';
import Stack from '@mui/material/Stack';
import ReactFlow, { Controls, MiniMap, useNodesState, useEdgesState, MarkerType } from 'reactflow';
import 'reactflow/dist/style.css';
import SyntaxHighlighter from 'react-syntax-highlighter';
import { vs } from 'react-syntax-highlighter/dist/esm/styles/hljs';

import defaultRulesGraphData from '../mock-api/generateRulesGraph';

const nodeWidth = 300;
const nodeHeight = 500;

const RulesGraph = NiceModal.create(({ rewriteExamples, database }) => {
  const modal = useModal();
  // Set up states for ReactFlow
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  // Set up states for PopOver
  const [anchorEl, setAnchorEl] = React.useState(null);
  const [popRule, setPopRule] = React.useState({});
  // Set up a state for providing forceUpdate function
  const [, updateState] = React.useState();
  const forceUpdate = React.useCallback(() => updateState({}), []);

  // initial loading rules graph from server
  const getRulesGraph = (_rewriteExamples, _database) => {
    if (_rewriteExamples.length >= 1 && _rewriteExamples[0].q0 != "" && _rewriteExamples[0].q1 != "") {
     // post generateRulesGraph request to server
     axios.post('/generateRulesGraph', {'examples': _rewriteExamples, 'database': _database})
     .then(function (response) {
       console.log('[/generateRulesGraph] -> response:');
       console.log(response);
       // update the states for rulesGraph
       computeNodesAndEdges(response.data);
     })
     .catch(function (error) {
       console.log('[/generateRulesGraph] -> error:');
       console.log(error);
       // mock the result
       console.log(defaultRulesGraphData);
       computeNodesAndEdges(defaultRulesGraphData);
     });
    }
  };
  
  // compute the nodes and edges for the rulesGraph
  const computeNodesAndEdges = (_rulesGraphData) => {
    // loop rules in _ruleGraph to build nodes list
    let _rules = _rulesGraphData['rules'];
    let _nodes = [];
    for (var i = 0; i < _rules.length; i ++) {
      let _rule = _rules[i];
      let _node = {
        'id': _rule['id'],
        'data': {
          label: 
          (
            <>
              <Paper elevation={0} style={{maxWidth: nodeWidth-4, maxHeight: nodeHeight-4}}>
                <SyntaxHighlighter language="sql" style={vs} wrapLongLines={true}>
                  {_rule['pattern']}
                </SyntaxHighlighter>
              </Paper>
            </>
          ),
          rule: _rule
        },
        'position': { x: 0, y: 0 }
      };
      // append new node to nodes
      _nodes.push(_node);
    }
    // loop relations in _rulesGraph to build edges list
    let _relations = _rulesGraphData['relations'];
    let _edges = [];
    for (var i = 0; i < _relations.length; i ++) {
      let _relation = _relations[i];
      let _edge = {
        'id': i,
        'source': _relation['parentRuleId'],
        'target': _relation['childRuleId'],
        'markerEnd': {
          type: MarkerType.Arrow,
        },
      };
      // append new edge to edges
      _edges.push(_edge); 
    }
    // layout the nodes
    let { _nodes: layoutedNodes, _edges: layoutedEdges } = layoutNodesAndEdges(_nodes, _edges, 'LR');
    // update states for ReactFlow
    setNodes(_nodes);
    setEdges(_edges);
  };

  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const layoutNodesAndEdges = (_nodes, _edges, _direction = 'TB') => {
    const isHorizontal = _direction === 'LR';
    dagreGraph.setGraph({ rankdir: _direction });

    _nodes.forEach((_node) => {
      dagreGraph.setNode(_node.id, { width: nodeWidth, height: nodeHeight });
    });

    _edges.forEach((_edge) => {
      dagreGraph.setEdge(_edge.source, _edge.target);
    });

    dagre.layout(dagreGraph);

    _nodes.forEach((_node) => {
      const nodeWithPosition = dagreGraph.node(_node.id);
      _node.targetPosition = isHorizontal ? 'left' : 'top';
      _node.sourcePosition = isHorizontal ? 'right' : 'bottom';

      // We are shifting the dagre node position (anchor=center center) to the top left
      // so it matches the React Flow node anchor point (top left).
      _node.position = {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      };

      return _node;
    });

    return { nodes: _nodes, edges: _edges };
  };

  const onNodeClick = (_event, _node) => {
    setAnchorEl(_event.currentTarget);
    setPopRule(_node.data.rule);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };
  const open = Boolean(anchorEl);

  React.useEffect(() => {getRulesGraph(rewriteExamples, database);}, []);

  return (
    <Dialog
      open={modal.visible}
      onClose={() => modal.hide()}
      TransitionProps={{
        onExited: () => modal.remove(),
      }}
      fullWidth
      maxWidth={'xl'}
    >
        <DialogTitle>Rules Graph</DialogTitle>
        <DialogContent style={{height:'600px'}}>
        <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} fitView onNodeClick={onNodeClick} minZoom={0.05} >
          <Controls />
          <MiniMap/>
          <Popover
            open={open}
            anchorEl={anchorEl}
            onClose={handleClose}
            anchorOrigin={{
              vertical: 'center',
              horizontal: 'center',
            }}
            transformOrigin={{
              vertical: 'bottom',
              horizontal: 'left',
            }}
          >
            <Stack
              direction="row"
              divider={<Divider orientation="vertical" flexItem />}
            >
              <Paper elevation={0}>
                <SyntaxHighlighter language="sql" style={vs} wrapLongLines={true}>
                  {popRule['pattern']}
                </SyntaxHighlighter>
              </Paper>
              <Paper elevation={0}>
                <SyntaxHighlighter language="sql" style={vs} wrapLongLines={true}>
                  {popRule['rewrite']}
                </SyntaxHighlighter>
              </Paper>
            </Stack>
          </Popover>
        </ReactFlow>
        </DialogContent>
    </Dialog>
  );
});

export default RulesGraph;
