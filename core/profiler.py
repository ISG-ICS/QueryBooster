import time

profiles = {}

class Profiler:

    @staticmethod
    def onFunctionStart(function: str) -> None:
        if function not in profiles.keys():
            profiles[function] = {'calls': 0, 'total_time': 0}
        profiles[function]['calls'] += 1
        profiles[function]['timer'] = {'start': time.time()}
        return
    
    @staticmethod
    def onFunctionEnd(function: str) -> None:
        if function not in profiles.keys():
            return
        start_time = profiles[function]['timer']['start']
        del profiles[function]['timer']
        end_time = time.time()
        timing = end_time - start_time
        profiles[function]['total_time'] += timing
        return

    @staticmethod
    def show() -> dict:
        return profiles
