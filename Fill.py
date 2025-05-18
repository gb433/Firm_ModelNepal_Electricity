# -*- coding: utf-8 -*-
"""
Created on Mon Dec  7 14:17:37 2020
@author: cheng + tim
adapted by Geeta – Export logic integrated (2025)
"""

from Input import *
from Simulation import Reliability
import numpy as np
import datetime as dt

def fill_deficit(deficit, india_imports, india_limit, india_annual, impflag, eff, step):
    idx = np.where(deficit > 0)[0]
    for idd, i in np.ndenumerate(idx):
        d = deficit[i]
        t = i
        count = 0
        try:
            while d > 0 and t >= 0 and count < step:
                year = t // 8760
                start = year * 8760
                end = (year + 1) * 8760
                if t == i - 1:
                    d = d / eff
                if impflag:
                    remaining = india_annual - sum(india_imports[start:end])
                    hydro_c = min(india_imports[t] + d, india_limit, india_imports[t] + remaining)
                    d = d - (hydro_c - india_imports[t])
                    india_imports[t] = hydro_c
                    if remaining == 0:
                        t = start - 1
                    else:
                        idxx = np.where(india_imports < india_limit)[0]
                        t = sorted([i for i in idxx if i < t])[-1]
                count += 1
        except:
            continue
    return india_imports

def save(arr, suffix, name='Dispatch_IndiaImports'):
    np.savetxt(f'Results/{name}{suffix}', arr, fmt='%f', delimiter=',', newline='\n',
               header=name.replace('_', ' '))

def maxx(x):
    return np.reshape(x, (-1, 8760)).sum(axis=-1).max() / 1e6

def mean(x):
    return x.sum() / years / 1e6

def Analysis(optimisation_x, suffix):
    from Optimisation import export_flag
    starttime = dt.datetime.now()
    print('Deficit fill starts at', starttime)

    S = Solution(optimisation_x)

    # First run: zero imports, see how much deficit
    Deficit_energy1, Deficit_power1, Deficit1, DischargePH1, DischargePeaking1, Spillage1, IndiaExport1 = \
        Reliability(S, baseload=baseload, india_imports=np.zeros(intervals), daily_peaking=daily_peaking, peaking_hours=peaking_hours, export_flag=True)
    Max_deficit1 = np.reshape(Deficit1, (-1, 8760)).sum(axis=-1)
    PIndia = Deficit1.max() * 1e-3
    GIndia = resolution * (Max_deficit1).max() / efficiencyPH

    print("GIndia max:", GIndia / 1e6)

    # Start with zero imports
    india_imports = np.zeros(intervals)
    Deficit_energy, Deficit_power, Deficit, DischargePH, DischargePeaking, Spillage, IndiaExport = \
        Reliability(S, baseload=baseload, india_imports=india_imports, daily_peaking=daily_peaking, peaking_hours=peaking_hours, export_flag=True)

    Indiamax = energy * 1e9  # MWh/year
        # Fix: Avoid imports if import_flag is False
    if S.import_flag:
        imp = fill_deficit(Deficit, india_imports, sum(S.CInter) * 1e3, Indiamax, True, 0.8, 168)
    else:
        imp = np.zeros(intervals)

    # Re-run with imports filled
    Deficit_energy, Deficit_power, Deficit, DischargePH, DischargePeaking, Spillage, IndiaExport = \
        Reliability(S, baseload=baseload, india_imports=imp, daily_peaking=daily_peaking, peaking_hours=peaking_hours, export_flag=True)


    print("India generation max:", maxx(imp))
    print("Remaining deficit:", Deficit.sum() / 1e6)

    # Iteratively fill remaining deficits (if any)
    step = 1
    while Deficit.sum() > allowance * years and step < 50:
        imp = fill_deficit(Deficit, imp, sum(S.CInter) * 1e3, Indiamax, True, 0.8, 168)
        Deficit_energy, Deficit_power, Deficit, DischargePH, DischargePeaking, Spillage, IndiaExport = \
            Reliability(S, baseload=baseload, india_imports=imp, daily_peaking=daily_peaking, peaking_hours=peaking_hours, export_flag=True)
        step += 1
    print("Max Import MW:", np.max(imp))
    print("CInter MW:", sum(S.CInter) * 1e3)
    print("Nonzero export hours:", np.count_nonzero(S.IndiaExport))
    print("Total Export MW:", S.IndiaExport.sum())
    print("India generation final (mean):", mean(imp))
    print("Remaining deficit final:", Deficit.sum() / 1e6)

    # Save final import and export profiles
    save(imp, suffix, name='Dispatch_IndiaImports')
    save(S.IndiaExport, suffix, name='Dispatch_IndiaExport')

    endtime = dt.datetime.now()
    print('Deficit fill took', endtime - starttime)

    # Run statistics
    from Statistics import Information
    Information(optimisation_x, imp, IndiaExport)

    return True

if __name__ == '__main__':
    suffix = "_Super_existing_2_True_True.csv"
    optimisation_x = np.genfromtxt('Results/Optimisation_resultx{}'.format(suffix), delimiter=',')
    Analysis(optimisation_x, suffix)