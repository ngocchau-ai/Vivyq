#include <windows.h>
#include <iostream>
#include <cstring>
#include "vivyqu/types.h"

typedef int32_t (*fn_init)();
typedef int32_t (*fn_step)(const vivyqu::VivyquInputFrame*, vivyqu::VivyquOutputFrame*);
typedef const char* (*fn_ver)();

int main() {
    HMODULE hDll = LoadLibraryA("build/bin/vivyqu_core.dll");
    if (!hDll) {
        std::cerr << "Failed to load DLL! Error: " << GetLastError() << std::endl;
        return 1;
    }

    fn_init pInit = (fn_init)GetProcAddress(hDll, "vivyqu_core_init");
    fn_step pStep = (fn_step)GetProcAddress(hDll, "vivyqu_core_step");
    fn_ver  pVer  = (fn_ver)GetProcAddress(hDll, "vivyqu_core_version");

    std::cout << "Version: " << pVer() << std::endl;
    pInit();

    vivyqu::VivyquInputFrame in{};
    vivyqu::VivyquOutputFrame out{};
    in.magic_header = vivyqu::MAGIC_INPUT_FRAME;
    in.sequence_id = 1;
    in.version = vivyqu::ABI_VERSION_1_0;
    std::memset(in.constraint_bitmask, 0xFF, 512);
    for (int i = 0; i < 4096; ++i) in.latent_vector[i] = 0.05;

    std::cout << "Calling step via dynamically loaded DLL..." << std::endl;
    int rc = pStep(&in, &out);
    std::cout << "Dynamic DLL call SUCCESS! rc = " << rc << ", best = " << out.best_decision_idx << std::endl;

    FreeLibrary(hDll);
    return 0;
}
