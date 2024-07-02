import PySAM
import PySAM.Pvwattsv8 as pvwatts
import pandas as pd
import os
import re

def preprocess_weather_file(input_file, output_file):
    # Read the file skipping the first two rows
    df = pd.read_csv(input_file, skiprows=2)
    
    # Read latitude, longitude, and elevation from the second row
    with open(input_file, 'r') as f:
        lines = f.readlines()
        second_row = lines[1].strip().split(',')
        latitude = float(second_row[5])  # Assuming latitude is at index 5
        longitude = float(second_row[6])  # Assuming longitude is at index 6
        elevation = float(second_row[8])  # Assuming elevation is at index 8
    
    # Ensure all required columns are present
    required_columns = ['Year', 'Month', 'Day', 'Hour', 'Minute', 'DNI', 'DHI', 'GHI', 'Temperature', 'Relative Humidity', 'Wind Direction', 'Wind Speed']
    
    # Check and handle case sensitivity or additional spaces
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"The file {input_file} is missing columns: {', '.join(missing_columns)}")
    
    # Save the cleaned file
    df.to_csv(output_file, index=False)
    
    return latitude, longitude, elevation

def run_pvwatts_simulation(solar_resource_file, output_file, latitude, longitude, elevation):
    model = pvwatts.default("PVWattsNone")

    model.SolarResource.solar_resource_file = solar_resource_file
    model.SolarResource.lat = latitude
    model.SolarResource.lon = longitude
    model.SolarResource.elev = elevation  # Set elevation

    model.SystemDesign.system_capacity = 4
    model.SystemDesign.dc_ac_ratio = 1.15
    model.SystemDesign.tilt = 20
    model.SystemDesign.azimuth = 180
    model.SystemDesign.inv_eff = 96
    model.Lifetime.system_use_lifetime_output = 0
    model.SystemDesign.losses = 14.08
    model.SystemDesign.module_type = 1  # Standard
    model.SystemDesign.array_type = 1
    model.SystemDesign.gcr = 0.3

    try:
        model.execute()
    except Exception as e:
        print(f"Exception: {e}")
        return

    ac = model.Outputs.ac
    pd.DataFrame(ac, columns=['ac']).to_csv(output_file, index=False)

if __name__ == '__main__':
    input_dir = '/Users/geetabhatta/Documents/Firm_ModelNepal_Electricity/Solar_SAM/NREL_Output'
    output_dir = '/Users/geetabhatta/Documents/Firm_ModelNepal_Electricity/Solar_SAM/SAM_Output'
    
    lats = [str(x) for x in [26.7908, 26.9784, 27.087, 27.3141, 27.3141, 27.7179, 26.9138, 26.9435, 26.5663, 27.5409, 27.9373, 27.7551, 27.8507, 28.3565, 27.5328, 28.4229, 28.4782, 28.855, 28.9754]]
    longs = [str(x) for x in [87.6376, 87.0945, 86.7587, 87.6968, 87.1537, 87.3067, 85.7204, 85.214, 86.6735, 85.671, 85.1109, 86.1999, 84.1951, 84.628, 83.1894, 82.7561, 82.1175, 82.2588, 80.6335]]
    years = list(range(2013, 2023))  # Adjusted to include up to 2022

    for i in range(len(lats)):
        latitude = float(lats[i])
        longitude = float(longs[i])
        combo_str = f"{latitude}_{longitude}"
        
        for year in years:
            nrel_file = os.path.join(input_dir, f'NREL_{year}_{combo_str}.csv')
            output_file = os.path.join(output_dir, f'PVWatts_{year}_{combo_str}.csv')
            
            # Preprocess weather file
            try:
                preprocess_weather_file(nrel_file, nrel_file)  # Overwrite the original file with preprocessed data
            except Exception as e:
                print(f"Error preprocessing {nrel_file}: {e}")
                continue
            
            # Run PVWatts simulation
            try:
                elevation = None  # You need to extract elevation from the file in preprocess_weather_file function
                run_pvwatts_simulation(nrel_file, output_file, latitude, longitude, elevation)
            except Exception as e:
                print(f"Error running PVWatts simulation for {nrel_file}: {e}")
                continue
        
        print(f'Simulations complete for {lats[i]}, {longs[i]}!')

