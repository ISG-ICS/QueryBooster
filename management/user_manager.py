import sys
# append the path of the parent directory
sys.path.append("..")
from management.data_manager import DataManager


class UserManager:

    def __init__(self, dm: DataManager) -> None:
        self.dm = dm
    
    def __del__(self):
        del self.dm

    def create_user(self, user: dict) -> bool:
        return self.dm.create_user(user)
