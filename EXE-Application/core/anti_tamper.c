/*
 * anti_tamper.c
 *
 * Native anti-tampering helpers exported by anti_tamper.dll.
 *
 * Exports:
 *   - check_hypervisor: reports whether the CPU hypervisor bit is set.
 *   - check_ntdll_hook: checks if NtQuerySystemInformation appears inline-hooked.
 *   - hide_all_threads: marks all current-process threads as hidden from a debugger.
 *   - check_api_patch: inspects critical anti-debug APIs for in-memory patching.
 *
 * Build (MinGW):
 *   gcc -O2 -shared -o anti_tamper.dll anti_tamper.c
 *
 * Build (MSVC x64 Native Tools):
 *   cl /nologo /O2 /W3 /LD anti_tamper.c /Fe:anti_tamper.dll
 */

#include <windows.h>
#include <tlhelp32.h>   /* CreateToolhelp32Snapshot, Thread32First/Next */
#include <intrin.h>
#include <stdint.h>
#include <stdio.h>

/* NT internal constants and structures used for process/thread enumeration. */
#define SystemProcessInformation  5
#define NT_SUCCESS(s)             ((NTSTATUS)(s) >= 0)
#define STATUS_INFO_LEN_MISMATCH  ((NTSTATUS)0xC0000004L)
#define ThreadHideFromDebugger    17

typedef LONG NTSTATUS;

/* Local UNICODE_STRING definition to avoid a hard dependency on winternl.h. */
typedef struct _UNICODE_STRING {
    USHORT Length;
    USHORT MaximumLength;
    PWSTR  Buffer;
} UNICODE_STRING;

typedef struct _SYSTEM_THREAD_INFORMATION {
    LARGE_INTEGER KernelTime;
    LARGE_INTEGER UserTime;
    LARGE_INTEGER CreateTime;
    ULONG         WaitTime;
    PVOID         StartAddress;
    union { struct { ULONG_PTR UniqueProcess; ULONG_PTR UniqueThread; }; } ClientId;
    LONG          Priority;
    LONG          BasePriority;
    ULONG         ContextSwitchCount;
    ULONG         State;
    ULONG         WaitReason;
} SYSTEM_THREAD_INFORMATION;

typedef struct _SYSTEM_PROCESS_INFORMATION {
    ULONG                     NextEntryOffset;
    ULONG                     NumberOfThreads;
    LARGE_INTEGER             Reserved[3];
    LARGE_INTEGER             CreateTime;
    LARGE_INTEGER             UserTime;
    LARGE_INTEGER             KernelTime;
    UNICODE_STRING            ImageName;
    LONG                      BasePriority;
    HANDLE                    UniqueProcessId;
    HANDLE                    InheritedFromUniqueProcessId;
    ULONG                     HandleCount;
    ULONG                     SessionId;
    ULONG_PTR                 PageDirectoryBase;
    SIZE_T                    PeakVirtualSize;
    SIZE_T                    VirtualSize;
    ULONG                     PageFaultCount;
    SIZE_T                    PeakWorkingSetSize;
    SIZE_T                    WorkingSetSize;
    SIZE_T                    QuotaPeakPagedPoolUsage;
    SIZE_T                    QuotaPagedPoolUsage;
    SIZE_T                    QuotaPeakNonPagedPoolUsage;
    SIZE_T                    QuotaNonPagedPoolUsage;
    SIZE_T                    PagefileUsage;
    SIZE_T                    PeakPagefileUsage;
    SIZE_T                    PrivatePageCount;
    LARGE_INTEGER             ReadOperationCount;
    LARGE_INTEGER             WriteOperationCount;
    LARGE_INTEGER             OtherOperationCount;
    LARGE_INTEGER             ReadTransferCount;
    LARGE_INTEGER             WriteTransferCount;
    LARGE_INTEGER             OtherTransferCount;
    SYSTEM_THREAD_INFORMATION Threads[1];
} SYSTEM_PROCESS_INFORMATION;

typedef NTSTATUS (WINAPI *PFN_NtQuerySystemInformation)(
    ULONG  SystemInformationClass,
    PVOID  pSystemInformation,
    ULONG  uSystemInformationLength,
    PULONG puReturnLength
);

typedef NTSTATUS (WINAPI *PFN_NtSetInformationThread)(
    HANDLE ThreadHandle,
    ULONG  ThreadInformationClass,
    PVOID  pThreadInformation,
    ULONG  uThreadInformationLength
);

/*
 * Note on hook detection:
 * This implementation uses fast byte-pattern heuristics at function entry.
 * It is intentionally lightweight and may miss advanced trampolines that
 * preserve a clean prologue or use page-level indirection.
 */

/*
 * Heuristically detect common inline-hook prologue patterns.
 * Returns:
 *   1 if the function appears hooked,
 *   0 if no known pattern is detected,
 *  -1 if fn is NULL.
 */
static int _prologue_hooked(const void *fn)
{
    if (!fn) return -1;
    const unsigned char *b = (const unsigned char *)fn;

    /* JMP rel32 */
    if (b[0] == 0xE9) return 1;
    /* JMP short */
    if (b[0] == 0xEB) return 1;
    /* Indirect JMP [rip+...] */
    if (b[0] == 0xFF && b[1] == 0x25) return 1;
    /* MOV RAX, imm64 / JMP RAX style detour */
    if (b[0] == 0x48 && b[1] == 0xB8) return 1;
    /* NOP sled */
    if (b[0] == 0x90 && b[1] == 0x90) return 1;
    /* PUSH imm32 / RET */
    if (b[0] == 0x68 && b[4] == 0xC3) return 1;
    return 0;
}

/*
 * Return 1 when CPUID indicates a hypervisor is present, otherwise 0.
 */
__declspec(dllexport) int check_hypervisor(void)
{
    int info[4] = { 0 };
    __cpuid(info, 0x1);
    return (info[2] >> 31) & 1;   /* ECX bit 31 */
}

/*
 * Check whether ntdll!NtQuerySystemInformation appears inline-hooked.
 * Returns: 1 = hooked, 0 = clean, -1 = ntdll/function unavailable.
 */
__declspec(dllexport) int check_ntdll_hook(void)
{
    HMODULE hNt = GetModuleHandleA("ntdll.dll");
    if (!hNt) return -1;

    const void *fn = GetProcAddress(hNt, "NtQuerySystemInformation");
    return _prologue_hooked(fn);
}

/*
 * Hide all current-process threads from an attached debugger.
 *
 * Strategy:
 *   1) Prefer NtQuerySystemInformation for full process/thread enumeration
 *      when the API itself appears unmodified.
 *   2) Fall back to Toolhelp thread snapshots when NtQuerySystemInformation
 *      appears hooked or enumeration fails.
 *
 * Return value:
 *   >=0 : number of threads processed
 *   -1  : ntdll module unavailable
 *   -2  : NtSetInformationThread unavailable
 *   -3  : Toolhelp snapshot failure in fallback path
 */
__declspec(dllexport) int hide_all_threads(void)
{
    HMODULE hNt = GetModuleHandleA("ntdll.dll");
    if (!hNt) return -1;

    PFN_NtSetInformationThread NtSetInfoThread =
        (PFN_NtSetInformationThread)GetProcAddress(hNt, "NtSetInformationThread");
    if (!NtSetInfoThread) return -2;

    DWORD myPid = GetCurrentProcessId();
    int   count = 0;

    /* Path A (preferred): enumerate via NtQuerySystemInformation. */
    int ntdll_hooked = check_ntdll_hook();

    if (ntdll_hooked == 0) {
        PFN_NtQuerySystemInformation NtQSI =
            (PFN_NtQuerySystemInformation)GetProcAddress(hNt, "NtQuerySystemInformation");

        /* Start with a fixed buffer and resize once if the kernel reports it
         * was too small. This keeps the call path simple and deterministic. */
        ULONG  bufLen = 1 << 20;  /* Initial 1 MB buffer. */
        PVOID  pBuf   = HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, bufLen);
        if (!pBuf) goto fallback;

        ULONG    retLen = 0;
        NTSTATUS st = NtQSI(SystemProcessInformation, pBuf, bufLen, &retLen);
        if (st == STATUS_INFO_LEN_MISMATCH) {
            HeapFree(GetProcessHeap(), 0, pBuf);
            /* Add padding to reduce the chance of a second size mismatch due
             * to process/thread churn between sizing and retry. */
            bufLen = retLen + 4096;
            pBuf   = HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, bufLen);
            if (!pBuf) goto fallback;
            st = NtQSI(SystemProcessInformation, pBuf, bufLen, &retLen);
        }

        if (NT_SUCCESS(st)) {
            SYSTEM_PROCESS_INFORMATION *e = (SYSTEM_PROCESS_INFORMATION *)pBuf;
            for (;;) {
                /* SYSTEM_PROCESS_INFORMATION records form a variable-length
                 * linked list using byte offsets rather than pointers. */
                if ((DWORD)(ULONG_PTR)e->UniqueProcessId == myPid) {
                    for (ULONG i = 0; i < e->NumberOfThreads; ++i) {
                        DWORD  tid = (DWORD)(ULONG_PTR)e->Threads[i].ClientId.UniqueThread;
                        HANDLE h   = OpenThread(THREAD_SET_INFORMATION, FALSE, tid);
                        if (h) {
                            NtSetInfoThread(h, ThreadHideFromDebugger, NULL, 0);
                            CloseHandle(h);
                            ++count;
                        }
                    }
                    break;
                }
                if (!e->NextEntryOffset) break;
                e = (SYSTEM_PROCESS_INFORMATION *)((BYTE *)e + e->NextEntryOffset);
            }
        }
        HeapFree(GetProcessHeap(), 0, pBuf);
        /* If no thread was hidden through the preferred path, continue to the
         * fallback enumerator instead of returning 0 immediately. */
        if (count > 0) return count;
    }

fallback:
    /* Path B (fallback): Toolhelp snapshot, independent of NtQSI output. */
    {
        HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
        if (snap == INVALID_HANDLE_VALUE) return -3;

        THREADENTRY32 te;
        te.dwSize = sizeof(te);
        if (Thread32First(snap, &te)) {
            do {
                /* Restrict to this process only; then apply
                 * ThreadHideFromDebugger to each owned thread. */
                if (te.th32OwnerProcessID == myPid) {
                    HANDLE h = OpenThread(THREAD_SET_INFORMATION, FALSE, te.th32ThreadID);
                    if (h) {
                        NtSetInfoThread(h, ThreadHideFromDebugger, NULL, 0);
                        CloseHandle(h);
                        ++count;
                    }
                }
            } while (Thread32Next(snap, &te));
        }
        CloseHandle(snap);
    }
    return count;
}

/*
 * Detect suspicious in-memory patching on anti-debug related APIs.
 *
 * Checked targets:
 *   - kernel32!IsDebuggerPresent
 *   - kernel32!CheckRemoteDebuggerPresent
 *   - ntdll!NtQueryInformationProcess
 *   - ntdll!NtSetInformationThread
 *
 * Returns:
 *   1  = patch/hook signature detected
 *   0  = no known signature detected
 *  -1  = required module resolution failure
 *  -2  = required symbol resolution failure
 */
__declspec(dllexport) int check_api_patch(void)
{
    HMODULE hK32 = GetModuleHandleA("kernel32.dll");
    HMODULE hNt  = GetModuleHandleA("ntdll.dll");
    if (!hK32 || !hNt) return -1;

    /* Check IsDebuggerPresent byte patterns. */
    {
        const unsigned char *b =
            (const unsigned char *)GetProcAddress(hK32, "IsDebuggerPresent");
        if (!b) return -2;

        if (_prologue_hooked(b))                          return 1;
        /* MOV EAX,0 / RETN can force a "not debugging" result. */
        if (b[0]==0xB8 && b[1]==0x00 && b[2]==0x00)      return 1;
        /* MOV EAX,1 / RETN is also suspicious for this API. */
        if (b[0]==0xB8 && b[1]==0x01 && b[5]==0xC3)      return 1;
        /* XOR EAX,EAX / RETN */
        if (b[0]==0x33 && b[1]==0xC0)                    return 1;
        /* RET immediately */
        if (b[0]==0xC3)                                   return 1;
    }

    /* Check CheckRemoteDebuggerPresent for hook prologue signatures. */
    {
        const void *fn = GetProcAddress(hK32, "CheckRemoteDebuggerPresent");
        if (_prologue_hooked(fn) == 1)                    return 1;
    }

    /* Check NtQueryInformationProcess, a frequent anti-debug bypass target. */
    {
        const void *fn = GetProcAddress(hNt, "NtQueryInformationProcess");
        if (_prologue_hooked(fn) == 1)                    return 1;
    }

    /* Check NtSetInformationThread, which can be patched to disable hiding. */
    {
        const void *fn = GetProcAddress(hNt, "NtSetInformationThread");
        if (_prologue_hooked(fn) == 1)                    return 1;
    }

    return 0;
}

/* Standard DLL entry point; no initialization is required. */
BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved)
{
    (void)h; (void)reason; (void)reserved;
    return TRUE;
}
