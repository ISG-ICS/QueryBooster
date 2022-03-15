import * as React from 'react';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Button from "@mui/material/Button";
import Title from './Title';


export default function JDBCDrivers() {

  const onDownload = () => {
    const link = document.createElement("a");
    link.download = `postgresql-42.3.2-SNAPSHOT.jar`;
    link.href = "./postgresql-42.3.2-SNAPSHOT.jar";
    link.click();
  };

  return (
    <React.Fragment>
      <Title>JDBC Drivers</Title>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Database</TableCell>
            <TableCell>JDBC Driver</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          <TableRow>
            <TableCell>PostgreSQL</TableCell>
            <TableCell>
              <Button onClick={onDownload} variant="contained" color="primary">
                Download
              </Button>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </React.Fragment>
  );
}
