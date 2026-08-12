// RUN: %visualise "%s" -O %t.json && %filecheck "%s" --input-file %t.json
// A CNOT circuit where all SSA values use numeric names (no name_hints).
// This tests that the IdTracker falls back to counter-based IDs (v_0, v_1, ...).
builtin.module {

    // Declare input patches
    %0 = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>
    %1 = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>

    // Prepare input patches
    // (Since many ops don't change the type of the result - the `->` [type] part of the normal mlir operation syntax is omitted
    // from the dialect where possible. The return type of prepare is just the same as the operand type.)
    %2 = log_asm.prepare<Z> (%0 : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
    %3 = log_asm.prepare<Z> (%1 : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)

    // Initial measure stabilisers
    %4 = log_asm.meas_stab<3> (%2 : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
    %5 = log_asm.meas_stab<3> (%3 : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)

    // Declare and prepare patches for the first multi-pauli
    %6 = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>
    %7 = log_asm.prepare<X> (%6 : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>)
    %8 = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 1), location=(0.0, 3.0), orient=h_z>

    // First multi-pauli
    // The return types are i1 followed simply by the types of the logical patch operands, so these are not repeated in the syntax.
    %9, %10, %11 = log_asm.multi_pauli_meas<3, (Z, Z)>
        (%4, %7 : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>,
                                !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>)
        (%8 : !log_asm.patch.rot_planar<size=(3, 1), location=(0.0, 3.0), orient=h_z>) -> i1

    // Stabilisers on all the logical patches
    %12 = log_asm.meas_stab<3> (%10 : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
    %13 = log_asm.meas_stab<3> (%5 : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)
    %14 = log_asm.meas_stab<3> (%11 : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>)

    // Declare and prepare patches for the second multi-pauli
    %15 = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(1, 3), location=(3.0, 4.0), orient=h_z>

    // Second multi-pauli
    %16, %17, %18 = log_asm.multi_pauli_meas<3, (X, X)>
        (%13, %14 : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>,
                                !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>)
        (%15 : !log_asm.patch.rot_planar<size=(1, 3), location=(3.0, 4.0), orient=h_z>) -> i1

    // Measure out patch C
    // Measurements do not return the logical patch operands - there is only one result, which has type i1 (bool).
    %19 = log_asm.measure<Z> (%18 : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>) -> i1

    // Stabilisers on all the logical patches
    // No need to do it on A since the last op on A was a meas_stab which will 'grow' in rounds to fill the gap
    %20 = log_asm.meas_stab<3> (%17 : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)

    // Measure out A and B
    %21 = log_asm.measure<Z> (%12 : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>) -> i1
    %22 = log_asm.measure<Z> (%20 : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>) -> i1

    // Our measurement results are: %9, %16, %19, and then %21 and %22
}
// Declare input patches
//CHECK: {"ops": [{"type": "surface", "id": "gen_id_0", "op_name": "log_asm.patch_dec", "location": [0.0, 0.0], "colour": "GREY", "size": [3, 3], "startHeight": 0.0},
//CHECK-SAME: {"type": "surface", "id": "gen_id_1", "op_name": "log_asm.patch_dec", "location": [4.0, 4.0], "colour": "GREY", "size": [3, 3], "startHeight": 0.0},

// Prepare input patches
//CHECK-SAME: {"type": "surface", "id": "gen_id_2", "op_name": "log_asm.prepare", "location": [0.0, 0.0], "colour": "BLUE", "size": [3, 3], "startHeight": 0.0},
//CHECK-SAME: {"type": "surface", "id": "gen_id_3", "op_name": "log_asm.prepare", "location": [4.0, 4.0], "colour": "BLUE", "size": [3, 3], "startHeight": 0.0},

// Initial measure stabilisers
//CHECK-SAME: {"type": "surface", "id": "gen_id_4", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 0.0},
//CHECK-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_4", "toSurfaceId": "gen_id_5"},
//CHECK-SAME: {"type": "surface", "id": "gen_id_5", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 3.0},
//CHECK-SAME: {"type": "surface", "id": "gen_id_6", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 3.0},
//CHECK-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_6", "toSurfaceId": "gen_id_7"},
//CHECK-SAME: {"type": "surface", "id": "gen_id_7", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 6.0},

// Declare and prepare patches for the first multi-pauli
//CHECK-SAME: {"type": "surface", "id": "gen_id_8", "op_name": "log_asm.patch_dec", "location": [0.0, 4.0], "colour": "GREY", "size": [3, 3], "startHeight": 6.0},
//CHECK-SAME: {"type": "surface", "id": "gen_id_9", "op_name": "log_asm.prepare", "location": [0.0, 4.0], "colour": "RED", "size": [3, 3], "startHeight": 6.0},
//CHECK-SAME: {"type": "surface", "id": "gen_id_10", "op_name": "log_asm.patch_dec", "location": [0.0, 3.0], "colour": "GREY", "size": [3, 1], "startHeight": 6.0},

// First multi-pauli logical patches
//CHECK-SAME: {"type": "surface", "id": "gen_id_11", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 6.0},
//CHECK-SAME: {"type": "side", "op_name": "log_asm.multi_pauli_meas", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": false, "-Y": true}, "fromSurfaceId": "gen_id_11", "toSurfaceId": "gen_id_13"},
//CHECK-SAME: {"type": "surface", "id": "gen_id_13", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 9.0},
//CHECK-SAME: {"type": "surface", "id": "gen_id_12", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [0.0, 4.0], "size": [3, 3], "startHeight": 6.0},
//CHECK-SAME: {"type": "side", "op_name": "log_asm.multi_pauli_meas", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": false}, "fromSurfaceId": "gen_id_12", "toSurfaceId": "gen_id_14"},
//CHECK-SAME: {"type": "surface", "id": "gen_id_14", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [0.0, 4.0], "size": [3, 3], "startHeight": 9.0},

// First multi-pauli bridge patches
//CHECK-SAME: {"type": "surface", "id": "gen_id_15", "op_name": "log_asm.multi_pauli_meas", "colour": "RED", "location": [0.0, 3.0], "size": [3, 1], "startHeight": 6.0},
//CHECK-SAME: {"type": "side", "op_name": "log_asm.multi_pauli_meas", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": false, "-Y": false}, "fromSurfaceId": "gen_id_15", "toSurfaceId": "gen_id_16"},
//CHECK-SAME: {"type": "surface", "id": "gen_id_16", "op_name": "log_asm.multi_pauli_meas", "colour": "RED", "location": [0.0, 3.0], "size": [3, 1], "startHeight": 9.0},

// Stabilisers on all the logical patches
//CHECK-SAME: {"type": "surface", "id": "gen_id_18", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 9.0},
//CHECK-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_18", "toSurfaceId": "gen_id_19"},
//CHECK-SAME: {"type": "surface", "id": "gen_id_19", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 12.0},
//CHECK-SAME: {"type": "surface", "id": "gen_id_20", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 12.0},
//CHECK-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_20", "toSurfaceId": "gen_id_21"},
//CHECK-SAME: {"type": "surface", "id": "gen_id_21", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 15.0},
//CHECK-SAME: {"type": "surface", "id": "gen_id_22", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 4.0], "size": [3, 3], "startHeight": 15.0},
//CHECK-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_22", "toSurfaceId": "gen_id_23"},
//CHECK-SAME: {"type": "surface", "id": "gen_id_23", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 4.0], "size": [3, 3], "startHeight": 18.0},

// Declare and prepare patches for the second multi-pauli
//CHECK-SAME: {"type": "surface", "id": "gen_id_24", "op_name": "log_asm.patch_dec", "location": [3.0, 4.0], "colour": "GREY", "size": [1, 3], "startHeight": 18.0},

// Second multi-pauli logical patches
//CHECK-SAME: {"type": "surface", "id": "gen_id_25", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 18.0},
//CHECK-SAME: {"type": "side", "op_name": "log_asm.multi_pauli_meas", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": false, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_25", "toSurfaceId": "gen_id_27"},
//CHECK-SAME: {"type": "surface", "id": "gen_id_27", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 21.0},
//CHECK-SAME: {"type": "surface", "id": "gen_id_26", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [0.0, 4.0], "size": [3, 3], "startHeight": 18.0},
//CHECK-SAME: {"type": "side", "op_name": "log_asm.multi_pauli_meas", "colourScheme": ["BLUE", "RED"], "sides": {"+X": false, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_26", "toSurfaceId": "gen_id_28"},
//CHECK-SAME: {"type": "surface", "id": "gen_id_28", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [0.0, 4.0], "size": [3, 3], "startHeight": 21.0},

// Second multi-pauli bridge patches
//CHECK-SAME: {"type": "surface", "id": "gen_id_29", "op_name": "log_asm.multi_pauli_meas", "colour": "BLUE", "location": [3.0, 4.0], "size": [1, 3], "startHeight": 18.0},
//CHECK-SAME: {"type": "side", "op_name": "log_asm.multi_pauli_meas", "colourScheme": ["BLUE", "RED"], "sides": {"+X": false, "-X": false, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_29", "toSurfaceId": "gen_id_30"},
//CHECK-SAME: {"type": "surface", "id": "gen_id_30", "op_name": "log_asm.multi_pauli_meas", "colour": "BLUE", "location": [3.0, 4.0], "size": [1, 3], "startHeight": 21.0},

// Measure out patch C
//CHECK-SAME: {"type": "surface", "id": "gen_id_32", "op_name": "log_asm.measure", "location": [0.0, 4.0], "colour": "BLUE", "size": [3, 3], "startHeight": 21.0},

// Stabilisers on all the logical patches
//CHECK-SAME: {"type": "surface", "id": "gen_id_33", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 21.0},
//CHECK-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_33", "toSurfaceId": "gen_id_34"},
//CHECK-SAME: {"type": "surface", "id": "gen_id_34", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 24.0},

// Measure out A and B
//CHECK-SAME: {"type": "surface", "id": "gen_id_35", "op_name": "log_asm.measure", "location": [0.0, 0.0], "colour": "BLUE", "size": [3, 3], "startHeight": 24.0},
//CHECK-SAME: {"type": "surface", "id": "gen_id_36", "op_name": "log_asm.measure", "location": [4.0, 4.0], "colour": "BLUE", "size": [3, 3], "startHeight": 24.0}]}
