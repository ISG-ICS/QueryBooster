import * as React from 'react';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Button from "@mui/material/Button";
import Title from './Title';


export default function JDBCDrivers() {

  const jdbcDrivers = [
    { database: "postgresql",
      version: "v42.3.3", 
      download: "postgresql-42.3.3-SNAPSHOT.jar", 
      href: "https://github.com/ISG-ICS/smart-pgjdbc/releases/download/smart_v42.3.3_new/postgresql-42.3.3-SNAPSHOT.jar",
      config: {
        download: "smart-pgjdbc.config", 
        href: "https://github.com/ISG-ICS/smart-pgjdbc/releases/download/smart_v42.3.3_new/smart-pgjdbc.config",
      }
    },
    { database: "mysql",
      version: "v8.0.28",
      download: "mysql-connector-java-8.0.28-SNAPSHOT.jar",
      href: "https://github.com/ISG-ICS/smart-mysql-connector-j/releases/download/smart_v8.0.28/mysql-connector-java-8.0.28-SNAPSHOT.jar"
    }
  ];

  const onDownload = (download, href) => {
    const link = document.createElement("a");
    link.download = download;
    link.href = href;
    link.click();
  };

  return (
    <React.Fragment>
      <Title>JDBC Drivers</Title>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Database</TableCell>
            <TableCell>Driver Version</TableCell>
            <TableCell>JDBC Driver</TableCell>
            <TableCell>Config File</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {jdbcDrivers.map((driver) => (
            <TableRow key={driver.database}>
              <TableCell>{driver.database}</TableCell>
              <TableCell>{driver.version}</TableCell>
              <TableCell>
                <Button onClick={() => onDownload(driver.download, driver.href)} variant="contained" color="primary">
                  Download
                </Button>
              </TableCell>
              <TableCell>
                <Button onClick={() => onDownload(driver.config.download, driver.config.href)} variant="contained" color="secondary">
                  Config File
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </React.Fragment>
  );
}
