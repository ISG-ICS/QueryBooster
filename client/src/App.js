import React from 'react';
import logo from './logo.svg';
import './App.css';
import Dashboard from './dashboard/Dashboard';
// user context
import {userContext} from './userContext';

function App() {
  document.title = 'QueryBooster';
  
  const [user, setUser] = React.useState({"id": 1, "email": "alice@ics.uci.edu"});

  return (
    <div className="App">
      {/* <header className="App-header">
        <img src={logo} className="App-logo" alt="logo" />
        <p>
          Edit <code>src/App.js</code> and save to reload.
        </p>
        <a
          className="App-link"
          href="https://reactjs.org"
          target="_blank"
          rel="noopener noreferrer"
        >
          Learn React
        </a>
      </header> */}
      <userContext.Provider value={user}>
        <Dashboard />
      </userContext.Provider>
    </div>
  );
}

export default App;
