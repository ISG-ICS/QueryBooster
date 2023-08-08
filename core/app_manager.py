import sys
# append the path of the parent directory
sys.path.append("..")
from core.data_manager import DataManager


class AppManager:

    def __init__(self, dm: DataManager) -> None:
        self.dm = dm
    
    def __del__(self):
        del self.dm

    def list_applications(self, user_id: str) -> list:
        applications = self.dm.list_applications(user_id)
        res = []
        for app in applications:
            res.append({
                'id': app[0],
                'name': app[1]
            })
        return res
    
    def save_applications(self, app: dict) -> bool:
        return self.dm.add_or_edit_application(app)

    def delete_application(self, app: dict) -> bool:
        return self.dm.delete_application(app)
