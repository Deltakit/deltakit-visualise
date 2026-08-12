// RUN: %visualise_patch "%s" -O %t.json && %filecheck "%s" --input-file %t.json
builtin.module {
    %q1, %q2, %q3 = qcore.alloc_qubit<coords=[(0.5, 0.5), (1.5, 0.5), (1.0, 1.0)]> -> !qcore.qubit, !qcore.qubit, !qcore.qubit
    %qreg = qcore.pack_qubit_reg(%q1, %q2, %q3) -> !qcore.qubit_reg<3>
    %p0 = log_asm.cast(%qreg : !qcore.qubit_reg<3>) -> !log_asm.patch.rot_planar<size=(2, 1), location=(0.0, 0.0), orient=v_z>
    %p0_1 = log_asm.prepare<Z> (%p0 : !log_asm.patch.rot_planar<size=(2, 1), location=(0.0, 0.0), orient=v_z>)
    %p0_2 = log_asm.cast(%p0_1 : !log_asm.patch.rot_planar<size=(2, 1), location=(0.0, 0.0), orient=v_z>) -> !qcore.qubit_reg<3>
    %p0_3, %p0_4, %p0_5 = qcore.unpack_qubit_reg(%p0_2 : !qcore.qubit_reg<3>)
    %p0_6, %p0_7, %p0_8 = qstruct.repeat<2> (%p0_3, %p0_4, %p0_5 : !qcore.qubit, !qcore.qubit, !qcore.qubit) -> !qcore.qubit, !qcore.qubit, !qcore.qubit {
        ^bb0(%0: !qcore.qubit, %1: !qcore.qubit, %2: !qcore.qubit):
        %3, %4, %5, %6 = qstruct.circuit(%0, %1, %2 : !qcore.qubit, !qcore.qubit, !qcore.qubit) -> !qcore.qubit, !qcore.qubit, !qcore.qubit, i1 {
            ^bb1(%7: !qcore.qubit, %8: !qcore.qubit, %9: !qcore.qubit):
            %10 = plaquette.round(%7, %8, %9) -> i1 {
                ^bb2(%11: !qcore.qubit, %12: !qcore.qubit, %13: !qcore.qubit):
                %14 = plaquette.plaquette<[Z0 Z1 : 2]> on (%11, %12) using (%13) -> i1
            plaquette.yield %14 : i1
        }
        qstruct.yield %7, %8, %9, %10 : !qcore.qubit, !qcore.qubit, !qcore.qubit, i1
        }
        qstruct.yield %3, %4, %5 : !qcore.qubit, !qcore.qubit, !qcore.qubit
    }
    %p0_9 = qcore.pack_qubit_reg(%p0_6, %p0_7, %p0_8) -> !qcore.qubit_reg<3>
    %p0_10 = log_asm.cast(%p0_9 : !qcore.qubit_reg<3>) -> !log_asm.patch.rot_planar<size=(2, 1), location=(0.0, 0.0), orient=v_z>
    %log = log_asm.measure<Z> (%p0_10 : !log_asm.patch.rot_planar<size=(2, 1), location=(0.0, 0.0), orient=v_z>) -> i1
}
// CHECK: [{"round": 1, "qubits": [{"id": "q_0", "type": "data", "coordinates": [0.5, 0.5]}, {"id": "q_1", "type": "data", "coordinates": [1.5, 0.5]}, {"id": "q_2", "type": "ancilla", "coordinates": [1.0, 1.0]}], "patches": [{"plaquettes": [{"id": 0, "colour": "blue", "shape": "semicircle", "weight": 2, "coordinates": ["q_0", "q_1", "q_2"]}]}]}, {"round": 2, "qubits": [{"id": "q_0", "type": "data", "coordinates": [0.5, 0.5]}, {"id": "q_1", "type": "data", "coordinates": [1.5, 0.5]}, {"id": "q_2", "type": "ancilla", "coordinates": [1.0, 1.0]}], "patches": [{"plaquettes": [{"id": 0, "colour": "blue", "shape": "semicircle", "weight": 2, "coordinates": ["q_0", "q_1", "q_2"]}]}]}]
