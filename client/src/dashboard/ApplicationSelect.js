import React, { useState, useCallback } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import DialogActions from '@mui/material/DialogActions';
import NiceModal, { useModal } from '@ebay/nice-modal-react';
import axios from 'axios';
import defaultApplicationsData from '../mock-api/listApplications';

const ApplicationSelect = NiceModal.create(({ user }) => {
    const modal = useModal();
    // Set up a state for list of applications
    const [applications, setApplications] = React.useState([]);
    // Set up a state for selected application Id
    const [selectedAppId, setSelectedAppId] = useState(-1);

    const handleSelectChange = (event) => {
        setSelectedAppId(event.target.value);
    };

    // initial loading applications for the current user from server
    const listApplications = (user) => {
        console.log('[/listApplications] -> request:');
        console.log('  user_id: ' + user.id);
        // post listApplications request to server
        axios.post('/listApplications', { 'user_id': user.id })
            .then(function (response) {
                console.log('[/listApplications] -> response:');
                console.log(response);
                // update the state for list of applications
                setApplications(response.data);
            })
            .catch(function (error) {
                console.log('[/listApplications] -> error:');
                console.log(error);
                // mock the result
                console.log(defaultApplicationsData);
                setApplications(defaultApplicationsData);
            });
    };

    // call listApplications() only once after initial rendering
    React.useEffect(() => { listApplications(user) }, []);

    const handleSubmit = useCallback(() => {
        const selectedApplication = applications.find((app) => app.id == selectedAppId);
        console.log("[ApplicationSelect] selectedAppId = " + selectedAppId);
        console.log("[ApplicationSelect] applications = ");
        console.log(applications);
        console.log("[ApplicationSelect] find selected application = ");
        console.log(selectedApplication);
        modal.resolve(selectedApplication);
        modal.hide();
    }, [modal]);

    return (
        <Dialog
            open={modal.visible}
            onClose={() => modal.hide()}
            TransitionProps={{
                onExited: () => modal.remove(),
            }}
            maxWidth={'sm'}
        >
            <DialogTitle>Enable Rule for Application</DialogTitle>
            <DialogContent>
                <Box>
                    <select value={selectedAppId} onChange={handleSelectChange}>
                        <option value={-1} key={-1}>Select...</option>
                        {applications.map((app) => (
                            <option value={app.id} key={app.id}>{app.name}</option>
                        ))}
                    </select>
                </Box>
            </DialogContent>
            <DialogActions>
                <Button type="submit" variant="contained" color="primary" onClick={handleSubmit}>Confirm</Button>
            </DialogActions>
        </Dialog>
    );
});

export default ApplicationSelect;