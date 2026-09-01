// RUN: %visualise "%s" -O %t.json && %filecheck "%s" --input-file %t.json
builtin.module {
    // Declare a patch + Prepare it in the Z basis
    %patch_A_0_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 3), location=(5.0, 5.0), orient=h_z>
    %patch_A_1_ = log_asm.prepare<Z> (%patch_A_0_ : !log_asm.patch.rot_planar<size=(3, 3), location=(5.0, 5.0), orient=h_z>)
}
// CHECK: {"ops": [{"type": "surface", "id": "patch_A_0_", "op_name": "log_asm.patch_dec", "location": [5.0, 5.0], "colour": "GREY", "size": [3, 3], "startHeight": 0.0},
// CHECK-SAME: {"type": "surface", "id": "patch_A_1_", "op_name": "log_asm.prepare", "location": [5.0, 5.0], "colour": "BLUE", "size": [3, 3], "startHeight": 0.0}]}
