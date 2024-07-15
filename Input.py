# Modelling input and assumptions
# Copyright (c) 2019, 2020 Bin Lu, The Australian National University
# Licensed under the MIT Licence
# Correspondence: bin.lu@anu.edu.au

import numpy as np
from Optimisation import scenario, node, percapita, import_flag, ac_flag

Nodel = np.array(['SP', 'KP', 'LP', 'GP', 'BP', 'MP', 'EP', 'TI','GI', 'MI', 'KI'])
PVl = np.array(['SP'] * 1 + ['KP'] * 2 + ['LP'] * 2 + ['GP'] * 2 + ['BP'] * 3+ ['MP'] * 3 + ['EP'] * 6)
pv_ub_np = np.array([250.] + [20., 10] + [20.,16.] + [10., 12.] + [8.,5.,6.] + [10.,8.,12.] + [7., 10.,13.,8.,6.,4.])
phes_ub_np = np.array([55.] + [120.] + [368.] + [552.] + [13.] + [1268.] + [942.] + [0.] + [0.] + [0.] + [0.])

# Add external interconnections 
Interl = np.array(['TI']*1 + ['GI']*1 + ['MI']*1 + ['KI']*1) if node == 'Super' else np.array([])
resolution = 1

###### DATA IMPORTS ######
MLoad = np.genfromtxt('Data/electricity{}.csv'.format(percapita), delimiter=',', skip_header=1, usecols=range(4, 4+len(Nodel))) # EOLoad(t, j), MW
TSPV = np.genfromtxt('Data/pv.csv', delimiter=',', skip_header=1, usecols=range(4, 4+len(PVl))) # TSPV(t, i), MW
# TSWind = np.genfromtxt('Data/wind.csv', delimiter=',', skip_header=1, usecols=range(4, 4+len(Windl))) # TSWind(t, i), MW

assets = np.genfromtxt('Data/assets.csv'.format(scenario), dtype=None, delimiter=',', encoding=None)[1:, 3:].astype(float)
constraints = np.genfromtxt('Data/constraints.csv'.format(scenario), dtype=None, delimiter=',', encoding=None)[1:, 3:].astype(float)

if scenario == 'existing':
    hydrol = np.array(['SP']*1+['KP']*1+['LP']*1+['GP']*1+['BP']*1+['MP']*1+['EP']*1)
    # expl = np.array(['TI']*6+['GI']*2+['MI']*2+['KI']*1)


CHydro_max, CHydro_RoR, CHydro_Peaking = [assets[:, x] * pow(10, -3) for x in range(assets.shape[1])] # CHydro(j), MW to GW
EHydro = constraints[:, 0] # GWh per year
hydroProfiles = np.genfromtxt('Data/RoR.csv'.format(scenario), delimiter=',', skip_header=1, usecols=range(4,4+len(Nodel)), encoding=None).astype(float)

#peaking_hours = 4
# Calculate baseload and daily peaking
baseload = np.ones((MLoad.shape[0], len(CHydro_RoR)))
daily_peaking = np.zeros((MLoad.shape[0], len(CHydro_RoR)))

for i in range(0, MLoad.shape[0]):
    for j in range(0, len(CHydro_RoR)):
        baseload[i,j] = hydroProfiles[i,j]
        daily_peaking[i, j] = sum(hydroProfiles[i:i+23, j] - baseload[i:i+23, j]) if i % 24 == 0 else daily_peaking[i-1, j]

###### CONSTRAINTS ######
# Energy constraints
Hydromax = EHydro.sum() * pow(10,3) # GWh to MWh per year

# Transmission constraints
externalImports = 0.05 if node=='Super' else 0
CDC7max, CDC8max, CDC9max, CDC10max = 4 * [externalImports * MLoad.sum() / MLoad.shape[0] / 1000] # 5%: External interconnections: TISP, GILP, MIMP, KIEP MW to GW """

###### TRANSMISSION LOSSES ######
# HVDC backbone scenario
if ac_flag == 'HVDC':
    # HVDC backbone scenario
    dc_flags = np.array([True, True, True, True, True, True, True, True, True, True, True])
else:
    # HVAC backbone scenario
    dc_flags = np.array([False, False, False, False, False, False, False, False, False, False])

TLoss = []
# ['SPKP', 'KPLP', 'LPGP', 'GPBP', 'BPMP', 'EPMP', 'TISP', 'GILP', 'MIMP', 'KIEP']
TDistances = [131, 178, 75, 149, 122, 197, 16, 40, 78, 26]
for i in range(0, len(dc_flags)):
    TLoss.append(TDistances[i] * 0.03) if dc_flags[i] else TLoss.append(TDistances[i] * 0.07)
TLoss = np.array(TLoss) * pow(10, -3)



###### STORAGE SYSTEM CONSTANTS ######
efficiencyPH = 0.8

###### COST FACTORS ######
factor = np.genfromtxt('Data/factor.csv', delimiter=',', usecols=1)

###### SIMULATION PERIOD ######
firstyear, finalyear, timestep = (2013, 2022, 1)

###### SCENARIO ADJUSTMENTS #######
# Node values
if 'Super' == node:
    coverage = Nodel

else:
    if 'APG_PMY_Only' == node:
        coverage = np.array(['SP', 'KP', 'LP', 'GP', 'BP', 'MP', 'EP'])
    elif 'APG_BMY_Only' == node:
        coverage = np.array(['TI','GI', 'MI', 'KI'])
    else:
        print("Undefined network structure. Check value of -n command line argument.")
        exit()

if ac_flag == 'HVAC':
    factor = np.genfromtxt('Data/factor_hvac.csv', delimiter=',', usecols=1)

###### DECISION VARIABLE LIST INDEXES ######
intervals, nodes = MLoad.shape
years = int(resolution * intervals / 8760)
pzones = TSPV.shape[1] # Solar PV and wind sites
# wzones = TSWind.shape[1]
# pidx, widx, phidx = (pzones, pzones + wzones, pzones + wzones + nodes) # Index of solar PV (sites), wind (sites), pumped hydro power (service areas)
pidx, phidx = (pzones, pzones + nodes)
inters = len(Interl) # Number of external interconnections
iidx = phidx + 1 + inters # Index of external interconnections, noting pumped hydro energy (network) and battery energy (network) decision variables after the index of battery power

###### NETWORK CONSTRAINTS ######
energy = (MLoad).sum() * pow(10, -9) * resolution / years # PWh p.a.
contingency_ph = list(0.25 * (MLoad).max(axis=0) * pow(10, -3))[:(nodes)] # MW to GW

#manage = 0 # weeks
allowance = min(0.00002*np.reshape(MLoad.sum(axis=1), (-1, 8760)).sum(axis=-1)) # Allowable annual deficit of 0.002%, MWh


###### DECISION VARIABLE UPPER BOUNDS ######
pv_ub = [x for x in pv_ub_np]
phes_ub = [x for x in phes_ub_np]
phes_s_ub = [10000.]
inters_ub = [500.] * inters if node == 'Super' else inters * [0]

###### DECISION VARIABLE LOWER BOUNDS ######
pv_lb = [.001] * pzones


class Solution:
    """A candidate solution of decision variables CPV(i), CWind(i), CPHP(j), S-CPHS(j)"""

    def __init__(self, x):
        self.x = x
        self.MLoad = MLoad
        self.intervals, self.nodes = (intervals, nodes)
        self.resolution = resolution
        self.baseload = baseload
        #self.indiaExportProfiles = indiaExportProfiles
        self.daily_peaking = daily_peaking

        self.CPV = list(x[: pidx]) # CPV(i), GW
        #self.CWind = list(x[pidx: widx]) # CWind(i), GW
        self.GPV = TSPV * np.tile(self.CPV, (intervals, 1)) * pow(10, 3) # GPV(i, t), GW to MW
        # self.GWind = TSWind * np.tile(self.CWind, (intervals, 1)) * pow(10, 3) # GWind(i, t), GW to MW

        # self.CPHP = [x[phidx]] # CPHP(j), GW
        self.CPHP = list(x[pidx: phidx]) # CPHP(j), GW
        self.CPHS = x[phidx] # S-CPHS(j), GWh
        self.efficiencyPH = efficiencyPH

        self.CInter = list(x[phidx+1: ]) if node == 'Super' else len(Interl)*[0] #CInter(j), GW
        self.GIndia = np.tile(self.CInter, (intervals, 1)) * pow(10,3) # GInter(j, t), GW to MW

        self.Nodel, self.PVl, self.Hydrol = (Nodel, PVl, hydrol)
        self.Interl = Interl
        # self.Windl = Windl
        # self.expl = expl
        self.node = node
        self.scenario = scenario
        self.import_flag = import_flag
        self.allowance = allowance
        self.coverage = coverage
        self.TLoss = TLoss

        self.CHydro_RoR = CHydro_RoR
        self.CHydro_Peaking = CHydro_Peaking
        self.CHydro_max = CHydro_max
        

    def __repr__(self):
        """S = Solution(list(np.ones(64))) >> print(S)"""
        return 'Solution({})'.format(self.x)