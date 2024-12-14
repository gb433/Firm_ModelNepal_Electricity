# A transmission network model to calculate inter-regional power flows
# Copyright (c) 2019, 2020 Bin Lu, The Australian National University
# Licensed under the MIT Licence
# Correspondence: bin.lu@anu.edu.au

import numpy as np

def Transmission(solution, domestic_only=False, export_only=False, output=False):
    """TDC = Network.Transmission(S)"""

    Nodel, PVl, Interl, Hydrol = (solution.Nodel, solution.PVl, solution.Interl, solution.Hydrol)
    intervals, nodes, inters = (solution.intervals, solution.nodes, len(Interl))
    
    CHydro_Peaking = solution.CHydro_Peaking
    peakingfactor = np.tile(CHydro_Peaking, (intervals, 1)) / sum(CHydro_Peaking) if sum(CHydro_Peaking) != 0 else 0
    MPeaking_long = np.tile(solution.DischargePeaking, (len(CHydro_Peaking), 1)).transpose() * peakingfactor 

    MPV, MBaseload, MPeaking = map(np.zeros, [(nodes, intervals)] * 3)
    for i, j in enumerate(Nodel):
        MPV[i, :] = solution.GPV[:, np.where(PVl==j)[0]].sum(axis=1)
        # MWind[i, :] = solution.GWind[:, np.where(Windl==j)[0]].sum(axis=1)
        MBaseload[i, :] = solution.baseload[:, np.where(Hydrol==j)[0]].sum(axis=1)
        MPeaking[i, :] = MPeaking_long[:, np.where(Hydrol==j)[0]].sum(axis=1)
    MPV, MBaseload, MPeaking = (MPV.transpose(), MBaseload.transpose(), MPeaking.transpose()) # Sij-GPV(t, i), Sij-GWind(t, i), MW
    
    MLoad = solution.MLoad # EOLoad(t, j), MW

    defactor = MLoad / MLoad.sum(axis=1)[:, None]
    MDeficit = np.tile(solution.Deficit, (nodes, 1)).transpose() * defactor # MDeficit: EDE(j, t)

    M_minFactors = np.full((intervals, nodes), pow(10,-9)) # Matrix of 10^(-9) required to distribute spillage between nodes when no solar generation
    MPW = MPV + M_minFactors # + MWind
    spfactor = np.divide(MPW, MPW.sum(axis=1)[:, None], where=MPW.sum(axis=1)[:, None]!=0)
    MSpillage = np.tile(solution.Spillage, (nodes, 1)).transpose() * spfactor # MSpillage: ESP(j, t)

    CIndia = np.append(np.array([0]*(nodes - len(solution.CInter))), np.nan_to_num(np.array(solution.CInter))) # GW
    CPHP = solution.CPHP
    pcfactor = np.tile(CPHP, (intervals, 1)) / sum(CPHP) if sum(CPHP) != 0 else 0
    MDischargePH = np.tile(solution.DischargePH, (nodes, 1)).transpose() * pcfactor # MDischarge: DPH(j, t)
    MChargePH = np.tile(solution.ChargePH, (nodes, 1)).transpose() * pcfactor # MCharge: CHPH(j, t)

    india_imports = solution.india_imports # MW
    if CIndia.sum() == 0:
        ifactor = np.tile(CIndia, (intervals, 1))
    else:
        ifactor = np.tile(CIndia, (intervals, 1)) / CIndia.sum()
    MIndia = np.tile(india_imports, (nodes, 1)).transpose() * ifactor

   # efactor = np.array([0,0,0,0,0,0,0,1,0,0,0])
    #ch2factor = np.array([0,1,0,0,0,0,0,0,0,0,0])
   # MExport = np.tile(solution.indiaExportProfiles, (nodes, 1)).transpose() * efactor
   # MHydro_CH2 = np.tile(solution.indiaExportProfiles, (nodes, 1)).transpose() * ch2factor

    """  CHydro_nodes = np.zeros(nodes)
    for j in range(0,len(Nodel)):
        CHydro_nodes[j] = solution.CHydro_max[expl==Nodel[j]].sum()
    expfactor = np.tile(CHydro_nodes, (intervals, 1)) / sum(CHydro_nodes) if sum(CHydro_nodes) != 0 else 0
    MSpillage_exp = np.tile(solution.Spillage, (nodes, 1)).transpose() * expfactor # MSpillage: ESP(j, t)
    MSpillage = np.zeros((nodes, intervals)).transpose() """

    """ BaseloadDomestic = MChargePH.sum(axis=1) + MLoad.sum(axis=1) - MIndia.sum(axis=1) - MDischargePH.sum(axis=1) - MDeficit.sum(axis=1)
    BaseloadDomestic[BaseloadDomestic < 0] = 0
    BaseloadExports = MBaseload.sum(axis=1) - BaseloadDomestic
    BaseloadExports[BaseloadExports < 0] = 0
    b1factor = np.divide(MBaseload, MBaseload.sum(axis=1)[:, None], where=MBaseload.sum(axis=1)[:, None]!=0)
    MBaseload_exp  = np.tile(BaseloadExports, (nodes, 1)).transpose() * b1factor """

    """ SolarDomestic = MChargePH.sum(axis=1) + MLoad.sum(axis=1) - MIndia.sum(axis=1) - MBaseload.sum(axis=1) - MDischargePH.sum(axis=1) - MDeficit.sum(axis=1)
    SolarDomestic[SolarDomestic < 0] = 0
    SolarExports = MPV.sum(axis=1) - SolarDomestic        
    SolarExports[SolarExports < 0] = 0
    s1factor = np.divide(MPV, MPV.sum(axis=1)[:, None], where=MPV.sum(axis=1)[:, None]!=0)
    MPV_exp  = np.tile(SolarExports, (nodes, 1)).transpose() * s1factor """
        
   # WindDomestic = MChargePH.sum(axis=1) + MLoad.sum(axis=1) - MIndia.sum(axis=1) - MBaseload.sum(axis=1) - MPV.sum(axis=1) - MDischargePH.sum(axis=1) - MDeficit.sum(axis=1)
   # WindDomestic[WindDomestic < 0] = 0
   # WindExports = MWind.sum(axis=1) - WindDomestic      
    #WindExports[WindExports < 0] = 0  
    #w1factor = np.divide(MWind, MWind.sum(axis=1)[:, None], where=MWind.sum(axis=1)[:, None]!=0)
    #MWind_exp  = np.tile(WindExports, (nodes, 1)).transpose() * w1factor

    """ PeakingDomestic = MChargePH.sum(axis=1) + MLoad.sum(axis=1) - MPV.sum(axis=1) - MIndia.sum(axis=1) - MBaseload.sum(axis=1) - MDischargePH.sum(axis=1) - MDeficit.sum(axis=1)
    PeakingDomestic[PeakingDomestic < 0] = 0
    PeakingExports = MPeaking.sum(axis=1) - PeakingDomestic
    PeakingExports[PeakingExports < 0]
    p1factor = np.divide(MPeaking, MPeaking.sum(axis=1)[:, None], where=MPeaking.sum(axis=1)[:, None]!=0)
    MPeaking_exp  = np.tile(PeakingExports, (nodes, 1)).transpose() * p1factor """
    if domestic_only:
        MImport = MLoad + MChargePH + MSpillage \
                - MPV - MIndia - MBaseload - MPeaking - MDischargePH - MDeficit # EIM(t, j), MW
    """ else:
        MImport = MLoad + MChargePH + MSpillage_exp + MSpillage \
              - MPV - MIndia - MBaseload - MPeaking - MDischargePH - MDeficit  # EIM(t, j), MW """
    
    coverage = solution.coverage
    if len(coverage) > 1:

       # ['SPKP', 'KPLP', 'LPGP', 'GPBP', 'BPMP', 'EPMP', 'TISP', 'GILP', 'MIMP', 'KIEP']

        #these are the external node so calculation woulde be −1 × 𝑅𝑒𝑞𝑢𝑖𝑟𝑒𝑑 𝐼𝑚𝑝𝑜𝑟𝑡 (𝑡, GI) 
        TISP =  1 * MImport[:, np.where(Nodel=='TI')[0][0]] if 'TI' in coverage else np.zeros(intervals)
        GILP =  1 * MImport[:, np.where(Nodel=='GI')[0][0]] if 'GI' in coverage else np.zeros(intervals)
        KIEP =  1 * MImport[:, np.where(Nodel=='KI')[0][0]] if 'KI' in coverage else np.zeros(intervals)
        MIMP =  -1 * MImport[:, np.where(Nodel=='MI')[0][0]] if 'MI' in coverage else np.zeros(intervals)
       
    
        #Imports into inner internal nodes 
        SPKP = -1 * MImport[:, np.where(Nodel=='SP')[0][0]] - TISP if 'SP' in coverage else np.zeros(intervals)

        #we need to calculate node to node connection so we need to substract in between node.
        KPLP = MImport[:, np.where(Nodel=='KP')[0][0]] - SPKP  if 'KP' in coverage else np.zeros(intervals)
        EPMP = -1 * MImport[:, np.where(Nodel=='EP')[0][0]] - KIEP if 'EP' in coverage else np.zeros(intervals)
        LPGP = -1 * MImport[:, np.where(Nodel=='LP')[0][0]] - GILP - KPLP if 'LP' in coverage else np.zeros(intervals)
        GPBP = 1 * MImport[:, np.where(Nodel=='GP')[0][0]] - LPGP if 'GP' in coverage else np.zeros(intervals)
        BPMP = -1 * MImport[:, np.where(Nodel=='BP')[0][0]] - GPBP  if 'BP' in coverage else np.zeros(intervals)
        
        #Check the final node
        BPMP1 = 1 *  MImport[:, np.where(Nodel=='MP')[0][0]] - MIMP - EPMP if 'MP' in coverage else np.zeros(intervals)
        assert abs(BPMP - BPMP1).max() <= 0.1, print('BPMP Error', abs(BPMP - BPMP1).max())
        TAC = np.array([SPKP, KPLP, LPGP, GPBP, BPMP, EPMP, TISP, GILP, MIMP, KIEP ]).transpose() # TDC(t, k), MW
    else:
        TAC = np.zeros((intervals, len(solution.TLoss)))
    if output:
        MStoragePH = np.tile(solution.StoragePH, (nodes, 1)).transpose() * pcfactor # SPH(t, j), MWh
        solution.MPV, solution.MIndia, solution.MBaseload, solution.MPeaking = (MPV, MIndia, MBaseload, MPeaking)
        solution.MDischargePH, solution.MChargePH, solution.MStoragePH = (MDischargePH, MChargePH, MStoragePH)
        solution.MDeficit, solution.MSpillage = (MDeficit, MSpillage)
        
    return TAC