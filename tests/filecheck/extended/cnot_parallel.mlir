// RUN: %visualise "%s" -O %t.json && %filecheck "%s" --input-file %t.json --check-prefix=VIS
builtin.module {

    // Declare input patches
    %patch_A_0_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>
    %patch_B_0_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>

    // Prepare input patches
    // (Since many ops don't change the type of the result - the `->` [type] part of the normal mlir operation syntax is omitted
    // from the dialect where possible. The return type of prepare is just the same as the operand type.)
    %patch_A_2_, %patch_B_2_ = qstruct.parallel<TOP> ->
                !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>,
                !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>
    {
        %patch_A_1_p = log_asm.prepare<Z> (%patch_A_0_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
        %patch_A_2_p = log_asm.meas_stab<3> (%patch_A_1_p : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
        qstruct.yield %patch_A_2_p : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>
    } {
        %patch_B_1_p = log_asm.prepare<Z> (%patch_B_0_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)
        %patch_B_2_p = log_asm.meas_stab<3> (%patch_B_1_p : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)
        qstruct.yield %patch_B_2_p : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>
    }

    // Declare and prepare patches for the first multi-pauli. patch_dec and prepare can be considered to take 0 rounds in block graphs.
    %patch_C_1_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>
    %patch_C_2_ = log_asm.prepare<X> (%patch_C_1_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>)
    %bridgeAC_2_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 1), location=(0.0, 3.0), orient=h_z>

    // First multi-pauli, while B continues with stabilisers
    %measurement_AC, %patch_A_3_, %patch_C_3_, %patch_B_3_ = qstruct.parallel<TOP> ->
                i1,
                !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>,
                !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>,
                !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>
    {
        %measurement_AC_p, %patch_A_3_p, %patch_C_3_p = log_asm.multi_pauli_meas<3, (Z, Z)>
            (%patch_A_2_, %patch_C_2_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>,
                                    !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>)
            (%bridgeAC_2_ : !log_asm.patch.rot_planar<size=(3, 1), location=(0.0, 3.0), orient=h_z>) -> i1
        qstruct.yield %measurement_AC_p, %patch_A_3_p, %patch_C_3_p :
                    i1,
                    !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>,
                    !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>
    } {
        %patch_B_3_p = log_asm.meas_stab<3> (%patch_B_2_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)
        qstruct.yield %patch_B_3_p : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>
    }

    // Stabilisers on all the logical patches - this is not actually required for an efficient CNOT implementation but is included here
    // to demonstrate uses of qstruct.parallel with 3 simultaneous regions.
    %patch_A_4_, %patch_B_4_, %patch_C_4_ = qstruct.parallel<TOP> ->
                !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>,
                !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>,
                !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>
    {
        %patch_A_4_p = log_asm.meas_stab<3> (%patch_A_3_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
        qstruct.yield %patch_A_4_p : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>
    } {
        %patch_B_4_p = log_asm.meas_stab<3> (%patch_B_3_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)
        qstruct.yield %patch_B_4_p : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>
    } {
        %patch_C_4_p = log_asm.meas_stab<3> (%patch_C_3_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>)
        qstruct.yield %patch_C_4_p : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>
    }

    // Declare bridge patch for the second multi-pauli
    %bridgeBC_4_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(1, 3), location=(3.0, 4.0), orient=h_z>

    // Second multi-pauli while A continues with stabilisers
    %measurement_BC, %patch_B_5_, %patch_C_5_, %patch_A_5_ = qstruct.parallel<TOP> ->
                i1,
                !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>,
                !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>,
                !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>
    {
        %measurement_BC_p, %patch_B_5_p, %patch_C_5_p = log_asm.multi_pauli_meas<3, (X, X)>
            (%patch_B_4_, %patch_C_4_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>,
                                    !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>)
            (%bridgeBC_4_ : !log_asm.patch.rot_planar<size=(1, 3), location=(3.0, 4.0), orient=h_z>) -> i1
        qstruct.yield %measurement_BC_p, %patch_B_5_p, %patch_C_5_p :
                    i1,
                    !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>,
                    !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>
    } {
        %patch_A_5_p = log_asm.meas_stab<3> (%patch_A_4_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
        qstruct.yield %patch_A_5_p : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>
    }

    // Measure out patch C, this can also be considered to take 0 rounds in a block graph diagram
    // Measurements do not return the logical patch operands - there is only one result, which has type i1 (bool).
    %measurementC = log_asm.measure<Z> (%patch_C_5_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>) -> i1

    // Stabilisers on the logical patches A and B.
    %patch_A_6_, %patch_B_6_ = qstruct.parallel<TOP> ->
                !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>,
                !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>
    {
        %patch_A_6_p = log_asm.meas_stab<3> (%patch_A_5_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
        qstruct.yield %patch_A_6_p : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>
    } {
        %patch_B_6_p = log_asm.meas_stab<3> (%patch_B_5_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)
        qstruct.yield %patch_B_6_p : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>
    }

    // Measure out A and B
    %measurementA, %measurementB = qstruct.parallel<TOP> -> i1, i1
    {
        %measurementA_p = log_asm.measure<Z> (%patch_A_4_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>) -> i1
        qstruct.yield %measurementA_p : i1
    } {
        %measurementB_p = log_asm.measure<Z> (%patch_B_6_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>) -> i1
        qstruct.yield %measurementB_p : i1
    }

    // Our measurement results are: %measurement_AC, %measurement_BC, %measurementC, and then %measurementA and %measurementB
}

// CHECK-NEXT:  builtin.module {
// CHECK-NEXT:    %patch_A_0_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>
// CHECK-NEXT:    %patch_B_0_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>
// CHECK-NEXT:    %patch_A_2_, %patch_B_2_ = qstruct.parallel<TOP> -> !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>, !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z> {
// CHECK-NEXT:      %patch_A_1_p = log_asm.prepare<Z> (%patch_A_0_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
// CHECK-NEXT:      %patch_A_2_p = log_asm.meas_stab<3> (%patch_A_1_p : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
// CHECK-NEXT:      qstruct.yield %patch_A_2_p : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>
// CHECK-NEXT:    } {
// CHECK-NEXT:      %patch_B_1_p = log_asm.prepare<Z> (%patch_B_0_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)
// CHECK-NEXT:      %patch_B_2_p = log_asm.meas_stab<3> (%patch_B_1_p : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)
// CHECK-NEXT:      qstruct.yield %patch_B_2_p : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>
// CHECK-NEXT:    }
// CHECK-NEXT:    %patch_C_1_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>
// CHECK-NEXT:    %patch_C_2_ = log_asm.prepare<X> (%patch_C_1_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>)
// CHECK-NEXT:    %bridgeAC_2_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 1), location=(0.0, 3.0), orient=h_z>
// CHECK-NEXT:    %measurement_AC, %patch_A_3_, %patch_C_3_, %patch_B_3_ = qstruct.parallel<TOP> -> i1, !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>, !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>, !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z> {
// CHECK-NEXT:      %measurement_AC_p, %patch_A_3_p, %patch_C_3_p = log_asm.multi_pauli_meas<3, (Z, Z)> (%patch_A_2_, %patch_C_2_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>, !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>) (%bridgeAC_2_ : !log_asm.patch.rot_planar<size=(3, 1), location=(0.0, 3.0), orient=h_z>) -> i1
// CHECK-NEXT:      qstruct.yield %measurement_AC_p, %patch_A_3_p, %patch_C_3_p : i1, !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>, !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>
// CHECK-NEXT:    } {
// CHECK-NEXT:      %patch_B_3_p = log_asm.meas_stab<3> (%patch_B_2_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)
// CHECK-NEXT:      qstruct.yield %patch_B_3_p : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>
// CHECK-NEXT:    }
// CHECK-NEXT:    %patch_A_4_, %patch_B_4_, %patch_C_4_ = qstruct.parallel<TOP> -> !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>, !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>, !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z> {
// CHECK-NEXT:      %patch_A_4_p = log_asm.meas_stab<3> (%patch_A_3_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
// CHECK-NEXT:      qstruct.yield %patch_A_4_p : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>
// CHECK-NEXT:    } {
// CHECK-NEXT:      %patch_B_4_p = log_asm.meas_stab<3> (%patch_B_3_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)
// CHECK-NEXT:      qstruct.yield %patch_B_4_p : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>
// CHECK-NEXT:    } {
// CHECK-NEXT:      %patch_C_4_p = log_asm.meas_stab<3> (%patch_C_3_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>)
// CHECK-NEXT:      qstruct.yield %patch_C_4_p : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>
// CHECK-NEXT:    }
// CHECK-NEXT:    %bridgeBC_4_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(1, 3), location=(3.0, 4.0), orient=h_z>
// CHECK-NEXT:    %measurement_BC, %patch_B_5_, %patch_C_5_, %patch_A_5_ = qstruct.parallel<TOP> -> i1, !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>, !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>, !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z> {
// CHECK-NEXT:      %measurement_BC_p, %patch_B_5_p, %patch_C_5_p = log_asm.multi_pauli_meas<3, (X, X)> (%patch_B_4_, %patch_C_4_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>, !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>) (%bridgeBC_4_ : !log_asm.patch.rot_planar<size=(1, 3), location=(3.0, 4.0), orient=h_z>) -> i1
// CHECK-NEXT:      qstruct.yield %measurement_BC_p, %patch_B_5_p, %patch_C_5_p : i1, !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>, !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>
// CHECK-NEXT:    } {
// CHECK-NEXT:      %patch_A_5_p = log_asm.meas_stab<3> (%patch_A_4_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
// CHECK-NEXT:      qstruct.yield %patch_A_5_p : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>
// CHECK-NEXT:    }
// CHECK-NEXT:    %measurementC = log_asm.measure<Z> (%patch_C_5_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>) -> i1
// CHECK-NEXT:    %patch_A_6_, %patch_B_6_ = qstruct.parallel<TOP> -> !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>, !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z> {
// CHECK-NEXT:      %patch_A_6_p = log_asm.meas_stab<3> (%patch_A_5_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
// CHECK-NEXT:      qstruct.yield %patch_A_6_p : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>
// CHECK-NEXT:    } {
// CHECK-NEXT:      %patch_B_6_p = log_asm.meas_stab<3> (%patch_B_5_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)
// CHECK-NEXT:      qstruct.yield %patch_B_6_p : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>
// CHECK-NEXT:    }
// CHECK-NEXT:    %measurementA, %measurementB = qstruct.parallel<TOP> -> i1, i1 {
// CHECK-NEXT:      %measurementA_p = log_asm.measure<Z> (%patch_A_4_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>) -> i1
// CHECK-NEXT:      qstruct.yield %measurementA_p : i1
// CHECK-NEXT:    } {
// CHECK-NEXT:      %measurementB_p = log_asm.measure<Z> (%patch_B_6_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>) -> i1
// CHECK-NEXT:      qstruct.yield %measurementB_p : i1
// CHECK-NEXT:    }
// CHECK-NEXT:  }

// Declare input patches
//VIS: {"ops": [{"type": "surface", "id": "patch_A_0_", "op_name": "log_asm.patch_dec", "location": [0.0, 0.0], "colour": "GREY", "size": [3, 3], "startHeight": 0.0},
//VIS-SAME: {"type": "surface", "id": "patch_B_0_", "op_name": "log_asm.patch_dec", "location": [4.0, 4.0], "colour": "GREY", "size": [3, 3], "startHeight": 0.0},

// Prepare input patches and initial measure stabilisers (parallel region 1)
//VIS-SAME: {"type": "surface", "id": "patch_A_1_p", "op_name": "log_asm.prepare", "location": [0.0, 0.0], "colour": "BLUE", "size": [3, 3], "startHeight": 0.0},
//VIS-SAME: {"type": "surface", "id": "gen_id_0", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 0.0},
//VIS-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_0", "toSurfaceId": "patch_A_2_p"},
//VIS-SAME: {"type": "surface", "id": "patch_A_2_p", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 3.0},
//VIS-SAME: {"type": "surface", "id": "patch_B_1_p", "op_name": "log_asm.prepare", "location": [4.0, 4.0], "colour": "BLUE", "size": [3, 3], "startHeight": 0.0},
//VIS-SAME: {"type": "surface", "id": "gen_id_1", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 0.0},
//VIS-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_1", "toSurfaceId": "patch_B_2_p"},
//VIS-SAME: {"type": "surface", "id": "patch_B_2_p", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 3.0},

// Declare and prepare patches for the first multi-pauli
//VIS-SAME: {"type": "surface", "id": "patch_C_1_", "op_name": "log_asm.patch_dec", "location": [0.0, 4.0], "colour": "GREY", "size": [3, 3], "startHeight": 3.0},
//VIS-SAME: {"type": "surface", "id": "patch_C_2_", "op_name": "log_asm.prepare", "location": [0.0, 4.0], "colour": "RED", "size": [3, 3], "startHeight": 3.0},
//VIS-SAME: {"type": "surface", "id": "bridgeAC_2_", "op_name": "log_asm.patch_dec", "location": [0.0, 3.0], "colour": "GREY", "size": [3, 1], "startHeight": 3.0},

// First multi-pauli logical patches
//VIS-SAME: {"type": "surface", "id": "gen_id_2", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 3.0},
//VIS-SAME: {"type": "side", "op_name": "log_asm.multi_pauli_meas", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": false, "-Y": true}, "fromSurfaceId": "gen_id_2", "toSurfaceId": "patch_A_3_p"},
//VIS-SAME: {"type": "surface", "id": "patch_A_3_p", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 6.0},
//VIS-SAME: {"type": "surface", "id": "gen_id_3", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [0.0, 4.0], "size": [3, 3], "startHeight": 3.0},
//VIS-SAME: {"type": "side", "op_name": "log_asm.multi_pauli_meas", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": false}, "fromSurfaceId": "gen_id_3", "toSurfaceId": "patch_C_3_p"},
//VIS-SAME: {"type": "surface", "id": "patch_C_3_p", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [0.0, 4.0], "size": [3, 3], "startHeight": 6.0},

// First multi-pauli bridge patches
//VIS-SAME: {"type": "surface", "id": "gen_id_4", "op_name": "log_asm.multi_pauli_meas", "colour": "RED", "location": [0.0, 3.0], "size": [3, 1], "startHeight": 3.0},
//VIS-SAME: {"type": "side", "op_name": "log_asm.multi_pauli_meas", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": false, "-Y": false}, "fromSurfaceId": "gen_id_4", "toSurfaceId": "gen_id_5"},
//VIS-SAME: {"type": "surface", "id": "gen_id_5", "op_name": "log_asm.multi_pauli_meas", "colour": "RED", "location": [0.0, 3.0], "size": [3, 1], "startHeight": 6.0},

// B stabilisers (parallel with first multi-pauli)
//VIS-SAME: {"type": "surface", "id": "gen_id_6", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 3.0},
//VIS-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_6", "toSurfaceId": "patch_B_3_p"},
//VIS-SAME: {"type": "surface", "id": "patch_B_3_p", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 6.0},

// Stabilisers on all the logical patches (parallel region)
//VIS-SAME: {"type": "surface", "id": "gen_id_7", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 6.0},
//VIS-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_7", "toSurfaceId": "patch_A_4_p"},
//VIS-SAME: {"type": "surface", "id": "patch_A_4_p", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 9.0},
//VIS-SAME: {"type": "surface", "id": "gen_id_8", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 6.0},
//VIS-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_8", "toSurfaceId": "patch_B_4_p"},
//VIS-SAME: {"type": "surface", "id": "patch_B_4_p", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 9.0},
//VIS-SAME: {"type": "surface", "id": "gen_id_9", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 4.0], "size": [3, 3], "startHeight": 6.0},
//VIS-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_9", "toSurfaceId": "patch_C_4_p"},
//VIS-SAME: {"type": "surface", "id": "patch_C_4_p", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 4.0], "size": [3, 3], "startHeight": 9.0},

// Declare bridge patch for the second multi-pauli
//VIS-SAME: {"type": "surface", "id": "bridgeBC_4_", "op_name": "log_asm.patch_dec", "location": [3.0, 4.0], "colour": "GREY", "size": [1, 3], "startHeight": 9.0},

// Second multi-pauli logical patches
//VIS-SAME: {"type": "surface", "id": "gen_id_10", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 9.0},
//VIS-SAME: {"type": "side", "op_name": "log_asm.multi_pauli_meas", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": false, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_10", "toSurfaceId": "patch_B_5_p"},
//VIS-SAME: {"type": "surface", "id": "patch_B_5_p", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 12.0},
//VIS-SAME: {"type": "surface", "id": "gen_id_11", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [0.0, 4.0], "size": [3, 3], "startHeight": 9.0},
//VIS-SAME: {"type": "side", "op_name": "log_asm.multi_pauli_meas", "colourScheme": ["BLUE", "RED"], "sides": {"+X": false, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_11", "toSurfaceId": "patch_C_5_p"},
//VIS-SAME: {"type": "surface", "id": "patch_C_5_p", "op_name": "log_asm.multi_pauli_meas", "colour": "NONE", "location": [0.0, 4.0], "size": [3, 3], "startHeight": 12.0},

// Second multi-pauli bridge patches
//VIS-SAME: {"type": "surface", "id": "gen_id_12", "op_name": "log_asm.multi_pauli_meas", "colour": "BLUE", "location": [3.0, 4.0], "size": [1, 3], "startHeight": 9.0},
//VIS-SAME: {"type": "side", "op_name": "log_asm.multi_pauli_meas", "colourScheme": ["BLUE", "RED"], "sides": {"+X": false, "-X": false, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_12", "toSurfaceId": "gen_id_13"},
//VIS-SAME: {"type": "surface", "id": "gen_id_13", "op_name": "log_asm.multi_pauli_meas", "colour": "BLUE", "location": [3.0, 4.0], "size": [1, 3], "startHeight": 12.0},

// A stabilisers (parallel with second multi-pauli)
//VIS-SAME: {"type": "surface", "id": "gen_id_14", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 9.0},
//VIS-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_14", "toSurfaceId": "patch_A_5_p"},
//VIS-SAME: {"type": "surface", "id": "patch_A_5_p", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 12.0},

// Measure out patch C
//VIS-SAME: {"type": "surface", "id": "measurementC", "op_name": "log_asm.measure", "location": [0.0, 4.0], "colour": "BLUE", "size": [3, 3], "startHeight": 12.0},

// Stabilisers on A and B
//VIS-SAME: {"type": "surface", "id": "gen_id_15", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 12.0},
//VIS-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_15", "toSurfaceId": "patch_A_6_p"},
//VIS-SAME: {"type": "surface", "id": "patch_A_6_p", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 15.0},
//VIS-SAME: {"type": "surface", "id": "gen_id_16", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 12.0},
//VIS-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_16", "toSurfaceId": "patch_B_6_p"},
//VIS-SAME: {"type": "surface", "id": "patch_B_6_p", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [4.0, 4.0], "size": [3, 3], "startHeight": 15.0},

// Measure out A and B
//VIS-SAME: {"type": "surface", "id": "measurementA_p", "op_name": "log_asm.measure", "location": [0.0, 0.0], "colour": "BLUE", "size": [3, 3], "startHeight": 15.0},
//VIS-SAME: {"type": "surface", "id": "measurementB_p", "op_name": "log_asm.measure", "location": [4.0, 4.0], "colour": "BLUE", "size": [3, 3], "startHeight": 15.0}]}