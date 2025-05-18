# To optimise the configurations of energy generation, storage and transmission assets 
# Copyright (c) 2019, 2020 Bin Lu, The Australian National University
# Licensed under the MIT Licence

from scipy.optimize import differential_evolution
from argparse import ArgumentParser
import datetime as dt
import csv
import os

parser = ArgumentParser()
parser.add_argument('-i', default=400, type=int, required=False, help='maxiter=4000, 400')
parser.add_argument('-p', default=2, type=int, required=False, help='popsize=2, 10')
parser.add_argument('-m', default=0.5, type=float, required=False, help='mutation=0.5')
parser.add_argument('-r', default=0.3, type=float, required=False, help='recombination=0.3')
parser.add_argument('-e', default=2, type=int, required=False, help='per-capita electricity = 2, 5, 9 MWh/year')
parser.add_argument('-n', default='Super', type=str, required=False, help='Super, SP, KP...')
parser.add_argument('-s', default='existing', type=str, required=False, help='existing,construction')
parser.add_argument('-y', default='import', type=str, required=False, help='import, no_import')
parser.add_argument('-x', default='no_export', type=str, required=False, help='export, no_export')


args = parser.parse_args()

scenario = args.s
node = args.n
percapita = args.e
import_flag = (args.y == 'import')
export_flag = (args.x == 'export')

from Input import *
from Simulation import Reliability
from Network import Transmission

def F(x):
    """This is the objective function."""

    # Initialise the optimisation
    S = Solution(x)

    CIndia = np.nan_to_num(np.array(S.CInter))
    india_imports = np.zeros(intervals)
    if import_flag:
        Deficit_energy1, Deficit_power1, Deficit1, DischargePH1, DischargePeaking1, Spillage1, IndiaExport1 = Reliability(
            S, baseload=baseload, india_imports=np.zeros(intervals), daily_peaking=daily_peaking, peaking_hours=peaking_hours, export_flag=export_flag)
        Max_deficit1 = np.reshape(Deficit1, (-1, 8760)).sum(axis=-1)
        PIndia = Deficit1.max() * pow(10, -3)  # GW
        GIndia = resolution * (Max_deficit1).max() / efficiencyPH

        PenPower = abs(PIndia - CIndia.sum()) * 1e3
        PenEnergy = 0

        Deficit_energy, Deficit_power, Deficit, DischargePH, DischargePeaking, Spillage, IndiaExport = Reliability(
            S, baseload=baseload, india_imports=np.ones(intervals) * CIndia.sum() * 1e3, daily_peaking=daily_peaking, peaking_hours=peaking_hours, export_flag=export_flag)

        PenDeficit = max(0, Deficit.sum() * resolution - S.allowance)

        india_imports = np.clip(Deficit1, 0, CIndia.sum() * 1e3)

        Deficit_energy, Deficit_power, Deficit, DischargePH, DischargePeaking, Spillage, IndiaExport = Reliability(
            S, baseload=baseload, india_imports=india_imports, daily_peaking=daily_peaking, peaking_hours=peaking_hours, export_flag=export_flag)

        GPHES = DischargePH.sum() * resolution / years * 1e-6
        
    else:
        PenPower = 0
        PenEnergy = 0
        india_imports = np.zeros(intervals)

        Deficit_energy, Deficit_power, Deficit, DischargePH, DischargePeaking, Spillage, IndiaExport = Reliability(
            S, baseload=baseload, india_imports=india_imports, daily_peaking=daily_peaking, peaking_hours=peaking_hours, export_flag=export_flag)

        PenDeficit = max(0, Deficit.sum() * resolution - S.allowance)

        GPHES = DischargePH.sum() * resolution / years * 1e-6

    TDC = Transmission(S, domestic_only=True, output=True) if 'Super' in node else np.zeros((intervals, len(TLoss)))
    CAC = np.amax(abs(TDC), axis=0) * 1e-3  # MW to GW

    PenDC = 0

    GHydro = resolution * (baseload.sum() + DischargePeaking.sum()) / efficiencyPH / years #MWh
    GIndia = resolution * india_imports.sum() / years / efficiencyPH #MWh

    # EXPORT: Add export energy and revenue
    GExport = S.IndiaExport.sum() * resolution / years / efficiencyPH  #TWh
    export_price = factor[1]  # same as India import price (e.g., factor[1] for India) #$/Kwh

    export_revenue = GExport * export_price  * 1e-6 # $b/year

    # Levelised cost of electricity calculation
    cost = factor * np.array([sum(S.CPV), GIndia * 1e-6, sum(S.CPHP), S.CPHS, GPHES] + list(CAC) + [sum(S.CPV), GHydro * 1e-6, 0, 0])
    cost = cost.sum() #- export_revenue  # subtract export revenue

    loss = np.sum(abs(TDC), axis=0) * TLoss
    loss = loss.sum() * 1e-9 * resolution / years  # PWh/year
    LCOE = cost / abs(energy - loss)

    if not os.path.exists('Results'):
        os.makedirs('Results')

    with open('Results/record_{}_{}_{}_{}_{}.csv'.format(node, scenario, percapita, import_flag, export_flag), 'a', newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(np.append(x, [PenDeficit+PenEnergy+PenPower+PenDC, PenDeficit, PenEnergy, PenPower, LCOE, GExport]))

    Func = LCOE + PenDeficit + PenEnergy + PenPower + PenDC
    return Func

if __name__=='__main__':
    starttime = dt.datetime.now()
    print("Optimisation starts at", starttime)

    lb = pv_lb + [0.] * nodes + [0.] + [0.] * inters
    ub = pv_ub + phes_ub + phes_s_ub + inters_ub

    result = differential_evolution(func=F, bounds=list(zip(lb, ub)), tol=0,
                                    maxiter=args.i, popsize=args.p, mutation=args.m, recombination=args.r,
                                    disp=True, polish=False, updating='deferred', workers=-1)

    with open('Results/Optimisation_resultx_{}_{}_{}_{}_{}.csv'.format(node, scenario, percapita, import_flag, export_flag), 'w', newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(result.x)

    endtime = dt.datetime.now()
    print("Optimisation took", endtime - starttime)

    from Fill import Analysis
    Analysis(result.x, '_{}_{}_{}_{}_{}.csv'.format(node, scenario, percapita, import_flag, export_flag))
