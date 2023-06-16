import React from 'react';
import ReactDOM from 'react-dom';
import { BrowserRouter } from "react-router-dom";
import './index.css';
import App from './App';
import NiceModal from '@ebay/nice-modal-react';
import reportWebVitals from './reportWebVitals';
import 'fontsource-roboto'
import { GoogleOAuthProvider } from '@react-oauth/google';

ReactDOM.render(
  <GoogleOAuthProvider clientId="536149484005-0rcbnt8rh458jcg806cf1e44o17fs86f.apps.googleusercontent.com">
    <React.StrictMode>
      <BrowserRouter>
        <NiceModal.Provider>
          <App />
        </NiceModal.Provider>
      </BrowserRouter>
    </React.StrictMode>
  </GoogleOAuthProvider>,
  document.getElementById('root')
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
