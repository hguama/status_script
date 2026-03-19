import ctypes
from ctypes import wintypes
import threading
import keyboard
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi

# Corrección de punteros de 64 bits para evitar ERROR 126 (Truncamiento en ctypes)
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
user32.SetWindowsHookExW.restype = ctypes.c_void_p
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, ctypes.c_void_p, wintypes.HMODULE, wintypes.DWORD]

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_KEYUP = 0x0101
WM_SYSKEYUP = 0x0105

VK_LMENU = 0xA4
VK_RMENU = 0xA5
VK_MENU = 0x12
VK_LEFT = 0x25
VK_RIGHT = 0x27

HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong))

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.c_ulong),
        ("scanCode", ctypes.c_ulong),
        ("flags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]

pressed_keys = {
    VK_LEFT: False,
    VK_RIGHT: False
}

track_alt = False
consumed_alt = False

def get_active_process_name():
    hwnd = user32.GetForegroundWindow()
    if not hwnd: return ""
    pid = ctypes.c_ulong(0)
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010
    try:
        hProcess = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
        if not hProcess: return ""
        executable_path = ctypes.create_unicode_buffer(260)
        if psapi.GetModuleFileNameExW(hProcess, 0, executable_path, ctypes.sizeof(executable_path) // 2):
            name = executable_path.value.split('\\')[-1]
            kernel32.CloseHandle(hProcess)
            return name
        kernel32.CloseHandle(hProcess)
    except:
        pass
    return ""

def is_onenote_active():
    return get_active_process_name().lower() == "onenote.exe"

def enviar_comando_sin_alt(key_to_press):
    time.sleep(0.01)
    
    # 1. Inyectamos Ctrl Down. Aborta posible menú Ribbon
    keyboard.press("ctrl")
    time.sleep(0.005)
    
    # 2. Soltamos el Alt físico (lógicamente)
    keyboard.release("alt")
    keyboard.release("left alt")
    time.sleep(0.005)
    
    # 3. Presionamos y soltamos la tecla de forma manual y transparente
    keyboard.press(key_to_press)
    time.sleep(0.005)
    keyboard.release(key_to_press)
    
    # 4. Soltamos Ctrl
    time.sleep(0.005)
    keyboard.release("ctrl")

hook_id = None
hook_proc_ref = None 

def hook_proc(nCode, wParam, lParam):
    global track_alt, consumed_alt
    if nCode < 0:
        return user32.CallNextHookEx(hook_id, nCode, wParam, lParam)

    try:
        kb_struct = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        vk = kb_struct.vkCode
        is_injected = (kb_struct.flags & 0x10) != 0

        if not is_injected:
            if vk in (VK_LMENU, VK_RMENU, VK_MENU):
                if wParam == WM_KEYDOWN or wParam == WM_SYSKEYDOWN:
                    track_alt = True
                    consumed_alt = False
                elif wParam == WM_KEYUP or wParam == WM_SYSKEYUP:
                    track_alt = False
                    if consumed_alt:
                        return 1 # Bloqueamos el "Up" para prevenir el foco en el Ribbon
            
            elif vk in (VK_LEFT, VK_RIGHT):
                if track_alt and is_onenote_active():
                    if wParam == WM_KEYDOWN or wParam == WM_SYSKEYDOWN:
                        consumed_alt = True
                        if not pressed_keys.get(vk, False):
                            pressed_keys[vk] = True
                            if vk == VK_LEFT:
                                threading.Thread(target=enviar_comando_sin_alt, args=('page up',)).start()
                            elif vk == VK_RIGHT:
                                threading.Thread(target=enviar_comando_sin_alt, args=('page down',)).start()
                    
                    elif wParam == WM_KEYUP or wParam == WM_SYSKEYUP:
                        pressed_keys[vk] = False
                    
                    return 1 # Ocultamos la flecha a Windows original

    except Exception:
        pass

    return user32.CallNextHookEx(hook_id, nCode, wParam, lParam)

def start_onenote_hook():
    global hook_id, hook_proc_ref
    hook_proc_ref = HOOKPROC(hook_proc)
    hook_id = user32.SetWindowsHookExW(WH_KEYBOARD_LL, hook_proc_ref, kernel32.GetModuleHandleW(None), 0)
    
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))

def run_in_background():
    t = threading.Thread(target=start_onenote_hook, daemon=True)
    t.start()
