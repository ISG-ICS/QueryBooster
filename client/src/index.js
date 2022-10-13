import React from 'react';
import ReactDOM from 'react-dom';
import { BrowserRouter } from "react-router-dom";
import './index.css';
import App from './App';
import NiceModal from '@ebay/nice-modal-react';
import reportWebVitals from './reportWebVitals';
import 'fontsource-roboto'

ReactDOM.render(
  <React.StrictMode>
    <BrowserRouter>
      <NiceModal.Provider>
        <App />
      </NiceModal.Provider>
    </BrowserRouter>
  </React.StrictMode>,
  document.getElementById('root')
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
