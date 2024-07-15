# To simulate energy supply-demand balance based on long-term, high-resolution chronological data
# Copyright (c) 2019, 2020 Bin Lu, The Australian National University
# Licensed under the MIT Licence
# Correspondence: bin.lu@anu.edu.au

import numpy as np

def Reliability(solution, baseload, india_imports, daily_peaking, peaking_hours=0, start=None, end=None):
    """Deficit = Simulation.Reliability(S, hydro=...)"""

    ###### CALCULATE NETLOAD FOR EACH INTERVAL ######
    Netload = (solution.MLoad.sum(axis=1) - solution.GPV.sum(axis=1) - baseload.sum(axis=1))[start:end] \
                - india_imports # Sj-ENLoad(j, t), MW
    length = len(Netload)
    
    solution.india_imports = india_imports # MW

    ###### CREATE STORAGE SYSTEM VARIABLES ######
    Pcapacity_PH = sum(solution.CPHP) * pow(10, 3) # S-CPHP(j), GW to MW
    Scapacity_PH = solution.CPHS * pow(10, 3) # S-CPHS(j), GWh to MWh
    #Pcapacity_Peaking = sum(solution.CHydro_Peaking) * pow(10, 3)
   # Scapacity_Peaking = peaking_hours*Pcapacity_Peaking
    efficiencyPH, resolution = (solution.efficiencyPH, solution.resolution)

    DischargePH, ChargePH, StoragePH, DischargePeaking, StoragePeaking = map(np.zeros, [length] * 5)
    Deficit_energy, Deficit_power = map(np.zeros, [length] * 2)
    
   # daily_peaking_divided = daily_peaking.sum(axis=1) / 24

    for t in range(length):
        ###### INITIALISE INTERVAL ######
        Netloadt = Netload[t]
        Storage_PH_t1 = StoragePH[t-1] if t>0 else 0.5 * Scapacity_PH

        """Storage_Peaking_t1 = StoragePeaking[t-1] + daily_peaking_divided[t] if t>0 else 0.5*Scapacity_Peaking

        # Calculate peaking discharge
        if Scapacity_Peaking < Storage_Peaking_t1:
            Discharge_Peaking_t = daily_peaking_divided[t]
        else:
            Discharge_Peaking_t = np.minimum(np.maximum(0, Netloadt), Pcapacity_Peaking)
            Discharge_Peaking_t = np.minimum(Discharge_Peaking_t, Storage_Peaking_t1/resolution)
        Storage_Peaking_t = Storage_Peaking_t1 - Discharge_Peaking_t * resolution

        DischargePeaking[t] = Discharge_Peaking_t
        StoragePeaking[t] = Storage_Peaking_t

        ##### UPDATE STORAGE SYSTEMS ######
        Netloadt = Netloadt - Discharge_Peaking_t """
        Discharge_PH_t = min(max(0, Netloadt), Pcapacity_PH, Storage_PH_t1 / resolution)
        Charge_PH_t = min(-1 * min(0, Netloadt), Pcapacity_PH, (Scapacity_PH - Storage_PH_t1) / efficiencyPH / resolution)
        Storage_PH_t = Storage_PH_t1 - Discharge_PH_t * resolution + Charge_PH_t * resolution * efficiencyPH

        DischargePH[t] = Discharge_PH_t
        ChargePH[t] = Charge_PH_t
        StoragePH[t] = Storage_PH_t

        diff1 = Netloadt - Discharge_PH_t + Charge_PH_t
        
        ###### DETERMINE DEFICITS ######
        if diff1 <= 0:
            Deficit_energy[t] = 0
            Deficit_power[t] = 0
        elif (Discharge_PH_t == Pcapacity_PH):
            Deficit_energy[t] = 0
            Deficit_power[t] = diff1
        elif (Discharge_PH_t == Storage_PH_t1 / resolution):
            Deficit_energy[t] = diff1
            Deficit_power[t] = 0    

    Deficit = Deficit_energy + Deficit_power
    Netload = Netload - DischargePeaking
    Spillage = -1 * np.minimum(Netload + ChargePH - DischargePH, 0)

    ###### ERROR CHECKING ######
    assert 0 <= int(np.amax(StoragePH)) <= Scapacity_PH, 'Storage below zero or exceeds max storage capacity'
    assert np.amin(Deficit) > -0.1, 'DeficitD below zero'
    assert np.amin(Spillage) >= 0, 'Spillage below zero'

    ###### UPDATE SOLUTION OBJECT ######
    solution.DischargePH, solution.ChargePH, solution.StoragePH, solution.DischargePeaking, solution.StoragePeaking = (DischargePH, ChargePH, StoragePH, DischargePeaking, StoragePeaking)
    solution.Deficit_energy, solution.Deficit_power, solution.Deficit, solution.Spillage = (Deficit_energy, Deficit_power, Deficit, Spillage)

    return Deficit_energy, Deficit_power, Deficit, DischargePH, DischargePeaking, Spillage

if __name__ == '__main__':
    from Input import *
    from Network import Transmission 

    suffix = "_Super_existing_20_True.csv"
    Optimisation_x = np.genfromtxt('Results/Optimisation_resultx{}'.format(suffix), delimiter=',')
    
    # Initialise the optimisation
    S = Solution(Optimisation_x)

    CIndia = np.nan_to_num(np.array(S.CInter))

     
    # Simulation with only baseload
    Deficit_energy1, Deficit_power1, Deficit1, DischargePH1, DischargePeaking1, Spillage1 = Reliability(S, baseload=baseload, india_imports=np.zeros(intervals), daily_peaking=daily_peaking)
    Max_deficit1 = np.reshape(Deficit1, (-1, 8760)).sum(axis=-1) # MWh per year
    PIndia = Deficit1.max() * pow(10, -3) # GW

    GIndia = resolution * (Max_deficit1).max() / efficiencyPH

    PenPower = abs(PIndia - CIndia.sum()) * pow(10,3)
    PenEnergy = 0
        
    # Simulation with baseload, all existing capacity
    Deficit_energy, Deficit_power, Deficit, DischargePH, DischargePeaking, Spillage = Reliability(S, baseload=baseload, india_imports=np.ones(intervals) * CIndia.sum() * pow(10,3), daily_peaking=daily_peaking)

    # Deficit penalty function
    PenDeficit = max(0, Deficit.sum() * resolution - S.allowance)

    # India import profile
    india_imports = np.clip(Deficit1, 0, CIndia.sum() * pow(10,3)) # MW

    # Simulation using the existing capacity generation profiles - required for storage average annual discharge
    Deficit_energy, Deficit_power, Deficit, DischargePH, DischargePeaking, Spillage = Reliability(S, baseload=baseload, india_imports=india_imports, daily_peaking=daily_peaking)

    # Discharged energy from storage systems
    GPHES = DischargePH.sum() * resolution / years * pow(10,-6) # TWh per year
    

    india_imports = np.zeros(intervals)

    # Transmission capacity calculations
    # TDC = Transmission(S, output=True) if 'Super' in node else np.zeros((intervals, len(TLoss))) # TDC: TDC(t, k), MW
    TDC = Transmission(S, domestic_only=True, output=True) if 'Super' in node else np.zeros((intervals, len(TLoss)))
    CDC = np.amax(abs(TDC), axis=0) * pow(10, -3) # CDC(k), MW to GW

    # Transmission penalty function
    PenDC = 0

    # Exports
    #GBaseloadExports = S.MBaseload_exp.sum() * resolution / years
    #GPeakingExports = S.MPeaking_exp.sum() * resolution / years

    # Average annual electricity generated by existing capacity
    GHydro = resolution * (baseload.sum() + DischargePeaking.sum()) / efficiencyPH / years
    
    # Average annual electricity imported through external interconnections
    GIndia = resolution * india_imports.sum() / years / efficiencyPH

    # Levelised cost of electricity calculation
    cost = factor * np.array([sum(S.CPV), GIndia * pow(10,-6), sum(S.CPHP), S.CPHS, GPHES] + list(CDC) + [sum(S.CPV), (GHydro) * pow(10, -6), 0, 0]) # $b p.a.
    cost = cost.sum()
    loss = np.sum(abs(TDC), axis=0) * TLoss
    loss = loss.sum() * pow(10, -9) * resolution / years # PWh p.a.
    LCOE = cost / abs(energy - loss) 

    print(LCOE, energy, loss, GIndia * pow(10,-6) * factor[2] / (GIndia*pow(10,-9)), (GHydro) * pow(10, -6) * factor[18] / ((GHydro)*pow(10,-9)), len(CDC))