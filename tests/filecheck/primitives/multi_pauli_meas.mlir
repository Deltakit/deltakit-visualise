// RUN: %visualise "%s" -O %t.json && %filecheck "%s" --input-file %t.json
builtin.module {
    // Declare input patches
    %patch_A_0_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>
    %patch_B_0_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>
    %bridge_AB = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 1), location=(0.0, 3.0), orient=h_z>
    
    // Prepare input patches
    %patch_A_1_ = log_asm.prepare<Z> (%patch_A_0_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
    %patch_B_1_ = log_asm.prepare<X> (%patch_B_0_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>)
    
    // Initial measure stabilisers
    %patch_A_2_ = log_asm.meas_stab<3> (%patch_A_1_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
    %patch_B_2_ = log_asm.meas_stab<3> (%patch_B_1_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>)

    // multi-pauli
    %measurement_AB, %patch_A_3_, %patch_B_3_ = log_asm.multi_pauli_meas<3, (Z, Z)>
        (%patch_A_2_, %patch_B_2_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>,
                                !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>)
        (%bridge_AB : !log_asm.patch.rot_planar<size=(3, 1), location=(0.0, 3.0), orient=h_z>) -> i1
}
// Declare input patches
// CHECK: {"ops": [{"type": "surface", "id": "patch_A_0_", "op_name": "log_asm.patch_dec", "location": [0.0, 0.0], "colour": "GREY", "size": [3, 3], "startHeight": 0.0},
// CHECK-SAME: {"type": "surface", "id": "patch_B_0_", "op_name": "log_asm.patch_dec", "location": [0.0, 4.0], "colour": "GREY", "size": [3, 3], "startHeight": 0.0},
// CHECK-SAME: {"type": "surface", "id": "bridge_AB", "op_name": "log_asm.patch_dec", "location": [0.0, 3.0], "colour": "GREY", "size": [3, 1], "startHeight": 0.0},

// Prepare input patches
// CHECK-SAME: {"type": "surface", "id": "patch_A_1_", "op_name": "log_asm.prepare", "location": [0.0, 0.0], "colour": "BLUE", "size": [3, 3], "startHeight": 0.0},
// CHECK-SAME: {"type": "surface", "id": "patch_B_1_", "op_name": "log_asm.prepare", "location": [0.0, 4.0], "colour": "RED", "size": [3, 3], "startHeight": 0.0},

// Initial measure stabilisers
// CHECK-SAME: {"type": "surface", "id": "gen_id_0", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 0.0},
// CHECK-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_0", "toSurfaceId": "patch_A_2_"},
// CHECK-SAME: {"type": "surface", "id": "patch_A_2_", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 3.0},
// CHECK-SAME: {"type": "surface", "id": "gen_id_1", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 4.0], "size": [3, 3], "startHeight": 3.0},
// CHECK-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_1", "toSurfaceId": "patch_B_2_"},
// CHECK-SAME: {"type": "surface", "id": "patch_B_2_", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 4.0], "size": [3, 3], "startHeight": 6.0},

// multi-pauli logical patches
// CHECK-SAME: {"type": "surface", "id": "gen_id_2", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 6.0},
// CHECK-SAME: {"type": "side", "op_name": "log_asm.multi_pauli_meas", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": false, "-Y": true}, "fromSurfaceId": "gen_id_2", "toSurfaceId": "patch_A_3_"},
// CHECK-SAME: {"type": "surface", "id": "patch_A_3_", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 9.0},
// CHECK-SAME: {"type": "surface", "id": "gen_id_3", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [0.0, 4.0], "size": [3, 3], "startHeight": 6.0},
// CHECK-SAME: {"type": "side", "op_name": "log_asm.multi_pauli_meas", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": false}, "fromSurfaceId": "gen_id_3", "toSurfaceId": "patch_B_3_"},
// CHECK-SAME: {"type": "surface", "id": "patch_B_3_", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [0.0, 4.0], "size": [3, 3], "startHeight": 9.0},

// multi-pauli bridge patches
// CHECK-SAME: {"type": "surface", "id": "gen_id_4", "op_name": "log_asm.multi_pauli_meas", "colour": "RED", "location": [0.0, 3.0], "size": [3, 1], "startHeight": 6.0},
// CHECK-SAME: {"type": "side", "op_name": "log_asm.multi_pauli_meas", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": false, "-Y": false}, "fromSurfaceId": "gen_id_4", "toSurfaceId": "gen_id_5"},
// CHECK-SAME: {"type": "surface", "id": "gen_id_5", "op_name": "log_asm.multi_pauli_meas", "colour": "RED", "location": [0.0, 3.0], "size": [3, 1], "startHeight": 9.0}]}
