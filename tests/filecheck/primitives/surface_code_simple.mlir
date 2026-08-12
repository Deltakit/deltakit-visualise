// RUN: %visualise_patch "%s" -O %t.json && %filecheck "%s" --input-file %t.json
builtin.module {
    %q1, %q2, %q3 = qcore.alloc_qubit<coords=[(0.5, 0.5), (1.5, 0.5), (1.0, 1.0)]> -> !qcore.qubit, !qcore.qubit, !qcore.qubit
    %qreg = qcore.pack_qubit_reg(%q1, %q2, %q3) -> !qcore.qubit_reg<3>
    %p0 = log_asm.cast(%qreg : !qcore.qubit_reg<3>) -> !log_asm.patch.rot_planar<size=(2, 1), location=(0.0, 0.0), orient=v_z>
    %p0_1 = log_asm.prepare<Z> (%p0 : !log_asm.patch.rot_planar<size=(2, 1), location=(0.0, 0.0), orient=v_z>)
    %log = log_asm.measure<Z> (%p0_1 : !log_asm.patch.rot_planar<size=(2, 1), location=(0.0, 0.0), orient=v_z>) -> i1
}
// CHECK: []
