// RUN: %visualise "%s" -O %t.json && %filecheck "%s" --input-file %t.json
builtin.module {

    // Declare input patches
    %patch_A_0_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>
    %patch_B_0_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>

    // Prepare input patches
    // (Since many ops don't change the type of the result - the `->` [type] part of the normal mlir operation syntax is omitted
    // from the dialect where possible. The return type of prepare is just the same as the operand type.)
    %patch_A_1_ = log_asm.prepare<Z> (%patch_A_0_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
    %patch_B_1_ = log_asm.prepare<Z> (%patch_B_0_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)

    // Initial measure stabilisers
    %patch_A_2_ = log_asm.meas_stab<3> (%patch_A_1_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
    %patch_B_2_ = log_asm.meas_stab<3> (%patch_B_1_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)

    // Declare and prepare patches for the first multi-pauli
    %patch_C_1_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>
    %patch_C_2_ = log_asm.prepare<X> (%patch_C_1_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>)
    %bridgeAC_2_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 1), location=(0.0, 3.0), orient=h_z>

    // First multi-pauli
    // The return types are i1 followed simply by the types of the logical patch operands, so these are not repeated in the syntax.
    %measurement_AC, %patch_A_3_, %patch_C_3_ = log_asm.multi_pauli_meas<3, (Z, Z)>
        (%patch_A_2_, %patch_C_2_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>,
                                !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>)
        (%bridgeAC_2_ : !log_asm.patch.rot_planar<size=(3, 1), location=(0.0, 3.0), orient=h_z>) -> i1

    // Stabilisers on all the logical patches
    %patch_A_4_ = log_asm.meas_stab<3> (%patch_A_3_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
    %patch_B_4_ = log_asm.meas_stab<3> (%patch_B_2_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)
    %patch_C_4_ = log_asm.meas_stab<3> (%patch_C_3_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>)

    // Declare and prepare patches for the second multi-pauli
    %bridgeBC_4_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(1, 3), location=(3.0, 4.0), orient=h_z>

    // Second multi-pauli
    %measurement_BC, %patch_B_5_, %patch_C_5_ = log_asm.multi_pauli_meas<3, (X, X)>
        (%patch_B_4_, %patch_C_4_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>,
                                !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>)
        (%bridgeBC_4_ : !log_asm.patch.rot_planar<size=(1, 3), location=(3.0, 4.0), orient=h_z>) -> i1

    // Measure out patch C
    // Measurements do not return the logical patch operands - there is only one result, which has type i1 (bool).
    %measurementC = log_asm.measure<Z> (%patch_C_5_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>) -> i1

    // Stabilisers on all the logical patches
    // No need to do it on A since the last op on A was a meas_stab which will 'grow' in rounds to fill the gap
    %patch_B_6_ = log_asm.meas_stab<3> (%patch_B_5_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)

    // Measure out A and B
    %measurementA = log_asm.measure<Z> (%patch_A_4_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>) -> i1
    %measurementB = log_asm.measure<Z> (%patch_B_6_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>) -> i1

    // Our measurement results are: %measurement_AC, %measurement_BC, %measurementC, and then %measurementA and %measurementB
}
// Declare input patches
//CHECK: {"ops": [{"type": "surface", "id": "patch_A_0_", "op_name": "log_asm.patch_dec", "location": [0.0, 0.0], "colour": "GREY", "size": [3, 3], "startHeight": 0.0},
// startHeight of 3 (instead of 0) is because it'll get adjusted later when it's an operand of the second multi-pauli.
//CHECK-SAME: {"type": "surface", "id": "patch_B_0_", "op_name": "log_asm.patch_dec", "location": [4.0, 4.0], "colour": "GREY", "size": [3, 3], "startHeight": 0.0},

// Prepare input patches
//CHECK-SAME: {"type": "surface", "id": "patch_A_1_", "op_name": "log_asm.prepare", "location": [0.0, 0.0], "colour": "BLUE", "size": [3, 3], "startHeight": 0.0},
//CHECK-SAME: {"type": "surface", "id": "patch_B_1_", "op_name": "log_asm.prepare", "location": [4.0, 4.0], "colour": "BLUE", "size": [3, 3], "startHeight": 0.0},

// Initial measure stabilisers
//CHECK-SAME: {"type": "surface", "id": "gen_id_0", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 0.0},
//CHECK-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_0", "toSurfaceId": "patch_A_2_"},
//CHECK-SAME: {"type": "surface", "id": "patch_A_2_", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 3.0},
//CHECK-SAME: {"type": "surface", "id": "gen_id_1", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 3.0},
//CHECK-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_1", "toSurfaceId": "patch_B_2_"},
//CHECK-SAME: {"type": "surface", "id": "patch_B_2_", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 6.0},

// Declare and prepare patches for the first multi-pauli
//CHECK-SAME: {"type": "surface", "id": "patch_C_1_", "op_name": "log_asm.patch_dec", "location": [0.0, 4.0], "colour": "GREY", "size": [3, 3], "startHeight": 6.0},
//CHECK-SAME: {"type": "surface", "id": "patch_C_2_", "op_name": "log_asm.prepare", "location": [0.0, 4.0], "colour": "RED", "size": [3, 3], "startHeight": 6.0},
//CHECK-SAME: {"type": "surface", "id": "bridgeAC_2_", "op_name": "log_asm.patch_dec", "location": [0.0, 3.0], "colour": "GREY", "size": [3, 1], "startHeight": 6.0},

// First multi-pauli logical patches
//CHECK-SAME: {"type": "surface", "id": "gen_id_2", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 6.0},
//CHECK-SAME: {"type": "side", "op_name": "log_asm.multi_pauli_meas", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": false, "-Y": true}, "fromSurfaceId": "gen_id_2", "toSurfaceId": "patch_A_3_"},
//CHECK-SAME: {"type": "surface", "id": "patch_A_3_", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 9.0},
//CHECK-SAME: {"type": "surface", "id": "gen_id_3", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [0.0, 4.0], "size": [3, 3], "startHeight": 6.0},
//CHECK-SAME: {"type": "side", "op_name": "log_asm.multi_pauli_meas", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": false}, "fromSurfaceId": "gen_id_3", "toSurfaceId": "patch_C_3_"},
//CHECK-SAME: {"type": "surface", "id": "patch_C_3_", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [0.0, 4.0], "size": [3, 3], "startHeight": 9.0},

// First multi-pauli bridge patches
//CHECK-SAME: {"type": "surface", "id": "gen_id_4", "op_name": "log_asm.multi_pauli_meas", "colour": "RED", "location": [0.0, 3.0], "size": [3, 1], "startHeight": 6.0},
//CHECK-SAME: {"type": "side", "op_name": "log_asm.multi_pauli_meas", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": false, "-Y": false}, "fromSurfaceId": "gen_id_4", "toSurfaceId": "gen_id_5"},
//CHECK-SAME: {"type": "surface", "id": "gen_id_5", "op_name": "log_asm.multi_pauli_meas", "colour": "RED", "location": [0.0, 3.0], "size": [3, 1], "startHeight": 9.0},

// Stabilisers on all the logical patches
//CHECK-SAME: {"type": "surface", "id": "gen_id_6", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 9.0},
//CHECK-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_6", "toSurfaceId": "patch_A_4_"},
//CHECK-SAME: {"type": "surface", "id": "patch_A_4_", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 12.0},
//CHECK-SAME: {"type": "surface", "id": "gen_id_7", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 12.0},
//CHECK-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_7", "toSurfaceId": "patch_B_4_"},
//CHECK-SAME: {"type": "surface", "id": "patch_B_4_", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 15.0},
//CHECK-SAME: {"type": "surface", "id": "gen_id_8", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 4.0], "size": [3, 3], "startHeight": 15.0},
//CHECK-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_8", "toSurfaceId": "patch_C_4_"},
//CHECK-SAME: {"type": "surface", "id": "patch_C_4_", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 4.0], "size": [3, 3], "startHeight": 18.0},

// Declare and prepare patches for the second multi-pauli
//CHECK-SAME: {"type": "surface", "id": "bridgeBC_4_", "op_name": "log_asm.patch_dec", "location": [3.0, 4.0], "colour": "GREY", "size": [1, 3], "startHeight": 18.0},

// Second multi-pauli logical patches
//CHECK-SAME: {"type": "surface", "id": "gen_id_9", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 18.0},
//CHECK-SAME: {"type": "side", "op_name": "log_asm.multi_pauli_meas", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": false, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_9", "toSurfaceId": "patch_B_5_"},
//CHECK-SAME: {"type": "surface", "id": "patch_B_5_", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 21.0},
//CHECK-SAME: {"type": "surface", "id": "gen_id_10", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [0.0, 4.0], "size": [3, 3], "startHeight": 18.0},
//CHECK-SAME: {"type": "side", "op_name": "log_asm.multi_pauli_meas", "colourScheme": ["BLUE", "RED"], "sides": {"+X": false, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_10", "toSurfaceId": "patch_C_5_"},
//CHECK-SAME: {"type": "surface", "id": "patch_C_5_", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [0.0, 4.0], "size": [3, 3], "startHeight": 21.0},

// Second multi-pauli bridge patches
//CHECK-SAME: {"type": "surface", "id": "gen_id_11", "op_name": "log_asm.multi_pauli_meas", "colour": "BLUE", "location": [3.0, 4.0], "size": [1, 3], "startHeight": 18.0},
//CHECK-SAME: {"type": "side", "op_name": "log_asm.multi_pauli_meas", "colourScheme": ["BLUE", "RED"], "sides": {"+X": false, "-X": false, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_11", "toSurfaceId": "gen_id_12"},
//CHECK-SAME: {"type": "surface", "id": "gen_id_12", "op_name": "log_asm.multi_pauli_meas", "colour": "BLUE", "location": [3.0, 4.0], "size": [1, 3], "startHeight": 21.0},

// Measure out patch C
//CHECK-SAME: {"type": "surface", "id": "measurementC", "op_name": "log_asm.measure", "location": [0.0, 4.0], "colour": "BLUE", "size": [3, 3], "startHeight": 21.0},

// Stabilisers on all the logical patches
//CHECK-SAME: {"type": "surface", "id": "gen_id_13", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 21.0},
//CHECK-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_13", "toSurfaceId": "patch_B_6_"},
//CHECK-SAME: {"type": "surface", "id": "patch_B_6_", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 24.0},

// Measure out A and B
//CHECK-SAME: {"type": "surface", "id": "measurementA", "op_name": "log_asm.measure", "location": [0.0, 0.0], "colour": "BLUE", "size": [3, 3], "startHeight": 24.0},
//CHECK-SAME: {"type": "surface", "id": "measurementB", "op_name": "log_asm.measure", "location": [4.0, 4.0], "colour": "BLUE", "size": [3, 3], "startHeight": 24.0}]}
