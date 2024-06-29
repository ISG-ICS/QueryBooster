import * as React from 'react';
import { Box } from '@mui/material';

export default function FullLayout({ children }) {
  return (
    <Box sx={{ width: '80', height: '80vh', display: 'flex', flexDirection: 'column', overflow: 'hidden'}}>
      {children}
    </Box>
  );
}
