"""Windows Job Object management for child process lifecycle control.

Assigns the current process to a Windows Job Object configured with
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE (0x2000). Any child process spawned by
Hammer 5 Tools (dotnet bridge, resourcecompiler, ffmpeg, git, bspsrc, etc.)
will automatically be terminated by the Windows kernel if the main process
exits, is terminated, or crashes.
"""
import sys
import ctypes
from typing import Optional

_job_handle = None


def install_job_object() -> Optional[int]:
    """Create a Windows Job Object and assign the current process to it."""
    global _job_handle

    if sys.platform != 'win32':
        return None

    if _job_handle is not None:
        return _job_handle

    try:
        from ctypes import wintypes

        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
        JOB_OBJECT_LIMIT_BREAKAWAY_OK = 0x0800
        JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK = 0x1000
        JobObjectExtendedLimitInformation = 9

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [
                ('ReadOperationCount', ctypes.c_uint64),
                ('WriteOperationCount', ctypes.c_uint64),
                ('OtherOperationCount', ctypes.c_uint64),
                ('ReadTransferCount', ctypes.c_uint64),
                ('WriteTransferCount', ctypes.c_uint64),
                ('OtherTransferCount', ctypes.c_uint64),
            ]

        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ('PerProcessUserTimeLimit', ctypes.c_int64),
                ('PerJobUserTimeLimit', ctypes.c_int64),
                ('LimitFlags', wintypes.DWORD),
                ('MinimumWorkingSetSize', ctypes.c_size_t),
                ('MaximumWorkingSetSize', ctypes.c_size_t),
                ('ActiveProcessLimit', wintypes.DWORD),
                ('Affinity', ctypes.c_size_t),
                ('PriorityClass', wintypes.DWORD),
                ('SchedulingClass', wintypes.DWORD),
            ]

        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ('BasicLimitInformation', JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ('IoCounters', IO_COUNTERS),
                ('ProcessMemoryLimit', ctypes.c_size_t),
                ('JobMemoryLimit', ctypes.c_size_t),
                ('PeakProcessMemoryLimit', ctypes.c_size_t),
                ('PeakJobMemoryLimit', ctypes.c_size_t),
            ]

        kernel32 = ctypes.windll.kernel32
        kernel32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL

        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return None

        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = (
            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            | JOB_OBJECT_LIMIT_BREAKAWAY_OK
            | JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK
        )

        success = kernel32.SetInformationJobObject(
            job,
            JobObjectExtendedLimitInformation,
            ctypes.byref(info),
            ctypes.sizeof(info)
        )
        if not success:
            kernel32.CloseHandle(job)
            return None

        cur_proc = kernel32.GetCurrentProcess()
        if not kernel32.AssignProcessToJobObject(job, cur_proc):
            # Process may already belong to an incompatible nested job on older Windows
            kernel32.CloseHandle(job)
            return None

        _job_handle = job
        return job
    except Exception as e:
        print(f"[Hammer5Tools] Failed to initialize Windows Job Object: {e}", file=sys.stderr)
        return None


def is_job_object_active() -> bool:
    """Return True if the job object is active and attached."""
    return _job_handle is not None
