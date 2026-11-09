// builtin.module {
//     %0 = sobs.dec_unplaced_observable -> !sobs.unplaced_observable
//     %patch_A_0_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>
//     %patch_B_0_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>
//     %patch_A_1_ = log_asm.prepare<Z> (%patch_A_0_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
//     %patch_B_1_ = log_asm.prepare<Z> (%patch_B_0_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)
//     %1 = sobs.locate_unplaced_observable<ZZ> (%0) on (%patch_A_1_, %patch_B_1_) -> !sobs.unplaced_observable
//     %patch_A_2_ = log_asm.meas_stab<3> (%patch_A_1_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
//     %patch_B_2_ = log_asm.meas_stab<3> (%patch_B_1_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)
//     %2 = sobs.locate_unplaced_observable<ZZ> (%1) on (%patch_A_2_, %patch_B_2_) -> !sobs.unplaced_observable
//     %patch_C_1_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>
//     %patch_C_2_ = log_asm.prepare<X> (%patch_C_1_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>)
//     %bridgeAC_2_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 1), location=(0.0, 3.0), orient=h_z>
//     %measurement_AC, %patch_A_3_, %patch_C_3_ = log_asm.multi_pauli_meas<3, (Z, Z)>
//         (%patch_A_2_, %patch_C_2_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>,
//                                 !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>)
//         (%bridgeAC_2_ : !log_asm.patch.rot_planar<size=(3, 1), location=(0.0, 3.0), orient=h_z>) -> i1
//     // %3 = sobs.locate_unplaced_observable<ZZ> (%2) on (%patch_C_3_) -> !sobs.unplaced_observable
//     %3 = sobs.locate_unplaced_observable<ZZ> (%2) on (%patch_A_3_, %patch_C_3_) -> !sobs.unplaced_observable
//     %patch_A_4_ = log_asm.meas_stab<3> (%patch_A_3_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
//     %patch_B_4_ = log_asm.meas_stab<3> (%patch_B_2_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)
//     %patch_C_4_ = log_asm.meas_stab<3> (%patch_C_3_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>)
//     %4 = sobs.locate_unplaced_observable<ZZ> (%3) on (%patch_C_4_, %patch_B_4_) -> !sobs.unplaced_observable
//     %bridgeBC_4_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(1, 3), location=(3.0, 4.0), orient=h_z>
//     %measurement_BC, %patch_B_5_, %patch_C_5_ = log_asm.multi_pauli_meas<3, (X, X)>
//         (%patch_B_4_, %patch_C_4_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>,
//                                 !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>)
//         (%bridgeBC_4_ : !log_asm.patch.rot_planar<size=(1, 3), location=(3.0, 4.0), orient=h_z>) -> i1
//     %5 = sobs.locate_unplaced_observable<Z> (%4) on (%patch_C_5_, %patch_B_5_) -> !sobs.unplaced_observable
//     // %5 = sobs.locate_unplaced_observable<Z> (%4) on (%patch_B_5_) -> !sobs.unplaced_observable
//     %measurementC = log_asm.measure<Z> (%patch_C_5_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 4.0), orient=h_z>) -> i1
//     %patch_B_6_ = log_asm.meas_stab<3> (%patch_B_5_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)
//     %6 = sobs.locate_unplaced_observable<Z> (%5) on (%patch_B_6_) -> !sobs.unplaced_observable
//     %measurementA = log_asm.measure<Z> (%patch_A_4_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>) -> i1
//     %measurementB = log_asm.measure<Z> (%patch_B_6_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>) -> i1
// }

// Test case - same as above but with Patch C at (4.0, 0.0)
builtin.module {
    %0 = sobs.dec_unplaced_observable -> !sobs.unplaced_observable
    %patch_A_0_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>
    %patch_B_0_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>
    %patch_A_1_ = log_asm.prepare<Z> (%patch_A_0_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
    %patch_B_1_ = log_asm.prepare<Z> (%patch_B_0_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)
    %1 = sobs.locate_unplaced_observable<ZZ> (%0) on (%patch_A_1_, %patch_B_1_) -> !sobs.unplaced_observable
    %patch_A_2_ = log_asm.meas_stab<3> (%patch_A_1_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
    %patch_B_2_ = log_asm.meas_stab<3> (%patch_B_1_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)
    %2 = sobs.locate_unplaced_observable<ZZ> (%1) on (%patch_A_2_, %patch_B_2_) -> !sobs.unplaced_observable
    %patch_C_1_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 0.0), orient=h_z>
    %patch_C_2_ = log_asm.prepare<X> (%patch_C_1_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 0.0), orient=h_z>)
    %bridgeAC_2_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(1, 3), location=(3.0, 0.0), orient=h_z>
    %measurement_AC, %patch_A_3_, %patch_C_3_ = log_asm.multi_pauli_meas<3, (Z, Z)>
        (%patch_A_2_, %patch_C_2_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>,
                                !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 0.0), orient=h_z>)
        (%bridgeAC_2_ : !log_asm.patch.rot_planar<size=(1, 3), location=(3.0, 0.0), orient=h_z>) -> i1
    // %3 = sobs.locate_unplaced_observable<ZZ> (%2) on (%patch_C_3_) -> !sobs.unplaced_observable
    %3 = sobs.locate_unplaced_observable<ZZ> (%2) on (%patch_A_3_, %patch_C_3_) -> !sobs.unplaced_observable
    %patch_A_4_ = log_asm.meas_stab<3> (%patch_A_3_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>)
    %patch_B_4_ = log_asm.meas_stab<3> (%patch_B_2_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)
    %patch_C_4_ = log_asm.meas_stab<3> (%patch_C_3_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 0.0), orient=h_z>)
    %4 = sobs.locate_unplaced_observable<ZZ> (%3) on (%patch_C_4_, %patch_B_4_) -> !sobs.unplaced_observable
    %bridgeBC_4_ = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(3, 1), location=(4.0, 3.0), orient=h_z>
    %measurement_BC, %patch_B_5_, %patch_C_5_ = log_asm.multi_pauli_meas<3, (X, X)>
        (%patch_B_4_, %patch_C_4_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>,
                                !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 0.0), orient=h_z>)
        (%bridgeBC_4_ : !log_asm.patch.rot_planar<size=(3, 1), location=(4.0, 3.0), orient=h_z>) -> i1
    %5 = sobs.locate_unplaced_observable<Z> (%4) on (%patch_C_5_, %patch_B_5_) -> !sobs.unplaced_observable
    // %5 = sobs.locate_unplaced_observable<Z> (%4) on (%patch_B_5_) -> !sobs.unplaced_observable
    %measurementC = log_asm.measure<Z> (%patch_C_5_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 0.0), orient=h_z>) -> i1
    %patch_B_6_ = log_asm.meas_stab<3> (%patch_B_5_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>)
    %6 = sobs.locate_unplaced_observable<Z> (%5) on (%patch_B_6_) -> !sobs.unplaced_observable
    %measurementA = log_asm.measure<Z> (%patch_A_4_ : !log_asm.patch.rot_planar<size=(3, 3), location=(0.0, 0.0), orient=h_z>) -> i1
    %measurementB = log_asm.measure<Z> (%patch_B_6_ : !log_asm.patch.rot_planar<size=(3, 3), location=(4.0, 4.0), orient=h_z>) -> i1
}

