#include "vivyqu/c_api.h"
#include <iostream>
#include <cstring>

int main() {
    std::cout << "Initializing Core..." << std::endl;
    int init_rc = vivyqu_core_init();
    std::cout << "init_rc = " << init_rc << std::endl;

    std::cout << "Loading E9 weights from data/e9_weights.bin..." << std::endl;
    int load_rc = vivyqu_core_load_e9_weights("data/e9_weights.bin");
    std::cout << "load_rc = " << load_rc << std::endl;

    vivyqu::VivyquInputFrame in{};
    vivyqu::VivyquOutputFrame out{};
    in.magic_header = vivyqu::MAGIC_INPUT_FRAME;
    in.sequence_id = 1;
    in.version = vivyqu::ABI_VERSION_1_0;
    in.mode_flags = vivyqu::MODE_GEOMETRIC_E9;
    std::memset(in.constraint_bitmask, 0xFF, 512);
    for (int i = 0; i < 4096; ++i) in.latent_vector[i] = 0.05;
    
    std::cout << "Calling step_e9 from C++..." << std::endl;
    int rc = vivyqu_core_step_e9(&in, &out);
    std::cout << "Done! rc = " << rc << ", best = " << out.best_decision_idx 
              << ", conf = " << out.best_confidence 
              << ", latency = " << out.latency_core_ns << " ns" << std::endl;
    return 0;
}
