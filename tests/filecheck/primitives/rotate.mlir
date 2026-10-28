// RUN: %visualise "%s" -O %t.json && %filecheck "%s" --input-file %t.json
builtin.module {
  %qreg = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(4, 4), location=(0.0, 0.0), orient=v_z>
  %qreg_1 = log_asm.prepare<X> (%qreg : !log_asm.patch.rot_planar<size=(4, 4), location=(0.0, 0.0), orient=v_z>)
  %qreg_2 = log_asm.meas_stab<4> (%qreg_1 : !log_asm.patch.rot_planar<size=(4, 4), location=(0.0, 0.0), orient=v_z>)
  %qreg_3 = log_asm.rotate<8> (%qreg_2 : !log_asm.patch.rot_planar<size=(4, 4), location=(0.0, 0.0), orient=v_z>) -> !log_asm.patch.rot_planar<size=(4, 4), location=(4.0, 0.0), orient=h_z>
  qstruct.output(:)
}
// CHECK: {"type": "spacetime", "ops": [{"type": "surface", "id": "qreg", "op_name": "log_asm.patch_dec", "location": [0.0, 0.0], "colour": "GREY", "size": [4, 4], "startHeight": 0.0},
// CHECK-SAME: {"type": "surface", "id": "qreg_1", "op_name": "log_asm.prepare", "location": [0.0, 0.0], "colour": "BLUE", "size": [4, 4], "startHeight": 0.0},
// CHECK-SAME: {"type": "surface", "id": "gen_id_0", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 0.0], "size": [4, 4], "startHeight": 0.0},
// CHECK-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["RED", "BLUE"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_0", "toSurfaceId": "qreg_2"},
// CHECK-SAME: {"type": "surface", "id": "qreg_2", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [0.0, 0.0], "size": [4, 4], "startHeight": 4.0},
// CHECK-SAME: {"type": "surface", "id": "gen_id_1", "op_name": "log_asm.rotate", "colour": "NONE", "location": [0.0, 0.0], "size": [4, 4], "startHeight": 4.0},
// CHECK-SAME: {"type": "surface", "id": "gen_id_1_rotate_midpoint", "op_name": "log_asm.rotate", "colour": "NONE", "location": [0.0, 0.0], "size": [4, 4], "startHeight": 8.0},
// CHECK-SAME: {"type": "surface", "id": "gen_id_1_rotate_top", "op_name": "log_asm.rotate", "colour": "BLUE", "location": [0.0, 0.0], "size": [4, 4], "startHeight": 12.0},
// CHECK-SAME: {"type": "side", "op_name": "log_asm.rotate", "colourScheme": ["RED", "BLUE"], "sides": {"+X": false, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_1", "toSurfaceId": "gen_id_1_rotate_midpoint"},
// CHECK-SAME: {"type": "rotate", "op_name": "log_asm.rotate", "colourScheme": ["BLUE", "RED", "RED", "BLUE"], "sides": {"+X": false, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_1_rotate_midpoint", "toSurfaceId": "gen_id_1_rotate_top"},
// CHECK-SAME: {"type": "surface", "id": "qreg_3", "op_name": "log_asm.rotate", "colour": "RED", "location": [4.0, 0.0], "size": [4, 4], "startHeight": 4.0},
// CHECK-SAME: {"type": "surface", "id": "qreg_3_rotate_midpoint", "op_name": "log_asm.rotate", "colour": "NONE", "location": [4.0, 0.0], "size": [4, 4], "startHeight": 8.0},
// CHECK-SAME: {"type": "surface", "id": "qreg_3_rotate_top", "op_name": "log_asm.rotate", "colour": "NONE", "location": [4.0, 0.0], "size": [4, 4], "startHeight": 12.0},
// CHECK-SAME: {"type": "side", "op_name": "log_asm.rotate", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": false, "+Y": true, "-Y": true}, "fromSurfaceId": "qreg_3_rotate_midpoint", "toSurfaceId": "qreg_3_rotate_top"},
// CHECK-SAME: {"type": "rotate", "op_name": "log_asm.rotate", "colourScheme": ["BLUE", "RED", "BLUE", "RED"], "sides": {"+X": true, "-X": false, "+Y": true, "-Y": true}, "fromSurfaceId": "qreg_3", "toSurfaceId": "qreg_3_rotate_midpoint"},
// CHECK-SAME: {"type": "surface", "id": "gen_id_2", "op_name": "log_asm.meas_stab", "colour": "NONE", "location": [4.0, 0.0], "size": [4, 4], "startHeight": 12.0},
// CHECK-SAME: {"type": "side", "op_name": "log_asm.meas_stab", "colourScheme": ["BLUE", "RED"], "sides": {"+X": true, "-X": true, "+Y": true, "-Y": true}, "fromSurfaceId": "gen_id_2", "toSurfaceId": "qreg_4"},
