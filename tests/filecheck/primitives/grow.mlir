builtin.module {
    %lq0 = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(5,5), location=(0.0, 0.0), orient=h_z>
    %lq1 = log_asm.prepare <Z> (%lq0 : !log_asm.patch.rot_planar<size=(5,5), location=(0.0, 0.0), orient=h_z>)

    %lq_grown = log_asm.grow <4>
                    (%lq1 : !log_asm.patch.rot_planar<size=(5,5), location=(0.0, 0.0), orient=h_z>)
                        -> !log_asm.patch.rot_planar<size=(10,10), location=(0.0, 0.0), orient=h_z>

    %r_z = log_asm.measure <Z> (%lq_grown : !log_asm.patch.rot_planar<size=(10,10), location=(0.0, 0.0), orient=h_z>) -> i1
}
