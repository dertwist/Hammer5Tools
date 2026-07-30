import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import ctypes

# Add repo root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.forms.mapbuilder.system_monitor import GPUStatsWorker

def test_intel_stats_collection():
    worker = GPUStatsWorker()

    # Mock ctypes.CDLL
    mock_lib = MagicMock()

    # Mock zesInit to return success (0)
    mock_lib.zesInit = MagicMock(return_value=0)

    # Mock zesDriverGet to return count of 1 and then driver handle pointer
    def mock_zesDriverGet(pCount, phDrivers):
        if not phDrivers:
            pCount.contents.value = 1
        else:
            phDrivers[0] = 12345 # dummy driver handle
        return 0
    mock_lib.zesDriverGet = mock_zesDriverGet

    # Mock zesDeviceGet to return count of 1 and then device handle
    def mock_zesDeviceGet(hDriver, pCount, phDevices):
        if not phDevices:
            pCount.contents.value = 1
        else:
            phDevices[0] = 67890 # dummy device handle
        return 0
    mock_lib.zesDeviceGet = mock_zesDeviceGet

    # Mock zesDeviceEnumMemoryModules to return 1 module
    def mock_zesDeviceEnumMemoryModules(hDevice, pCount, phMemory):
        if not phMemory:
            pCount.contents.value = 1
        else:
            phMemory[0] = 11111 # dummy memory module handle
        return 0
    mock_lib.zesDeviceEnumMemoryModules = mock_zesDeviceEnumMemoryModules

    # Mock zesMemoryGetProperties to return location = 1 (DEVICE) and physicalSize = 8GB
    def mock_zesMemoryGetProperties(hMemory, pProperties):
        pProperties.contents.location = 1 # ZES_MEM_LOC_DEVICE
        pProperties.contents.physicalSize = 8589934592 # 8GB
        return 0
    mock_lib.zesMemoryGetProperties = mock_zesMemoryGetProperties

    # Mock zesMemoryGetState to return 2GB free and 8GB total size
    def mock_zesMemoryGetState(hMemory, pState):
        pState.contents.free = 2147483648 # 2GB free
        pState.contents.size = 8589934592 # 8GB size
        return 0
    mock_lib.zesMemoryGetState = mock_zesMemoryGetState

    # Mock zesDeviceEnumEngineGroups to return 1 engine group
    def mock_zesDeviceEnumEngineGroups(hDevice, pCount, phEngine):
        if not phEngine:
            pCount.contents.value = 1
        else:
            phEngine[0] = 22222 # dummy engine group handle
        return 0
    mock_lib.zesDeviceEnumEngineGroups = mock_zesDeviceEnumEngineGroups

    # Mock zesEngineGetProperties to return type = 0 (ZES_ENGINE_GROUP_ALL)
    def mock_zesEngineGetProperties(hEngine, pProperties):
        pProperties.contents.type = 0 # ZES_ENGINE_GROUP_ALL
        return 0
    mock_lib.zesEngineGetProperties = mock_zesEngineGetProperties

    # Mock zesEngineGetActivity to return dynamic stats
    activity_calls = []
    def mock_zesEngineGetActivity(hEngine, pStats):
        if len(activity_calls) == 0:
            pStats.contents.activeTime = 1000000
            pStats.contents.timestamp = 2000000
        else:
            pStats.contents.activeTime = 1500000 # +500ms active
            pStats.contents.timestamp = 3000000  # +1000ms elapsed -> 50% usage
        activity_calls.append(True)
        return 0
    mock_lib.zesEngineGetActivity = mock_zesEngineGetActivity

    with patch("ctypes.CDLL", return_value=mock_lib), \
         patch("ctypes.byref", ctypes.pointer):
        # First call: should initialize and return 0.0 usage
        stats1 = worker._get_intel_stats()
        assert stats1 is not None
        usage1, used1, total1 = stats1
        assert usage1 == 0.0
        assert abs(used1 - 6.0) < 0.01  # 8GB - 2GB free = 6GB used
        assert abs(total1 - 8.0) < 0.01  # 8GB total

        # Second call: should compute 50.0% usage based on delta activeTime / timestamp
        stats2 = worker._get_intel_stats()
        assert stats2 is not None
        usage2, used2, total2 = stats2
        assert abs(usage2 - 50.0) < 0.01
        assert abs(used2 - 6.0) < 0.01
        assert abs(total2 - 8.0) < 0.01

    print("All mock Level-Zero Sysman tests passed successfully!")

if __name__ == "__main__":
    test_intel_stats_collection()
