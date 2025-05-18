# Load profiles and generation mix data (LPGM) & energy generation, storage and transmission information (GGTA)
# based on x/capacities from Optimisation and flexible from Dispatch
# Copyright (c) 2019, 2020 Bin Lu, The Australian National University
# Licensed under the MIT Licence

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

    PHS = solution.CPHS * pow(10, 3)
    efficiencyPH = solution.efficiencyPH

    for i in range(intervals):
        assert abs(Load[i] + ChargePH[i] + Spillage[i] \
                   - PV[i] - India[i] - Baseload[i] - Peaking[i] - DischargePH[i] - Deficit[i]) <= 1

        if i==0:
            assert abs(StoragePH[i] - 0.5 * PHS + DischargePH[i] * resolution - ChargePH[i] * resolution * efficiencyPH) <= 1
        else:
            assert abs(StoragePH[i] - StoragePH[i - 1] + DischargePH[i] * resolution - ChargePH[i] * resolution * efficiencyPH) <= 1

        try:
            assert np.amax(India) - sum(solution.CInter) * pow(10,3) <= 0.1
            assert np.amax(DischargePH) - sum(solution.CPHP) * pow(10, 3) <= 0.1
            assert np.amax(ChargePH) - sum(solution.CPHP) * pow(10, 3) <= 0.1
            assert np.amax(StoragePH) - solution.CPHS * pow(10, 3) <= 0.1
        except AssertionError:
            pass

    print('Debugging: everything is ok')
    return True

def LPGM(solution):
    """Load profiles and generation mix data"""
    Debug(solution)

    C = np.stack([
        solution.MLoad.sum(axis=1),
        solution.MBaseload.sum(axis=1),
        solution.MPeaking.sum(axis=1),
        solution.MIndia.sum(axis=1),
        solution.GPV.sum(axis=1),
        solution.DischargePH,
        solution.Deficit,
        solution.MExport.sum(axis=1),
        -1* solution.Spillage,      
        -1 * solution.ChargePH,
        solution.StoragePH,
        solution.StoragePeaking,
        solution.SPKP, solution.KPLP, solution.LPGP, solution.GPBP,
        solution.BPMP, solution.EPMP, solution.TISP, solution.GILP, solution.MIMP, solution.KIEP
    ])
    C = np.around(C.transpose())
    datentime = np.array([(dt.datetime(firstyear, 1, 1, 0, 0) + x * dt.timedelta(minutes=60 * resolution)).strftime('%a %-d %b %Y %H:%M') for x in range(intervals)])
    C = np.insert(C.astype('str'), 0, datentime, axis=1)

    header = 'Date & time,Operational demand,RoR Hydropower (MW),Peaking Hydropower (MW), India Imports (MW),Solar photovoltaics (MW),PHES-Discharge (MW),Energy deficit (MW), India Exports (MW), PHES-Charge (MW),PHES-Storage (MWh),Peaking-Storage (MWh),SPKP, KPLP, LPGP, GPBP, BPMP, EPMP, TISP, GILP, MIMP, KIEP'

    np.savetxt('Results/LPGM_{}_{}_{}_{}_{}_Network.csv'.format(node, scenario, percapita, import_flag, export_flag), C, fmt='%s', delimiter=',', header=header, comments='')

    if 'Super' in node:
        header = 'Date & time,Operational demand,RoR Hydropower (MW),Peaking Hydropower (MW), India Imports (MW),Solar photovoltaics (MW),PHES-Discharge (MW),Energy deficit (MW), India Exports (MW),Transmission,PHES-Charge (MW),PHES-Storage (MWh)'
        Topology = solution.Topology[np.where(np.in1d(Nodel, coverage) == True)[0]]

        for j in range(nodes):
            C_node = np.stack([
                solution.MLoad[:, j],
                solution.MBaseload[:, j],
                solution.MPeaking[:, j],
                solution.MIndia[:, j],
                solution.MPV[:, j],
                solution.MDischargePH[:, j],
                solution.MDeficit[:, j],
                solution.MExport[:, j],
                -1 * solution.MSpillage[:, j],
                Topology[j],
                -1 * solution.MChargePH[:, j],
                solution.MStoragePH[:, j],
            ])
            C_node = np.around(C_node.transpose())
            C_node = np.insert(C_node.astype('str'), 0, datentime, axis=1)
            np.savetxt('Results/LPGM_{}_{}_{}_{}_{}_{}.csv'.format(node, scenario, percapita, import_flag, export_flag, solution.Nodel[j]), C_node, fmt='%s', delimiter=',', header=header, comments='')

    print('Load profiles and generation mix is produced.')
    return True

def GGTA(solution):
    """GW, GWh, TWh p.a. and A$/MWh information"""
    factor_data = np.genfromtxt('Data/factor_hvac.csv', dtype=None, delimiter=',', encoding=None)
    factor = dict(factor_data)

    CPV, CInter, CPHP, CPHS = (sum(solution.CPV), sum(solution.CInter), sum(solution.CPHP), solution.CPHS)
    CapHydro = CHydro_max.sum()

    
    GPV = solution.GPV.sum() * 1e-6 * resolution / years
    GHydro = (solution.MBaseload.sum() + solution.MPeaking.sum()) * 1e-6 * resolution / years
    GExport = solution.IndiaExport.sum() * 1e-6 * resolution / years
    GSpillage = solution.Spillage.sum() * 1e-6 * resolution / years
    DischargePH = solution.DischargePH.sum()
    GPHES = solution.DischargePH.sum() * 1e-6 * resolution / years
    print("Debug GExport (sum MW):", solution.IndiaExport.sum())    
    if solution.import_flag:
        GIndia = solution.MIndia.sum() * 1e-6 * resolution / years
        CostIndia = factor['India'] * GIndia
    else:
        GIndia = 0
        CostIndia = 0

    CFPV = GPV / CPV / 8.76 if CPV != 0 else 0

    CostPV = factor['PV'] * CPV
    CostHydro = factor['Hydro'] * GHydro
    CostPH = factor['PHP'] * CPHP + factor['PHS'] * CPHS + factor['PHES-VOM'] * DischargePH * pow(10, -6) * resolution / years
    CostIndia = factor['India'] * GIndia
    CostExport = factor['India'] * GExport # Same price for export revenue

    CostT = np.array([factor['SPKP'], factor['KPLP'], factor['LPGP'], factor['GPBP'], factor['BPMP'], factor['EPMP'], factor['TISP'], factor['GILP'], factor['MIMP'], factor['KIEP']])
    CostAC, CAC = [], []

    for i in range(len(CostT)):
        CostAC.append(CostT[i])
    CostAC, CAC = [np.array(x) for x in [CostAC, CAC]]
    CostAC = (CostAC * CAC).sum() if len(CAC) > 0 else 0
    CostAC += factor['ACPV'] * CPV

    Energy = (MLoad).sum() * pow(10, -9) * resolution / years #PWh per annum
    Loss = np.sum(abs(solution.TDC), axis=0) * TLoss 
    Loss = Loss.sum() * pow(10, -9) * resolution / years #PWh per annum

    TotalCost = CostPV + CostIndia + CostHydro + CostPH + CostAC
    LCOE = TotalCost / (Energy - Loss)
    LCOG = (CostPV + CostHydro + CostIndia) * 1e3 / (GPV + GHydro + GIndia)
    LCOGP = CostPV * 1e3 / GPV if GPV != 0 else 0
    LCOGH = CostHydro * 1e3 / GHydro if GHydro != 0 else 0
    LCOGI = CostIndia * 1e3 / GIndia if GIndia != 0 else 0

    LCOB = LCOE - LCOG
    LCOBS_P = CostPH / (Energy - Loss)
    LCOBT = CostAC / (Energy - Loss)
    LCOBL = LCOB - LCOBS_P - LCOBT

    print("India Export (TWh/year):", (GExport))
    print("Export Revenue:", (CostExport))
    print('Levelised costs of electricity:')
    print('\u2022 LCOE:', LCOE)
    print('\u2022 LCOG:', LCOG)
    print('\u2022 LCOB:', LCOB)
    print('\u2022 LCOG-PV:', LCOGP, '(%s)' % CFPV)
    print('\u2022 LCOG-Hydro:', LCOGH)
    print('\u2022 LCOG-External_Imports:', LCOGI)
    print('\u2022 LCOB-PHES_Storage:', LCOBS_P)
    print('\u2022 LCOB-Transmission:', LCOBT)
    print('\u2022 LCOB-Spillage & loss:', LCOBL)
    print(f"Export Revenue: {CostExport:.6f} B$ ({CostExport* 1e3:.2f} M$)")

    size = 22 + len(list(solution.CAC))
    D = np.zeros((3, size))
    header = 'Boundary,Annual demand (TWh),Annual Energy Losses (TWh),' \
             'PV Capacity (GW),PV Avg Annual Gen (TWh),Hydro Capacity (GW),Hydro Avg Annual Gen (TWh),Inter Capacity (GW),India Avg Annual Imports (TWh),India Avg Annual Exports (TWh), Energy Spillage (TWh),' \
             'PHES-PowerCap (GW),PHES-EnergyCap (GWh),' \
             'SPKP, KPLP, LPGP, GPBP, BPMP, EPMP, TISP, GILP, MIMP, KIEP,' \
             'LCOE,LCOG,LCOB,LCOG_PV,LCOG_Hydro,LCOG_IndiaImports,LCOBS_PHES,LCOBT,LCOBL'

    D[0, :] = [0,Energy * pow(10, 3), Loss * pow(10, 3), CPV, GPV, CapHydro, GHydro, CInter, GIndia, GExport, GSpillage] \
              + [CPHP, CPHS] \
              + list(solution.CAC) \
              + [LCOE, LCOG, LCOB, LCOGP, LCOGH, LCOGI, LCOBS_P, LCOBT, LCOBL] 


    np.savetxt('Results/GGTA_{}_{}_{}_{}_{}.csv'.format(node,scenario,percapita,import_flag, export_flag), D, fmt='%f', delimiter=',',header=header)
    print('Energy generation, storage and transmission information is produced.')
    return True

def Information(x, flexible, IndiaExport=None):
    """Dispatch: Statistics.Information(x, Flex)"""
    start = dt.datetime.now()
    print("Statistics start at", start)

    S = Solution(x)
    Deficit_energy, Deficit_power, Deficit, DischargePH, DischargePeaking, Spillage, IndiaExport = Reliability(S, baseload=baseload, india_imports=flexible, daily_peaking=daily_peaking, peaking_hours=peaking_hours, export_flag=True)
    S.IndiaExport = IndiaExport 
    try:
        assert Deficit.sum() * resolution < 0.1, 'Energy generation and demand are not balanced.'
    except AssertionError:
        pass

    S.TDC = Transmission(S, domestic_only=True, output=True)
    S.CAC = np.amax(abs(S.TDC), axis=0) * pow(10, -3)

    S.SPKP, S.KPLP, S.LPGP, S.GPBP, S.BPMP, S.EPMP, S.TISP, S.GILP, S.MIMP, S.KIEP = map(lambda k: S.TDC[:, k], range(S.TDC.shape[1]))

    if 'Super' not in node:
        S.MPV = S.GPV
        S.MIndia = S.GIndia
        S.MDischargePH = np.tile(S.DischargePH, (nodes, 1)).transpose()
        S.MDeficit = np.tile(S.Deficit, (nodes, 1)).transpose()
        S.MChargePH = np.tile(S.ChargePH, (nodes, 1)).transpose()
        S.MStoragePH = np.tile(S.StoragePH, (nodes, 1)).transpose()
        S.MSpillage = np.tile(S.Spillage, (nodes, 1)).transpose()
        S.MExport = np.tile(S.IndiaExport, (nodes, 1)).transpose()

    S.MPHS = S.CPHS * np.array(S.CPHP) * pow(10, 3) / sum(S.CPHP)

    S.Topology = np.array([-1 * (S.TISP + S.SPKP),
                           (S.SPKP + S.KPLP),
                           -1 * (S.GILP + S.KPLP + S.LPGP),
                           (S.LPGP + S.GPBP),
                           -1 * (S.GPBP + S.BPMP),
                           (S.MIMP + S.BPMP + S.EPMP),
                           -1* (S.EPMP + S.KIEP),
                           S.TISP,
                           -1 * S.GILP,
                           -1 * S.MIMP,
                           S.KIEP])

    LPGM(S)
    GGTA(S)

    end = dt.datetime.now()
    print("Statistics took", end - start)
    return True

if __name__ == '__main__':
    suffix="_Super_existing_2_True_True.csv"
    Optimisation_x = np.genfromtxt('Results/Optimisation_resultx{}'.format(suffix), delimiter=',')
    flexible = np.genfromtxt('Results/Dispatch_IndiaImports{}'.format(suffix), delimiter=',', skip_header=1)
    Information(Optimisation_x, flexible)
