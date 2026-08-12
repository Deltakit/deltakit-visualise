// RUN: %visualise "%s" -O %t.json && %filecheck "%s" --input-file %t.json
// Alias for patch type with parameters (rotated planar code, Z logical is vertical,
// located at coordinate (1, 1), size is 5 x 5).
!lq_patch_type = !log_asm.patch.rot_planar<size=(3,3), location=(1.0,1.0), orient=v_z>

builtin.module {
    // Declare the parameterised patch
    %lq = log_asm.patch_dec -> !lq_patch_type
    // Initialise the patch in the Z basis
    %lq_p = log_asm.prepare<Z> (%lq : !lq_patch_type)
    // Measure stabiliser for 20 rounds.
    %lq_m = log_asm.meas_stab<20> (%lq_p : !lq_patch_type)
    // Measure patch in the Z basis
    %r_z = log_asm.measure<Z> (%lq_m : !lq_patch_type) -> i1
}
// Declare the parameterised patch
// CHECK: {"ops": [{"type": "surface", "id": "lq", "op_name": "log_asm.patch_dec", "location": [1.0, 1.0], "colour": "GREY", "size": [3, 3], "startHeight": 0.0},

// Initialise the patch in the Z basis
// CHECK-SAME: {"type": "surface", "id": "lq_p", "op_name": "log_asm.prepare", "location": [1.0, 1.0], "colour": "BLUE", "size": [3, 3], "startHeight": 0.0},

// Measure stabiliser for 20 rounds.
// CHECK-SAME: {"type": "surface", "id": "gen_id_0", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [1.0, 1.0], "size": [3, 3], "startHeight": 0.0},
// CHECK-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["RED", "BLUE"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_0", "toSurfaceId": "lq_m"},
// CHECK-SAME: {"type": "surface", "id": "lq_m", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [1.0, 1.0], "size": [3, 3], "startHeight": 20.0},

// Measure patch in the Z basis
// CHECK-SAME: {"type": "surface", "id": "r_z", "op_name": "log_asm.measure", "location": [1.0, 1.0], "colour": "BLUE", "size": [3, 3], "startHeight": 20.0}]}
