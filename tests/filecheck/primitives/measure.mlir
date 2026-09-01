// RUN: %visualise "%s" -O %t.json && %filecheck "%s" --input-file %t.json
builtin.module {
    // Declare a patch + Prepare it in the Z basis + Measure Stabilisers on it for 3 rounds + Measure it in the Z basis
    %patch_A_0_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>
    %patch_A_1_ = log_asm.prepare<Z> (%patch_A_0_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
    %patch_A_2_ = log_asm.meas_stab<3> (%patch_A_1_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
    %measurementE = log_asm.measure<Z> (%patch_A_2_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>) -> i1
}
// CHECK: {"ops": [{"type": "surface", "id": "patch_A_0_", "op_name": "log_asm.patch_dec", "location": [0.0, 0.0], "colour": "GREY", "size": [3, 3], "startHeight": 0.0},
// CHECK-SAME: {"type": "surface", "id": "patch_A_1_", "op_name": "log_asm.prepare", "location": [0.0, 0.0], "colour": "BLUE", "size": [3, 3], "startHeight": 0.0},
// CHECK-SAME: {"type": "surface", "id": "gen_id_0", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 0.0},
// CHECK-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_0", "toSurfaceId": "patch_A_2_"},
// CHECK-SAME: {"type": "surface", "id": "patch_A_2_", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 0.0], "size": [3, 3], "startHeight": 3.0},
// CHECK-SAME: {"type": "surface", "id": "measurementE", "op_name": "log_asm.measure", "location": [0.0, 0.0], "colour": "BLUE", "size": [3, 3], "startHeight": 3.0}]}
