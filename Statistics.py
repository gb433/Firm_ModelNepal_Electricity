# Load profiles and generation mix data (LPGM) & energy generation, storage and transmission information (GGTA)
# based on x/capacities from Optimisation and flexible from Dispatch
# Copyright (c) 2019, 2020 Bin Lu, The Australian National University
# Licensed under the MIT Licence
# Correspondence: bin.lu@anu.edu.au

from Input import *
from Simulation import Reliability
from Network import Transmission

import numpy as np
import datetime as dt

def Debug(solution):
    """Debugging"""
    Load, PV, India = (solution.MLoad.sum(axis=1), solution.GPV.sum(axis=1), solution.MIndia.sum(axis=1))
    Baseload = solution.MBaseload.sum(axis=1)
    Peaking = solution.MPeaking.sum(axis=1)

    DischargePH, ChargePH, StoragePH = (solution.DischargePH, solution.ChargePH, solution.StoragePH)
    Deficit_energy, Deficit_power, Deficit, Spillage = (solution.Deficit_energy, solution.Deficit_power, solution.Deficit, solution.Spillage)

    PHS = solution.CPHS * pow(10, 3) # GWh to MWh
    efficiencyPH = solution.efficiencyPH

    for i in range(intervals):
        # Energy supply-demand balance
        assert abs(Load[i] + ChargePH[i] + Spillage[i] \
                   - PV[i] - India[i] - Baseload[i] - Peaking[i] - DischargePH[i] - Deficit[i]) <= 1

        # Discharge, Charge and Storage
        if i==0:
            assert abs(StoragePH[i] - 0.5 * PHS + DischargePH[i] * resolution - ChargePH[i] * resolution * efficiencyPH) <= 1
        else:
            assert abs(StoragePH[i] - StoragePH[i - 1] + DischargePH[i] * resolution - ChargePH[i] * resolution * efficiencyPH) <= 1

        # Capacity: PV, Discharge, Charge and Storage
        try:
            assert np.amax(PV) - sum(solution.CPV) * pow(10, 3) <= 0.1, print("PV",np.amax(PV) - sum(solution.CPV) * pow(10, 3))
            assert np.amax(India) - sum(solution.CInter) * pow(10,3) <= 0.1

            assert np.amax(DischargePH) - sum(solution.CPHP) * pow(10, 3) <= 0.1, print("DischargePH",np.amax(DischargePH) - sum(solution.CPHP) * pow(10, 3))
            assert np.amax(ChargePH) - sum(solution.CPHP) * pow(10, 3) <= 0.1, print("ChargePH",np.amax(ChargePH) - sum(solution.CPHP) * pow(10, 3))
            assert np.amax(StoragePH) - solution.CPHS * pow(10, 3) <= 0.1, print("StoragePH",np.amax(StoragePH) - solution.CPHS * pow(10, 3))
        except AssertionError:
            pass

    print('Debugging: everything is ok')

    return True

def LPGM(solution):
    """Load profiles and generation mix data"""

    Debug(solution)

    C = np.stack([(solution.MLoad).sum(axis=1),
                  solution.MBaseload.sum(axis=1), solution.MPeaking.sum(axis=1), solution.MIndia.sum(axis=1), solution.GPV.sum(axis=1),
                  solution.DischargePH, solution.Deficit, -1 * (solution.Spillage), -1 * solution.ChargePH,
                  solution.StoragePH, solution.StoragePeaking,
                  solution.SPKP, solution.KPLP, solution.LPGP, solution.GPBP, solution.BPMP, solution.EPMP, solution.TISP, solution.GILP, solution.MIMP, solution.KIEP])
       # ['SPKP', 'KPLP', 'LPGP', 'GPBP', 'BPMP', 'EPMP', 'TISP', 'GILP', 'MIMP', 'KIEP']

    C = np.around(C.transpose())

    datentime = np.array([(dt.datetime(firstyear, 1, 1, 0, 0) + x * dt.timedelta(minutes=60 * resolution)).strftime('%a %-d %b %Y %H:%M') for x in range(intervals)])
    C = np.insert(C.astype('str'), 0, datentime, axis=1)

    header = 'Date & time,Operational demand,' \
             'RoR Hydropower (MW),Peaking Hydropower (MW), India Imports (MW),Solar photovoltaics (MW),PHES-Discharge (MW),Energy deficit (MW), Energy Spillage (MW), PHES-Charge (MW),' \
             'PHES-Storage (MWh),Peaking-Storage (MWh),' \
             'SPKP, KPLP, LPGP, GPBP, BPMP, EPMP, TISP, GILP, MIMP, KIEP'

    np.savetxt('Results/LPGM_{}_{}_{}_{}_Network.csv'.format(node,scenario,percapita,import_flag), C, fmt='%s', delimiter=',', header=header, comments='')

    if 'Super' in node:
        header = 'Date & time,Operational demand,' \
                 'RoR Hydropower (MW),Peaking Hydropower (MW), India Imports (MW),Solar photovoltaics (MW),PHES-Discharge (MW),Energy deficit (MW), Energy Spillage (MW),'\
                 'Transmission,PHES-Charge (MW),' \
                 'PHES-Storage,'
        Topology = solution.Topology[np.where(np.in1d(Nodel, coverage) == True)[0]]

        for j in range(nodes):

            C = np.stack([(solution.MLoad)[:, j],
                          solution.MBaseload[:, j],solution.MPeaking[:, j], solution.MIndia[:, j], solution.MPV[:, j], #solution.MWind[:, j],
                          solution.MDischargePH[:, j], solution.MDeficit[:, j], -1 * (solution.MSpillage[:, j]), Topology[j], 
                          -1 * solution.MChargePH[:, j],
                          solution.MStoragePH[:, j]])
            C = np.around(C.transpose())

            C = np.insert(C.astype('str'), 0, datentime, axis=1)
            np.savetxt('Results/LPGM_{}_{}_{}_{}_{}.csv'.format(node,scenario,percapita, import_flag,solution.Nodel[j]), C, fmt='%s', delimiter=',', header=header, comments='')

    print('Load profiles and generation mix is produced.')

    return True

def GGTA(solution):
    """GW, GWh, TWh p.a. and A$/MWh information"""
    # Import cost factors
    factor = np.genfromtxt('Data/factor_hvac.csv', dtype=None, delimiter=',', encoding=None)
        
    factor = dict(factor)

    # Import capacities [GW, GWh] from the least-cost solution
    CPV, CInter, CPHP, CPHS = (sum(solution.CPV), sum(solution.CInter), sum(solution.CPHP), solution.CPHS) # GW, GWh
    CapHydro = CHydro_max.sum() # GW

    # Import generation energy [GWh] from the least-cost solution
    GPV, GHydro, GIndia = map(lambda x: x * pow(10, -6) * resolution / years, (solution.GPV.sum(), solution.MBaseload.sum() + solution.MPeaking.sum(), solution.MIndia.sum())) # TWh p.a.
    DischargePH = solution.DischargePH.sum()
    CFPV = GPV / CPV / 8.76 if CPV != 0 else 0
    
    # Calculate the annual costs for each technology
    CostPV = factor['PV'] * CPV # A$b p.a.
    # CostWind = factor['Wind'] * CWind # A$b p.a.
    CostHydro = factor['Hydro'] * GHydro # A$b p.a.
    CostPH = factor['PHP'] * CPHP + factor['PHS'] * CPHS + factor['PHES-VOM'] * DischargePH * pow(10, -6) * resolution / years # A$b p.a.
    CostIndia = factor['India'] * GIndia # A$b p.a.
       
    # ['SPKP', 'KPLP', 'LPGP', 'GPBP', 'BPMP', 'EPMP', 'TISP', 'GILP', 'MIMP', 'KIEP']
    CostT = np.array([factor['SPKP'], factor['KPLP'], factor['LPGP'], factor['GPBP'], factor['BPMP'], factor['EPMP'], factor['TISP'], factor['GILP'], factor['MIMP'], factor['KIEP']])
    CostAC, CAC = [],[]

    for i in range(0,len(CostT)):
        CostAC.append(CostT[i]) #if ac_flags[i] else CostDC.append(CostT[i])
        #CAC.append(solution.CAC[i]) if ac_flags[i] else CDC.append(solution.CDC[i])
    CostAC, CAC = [np.array(x) for x in [CostAC, CAC]]
    
    CostAC = (CostAC * CAC).sum() if len(CAC) > 0 else 0 # A$b p.a.
    #CostDC = (CostDC * CDC).sum() if len(CDC) > 0 else 0 # A$b p.a.

    CostAC += factor['ACPV'] * CPV #+ factor['ACWind'] * CWind # A$b p.a.

    
    # Calculate the average annual energy demand
    Energy = (MLoad).sum() * pow(10, -9) * resolution / years # TWh p.a.
    #Exports = (solution.MSpillage.sum() + solution.MSpillage_exp.sum()) * pow(10,-6) * resolution / years
    Loss = np.sum(abs(solution.TDC), axis=0) * TLoss
    Loss = Loss.sum() * pow(10, -9) * resolution / years # TWh p.a.

    # Calculate the levelised cost of elcetricity at a network level
    LCOE = (CostPV + CostIndia + CostHydro + CostPH + CostAC) / (Energy - Loss)
    LCOEPV = CostPV / (Energy - Loss)
    LCOEIndia = CostIndia / (Energy - Loss)
    LCOEHydro = CostHydro / (Energy - Loss)
    LCOEPH = CostPH / (Energy - Loss)
    #LCOEDC = CostDC / (Energy - Loss)
    LCOEAC = CostAC / (Energy - Loss)
    
    # Calculate the levelised cost of generation
    LCOG = (CostPV + CostHydro + CostIndia) * pow(10, 3) / (GPV + GHydro + GIndia)
    LCOGP = CostPV * pow(10, 3) / GPV if GPV!=0 else 0
    LCOGH = CostHydro * pow(10, 3) / (GHydro) if (GHydro)!=0 else 0
    LCOGI = CostIndia * pow(10, 3) / GIndia if GIndia != 0 else 0

    # Calculate the levelised cost of balancing
    LCOB = LCOE - LCOG
    LCOBS_P = CostPH / (Energy - Loss)
    LCOBT = (CostAC) / (Energy - Loss)
    LCOBL = LCOB - LCOBS_P - LCOBT

    print('Levelised costs of electricity:')
    print('\u2022 LCOE:', LCOE)
    print('\u2022 LCOG:', LCOG)
    print('\u2022 LCOB:', LCOB)
    print('\u2022 LCOG-PV:', LCOGP, '(%s)' % CFPV)
    # print('\u2022 LCOG-Wind:', LCOGW, '(%s)' % CFWind)
    print('\u2022 LCOG-Hydro:', LCOGH)
    print('\u2022 LCOG-External_Imports:', LCOGI)
    print('\u2022 LCOB-PHES_Storage:', LCOBS_P)
    print('\u2022 LCOB-Transmission:', LCOBT)
    print('\u2022 LCOB-Spillage & loss:', LCOBL)

    size = 20 + len(list(solution.CAC))
    D = np.zeros((3, size))
    header = 'Boundary,Annual demand (TWh),Annual Energy Losses (TWh),' \
             'PV Capacity (GW),PV Avg Annual Gen (TWh),Hydro Capacity (GW),Hydro Avg Annual Gen (TWh),Inter Capacity (GW),India Avg Annual Imports (TWh),' \
             'PHES-PowerCap (GW),PHES-EnergyCap (GWh),' \
             'SPKP, KPLP, LPGP, GPBP, BPMP, EPMP, TISP, GILP, MIMP, KIEP,' \
             'LCOE,LCOG,LCOB,LCOG_PV,LCOG_Hydro,LCOG_IndiaImports,LCOBS_PHES,LCOBT,LCOBL'
    
    ### ALL IN COSTS
    #Domestic and Imports
    D[0, :] = [0,Energy * pow(10, 3), Loss * pow(10, 3), CPV, GPV, CapHydro, GHydro, CInter, GIndia] \
              + [CPHP, CPHS] \
              + list(solution.CAC) \
              + [LCOE, LCOG, LCOB, LCOGP, LCOGH, LCOGI, LCOBS_P, LCOBT, LCOBL] 

    ### DOMESTIC COSTS ONLY
    CostHydro = factor['Hydro'] * (GHydro)

    TDC_domestic = Transmission(solution, domestic_only=True)
    CAC_domestic_all = np.amax(abs(TDC_domestic), axis=0) * pow(10, -3)
    Loss_domestic = np.sum(abs(TDC_domestic), axis=0) * TLoss
    Loss_domestic = Loss_domestic.sum() * pow(10, -9) * resolution / years # PWh p.a.
    CostAC_domestic, CAC_domestic = [],[]

    for i in range(0,len(CostT)):
        CostAC_domestic.append(CostT[i]) #if ac_flags[i] else CostDC_domestic.append(CostT[i])
       # CAC_domestic.append(CAC_domestic_all[i]) if ac_flags[i] else CDC_domestic.append(CAC_domestic_all[i])
    CostAC_domestic, CAC_domestic = [np.array(x) for x in [CostAC_domestic, CAC_domestic]]
    
    CostAC_domestic = (CostAC_domestic * CAC_domestic).sum() if len(CAC_domestic) > 0 else 0 # A$b p.a.
   # CostDC_domestic = (CostDC_domestic * CDC_domestic).sum() if len(CAC_domestic) > 0 else 0 # A$b p.a.
    CostAC_domestic += factor['ACPV'] * CPV   # A$b p.a.

    LCOE = (CostPV + CostIndia + CostHydro + CostPH  + CostAC) / (Energy - Loss_domestic)

    LCOG = (CostPV + CostHydro + CostIndia) * pow(10, 3) / (GPV + GHydro + GIndia)
    LCOGH = CostHydro * pow(10, 3) / (GHydro) if (GHydro)!=0 else 0
    LCOGI = CostIndia * pow(10, 3) / GIndia if GIndia != 0 else 0
# Calculate the levelised cost
    LCOB = LCOE - LCOG
    LCOBS_P = CostPH / (Energy - Loss_domestic)
    LCOBT = (CostAC_domestic) / (Energy - Loss_domestic)
    LCOBL = LCOB - LCOBS_P - LCOBT

    np.savetxt('Results/GGTA_{}_{}_{}_{}.csv'.format(node,scenario,percapita,import_flag), D, fmt='%f', delimiter=',',header=header)
    print('Energy generation, storage and transmission information is produced.')

    return True

def Information(x, flexible):
    """Dispatch: Statistics.Information(x, Flex)"""

    start = dt.datetime.now()
    print("Statistics start at", start)

    S = Solution(x)
    Deficit_energy, Deficit_power, Deficit, DischargePH, DischargePeaking, Spillage = Reliability(S, baseload=baseload, india_imports=flexible, daily_peaking=daily_peaking, peaking_hours=peaking_hours)

    try:
        assert Deficit.sum() * resolution < 0.1, 'Energy generation and demand are not balanced.'
    except AssertionError:
        pass
    
    S.TDC = Transmission(S,domestic_only=True, output=True)
    S.CAC = np.amax(abs(S.TDC), axis=0) * pow(10, -3) # CAC(k), MW to GW
    # SPKP, KPLP, LPGP, GPBP, BPMP, EPMP, TISP, GILP, MIMP, KIEP
    S.SPKP, S.KPLP, S.LPGP, S.GPBP, S.BPMP, S.EPMP, S.TISP, S.GILP, S.MIMP, S.KIEP = map(lambda k: S.TDC[:, k], range(S.TDC.shape[1]))
    if 'Super' not in node:
        S.MPV = S.GPV
        S.MIndia = S.GIndia
        S.MDischargePH = np.tile(S.DischargePH, (nodes, 1)).transpose()
        S.MDeficit = np.tile(S.Deficit, (nodes, 1)).transpose()
        S.MChargePH = np.tile(S.ChargePH, (nodes, 1)).transpose()
        S.MStoragePH = np.tile(S.StoragePH, (nodes, 1)).transpose()
        S.MSpillage = np.tile(S.Spillage, (nodes, 1)).transpose()

    S.MPHS = S.CPHS * np.array(S.CPHP) * pow(10, 3) / sum(S.CPHP) # GW to MW


    # SPKP, KPLP, LPGP, GPBP, BPMP, EPMP, TISP, GILP, MIMP, KIEP
    # 'SP' 'KP' 'LP' 'GP' 'BP' 'MP' 'EP' 'TI' 'GI' 'MI' 'KI'
    S.Topology = np.array([-1 * (S.TISP + S.SPKP),              # SP
                 (S.SPKP + S.KPLP),                            # KP
                 -1 * (S.GILP + S.KPLP + S.LPGP),              # LP
                 (S.LPGP + S.GPBP),                            # GP
                 -1 * (S.GPBP + S.BPMP),                       # BP
                 (S.MIMP + S.BPMP + S.EPMP),                   # MP
                 -1* (S.EPMP + S.KIEP),                        # EP
                 S.TISP,                                       # TI
                 -1 * S.GILP,                                  # GI
                 -1 * S.MIMP,                                  # MI
                 S.KIEP])                                      # KI
    LPGM(S)
    GGTA(S)

    end = dt.datetime.now()
    print("Statistics took", end - start)

    return True

if __name__ == '__main__':
    suffix="_Super_existing_2_True.csv"
    Optimisation_x = np.genfromtxt('Results/Optimisation_resultx{}'.format(suffix), delimiter=',')
    flexible = np.genfromtxt('Results/Dispatch_IndiaImports{}'.format(suffix), delimiter=',', skip_header=1)
    Information(Optimisation_x, flexible)
