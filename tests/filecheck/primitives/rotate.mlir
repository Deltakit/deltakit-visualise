builtin.module {
  %qreg = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(4, 4), location=(0.0, 0.0), orient=v_z>
  %qreg_1 = log_asm.prepare<X> (%qreg : !log_asm.patch.rot_planar<size=(4, 4), location=(0.0, 0.0), orient=v_z>)
  %qreg_2 = log_asm.meas_stab<4> (%qreg_1 : !log_asm.patch.rot_planar<size=(4, 4), location=(0.0, 0.0), orient=v_z>)
  %qreg_3 = log_asm.rotate<8> (%qreg_2 : !log_asm.patch.rot_planar<size=(4, 4), location=(0.0, 0.0), orient=v_z>) -> !log_asm.patch.rot_planar<size=(4, 4), location=(4.0, 0.0), orient=h_z>
  %qreg_4 = log_asm.meas_stab<4> (%qreg_3 : !log_asm.patch.rot_planar<size=(4, 4), location=(4.0, 0.0), orient=h_z>)
  %cexpr = log_asm.measure<X> (%qreg_4 : !log_asm.patch.rot_planar<size=(4, 4), location=(4.0, 0.0), orient=h_z>) -> i1
  qstruct.output(:)
}
