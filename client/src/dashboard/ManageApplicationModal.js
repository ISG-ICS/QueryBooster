import * as React from 'react';
import axios from 'axios';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Grid from '@mui/material/Grid';
import NiceModal, { useModal } from '@ebay/nice-modal-react';
import TextField from '@mui/material/TextField';


const ManageApplicationModal = NiceModal.create(({user_id, app=null}) => {
    const modal = useModal();
    // Set up states for an application
    const isNewApplication = !app;
    const [name, setName] = React.useState(isNewApplication ? "" : app.name);

    const onNameChange = (event) => {
        setName(event.target.value);
    };

    const onAddOrEdit = () => {
        if (name !== null && name.replace(/\s/g, '').length ) {

            // check if user is authenticated before sending the request
            if (!user_id) {
                alert("Please log in to save the application.");
                return;
            }

            // post saveApplication request to server
            const request = {
              'name': name,
              'id': isNewApplication ? -1 : app.id,
              'user_id': user_id
            };
            console.log('[/saveApplication] -> request:');
            console.log(request);
            axios.post('/saveApplication', request)
            .then(function (response) {
              console.log('[/saveApplication] -> response:');
              console.log(response);
              modal.resolve(response);
              modal.hide();
            })
            .catch(function (error) {
              console.log('[/saveApplication] -> error:');
              console.log(error);
            });
        }
    }

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
          <DialogTitle>{isNewApplication ? "Add Application" : "Edit Application"}</DialogTitle>
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
                      <Button type="submit" variant="contained" color="primary" onClick={onAddOrEdit}>Save</Button>
                    </Grid>
                  </Grid>  
                </Grid>    
            </Grid>
          </DialogContent>
        </Dialog>
    );
});

export default ManageApplicationModal;