import * as React from 'react';
import axios from 'axios';
import { useModal } from '@ebay/nice-modal-react';
import ApplicationSelect from './ApplicationSelect';
import {userContext} from '../userContext';

function AppTagCell({ruleId: initialRuleId, tags: initialApps }) {
  const [ruleId, setRule] = React.useState(initialRuleId);
  const [apps, setApps] = React.useState(initialApps);
  // Set up a state for providing forceUpdate function
  const [, updateState] = React.useState();
  const forceUpdate = React.useCallback(() => updateState({}), []);

  const applicationSelectModal = useModal(ApplicationSelect);

  const user = React.useContext(userContext);

  function handleSelect(selectedApplication) {
    if (selectedApplication) {
      // post enableRule request to server
      axios.post('/enableRule', {'rule': {'id': ruleId}, 'app': selectedApplication})
      .then(function (response) {
        console.log('[/enableRule] -> response:');
        console.log(response);
        setApps([...apps, {'app_id': selectedApplication.id, 'app_name': selectedApplication.name}]);
        forceUpdate();
      })
      .catch(function (error) {
        console.log('[/enableRule] -> error:');
        console.log(error);
        // TODO - alter the entered application name doest not exist
      });
    }
  }
  
  const handleAddApp = React.useCallback(() => {
    applicationSelectModal.show({user}).then((selectedApplication) => {
      console.log("[ApplicationTag] selectedApplication = ");
      console.log(selectedApplication);
      handleSelect(selectedApplication);
    });
  }, [applicationSelectModal]);

  function handleRemoveApp(app) {
    // post disableRule request to server
    axios.post('/disableRule', {'rule': {'id': ruleId}, 'app': {'id': app.app_id, 'name': app.app_name}})
    .then(function (response) {
      console.log('[/disableRule] -> response:');
      console.log(response);
      const updatedApps = apps.filter((a) => a !== app);
      setApps(updatedApps);
      forceUpdate();
    })
    .catch(function (error) {
      console.log('[/disableRule] -> error:');
      console.log(error);
    });
  }

  return (
    <div>
      {apps.map((app) => (
        <span key={app.app_id} className="tag">
          {app.app_name}
          <button
            className="delete-button"
            onClick={() => handleRemoveApp(app)}
          >
            x
          </button>
        </span>
      ))}
      <button onClick={handleAddApp}>+</button>
    </div>
  );
}
  
export default AppTagCell;  
