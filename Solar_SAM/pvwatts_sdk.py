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

def run_pvwatts_simulation(solar_resource_file, latitude, longitude, elevation, output_file):
    model = pvwatts.default("PVWattsNone")

    model.SolarResource.solar_resource_file = solar_resource_file
    model.SolarResource.lat = latitude
    model.SolarResource.lon = longitude
    model.SolarResource.elev = elevation  # Set elevation
    model.SolarResource.use_wf_albedo = 1

    model.SystemDesign.system_capacity = 4
    model.SystemDesign.dc_ac_ratio = 1.2
    model.SystemDesign.tilt = 0
    model.SystemDesign.azimuth = 180
    model.SystemDesign.inv_eff = 96
    model.Lifetime.system_use_lifetime_output = 0
    model.SystemDesign.losses = 14.08
    model.SystemDesign.module_type = 1
    model.SystemDesign.array_type = 2
    model.SystemDesign.gcr = 0.4

    try:
        model.execute()
    except Exception as e:
        print(f"Exception: {e}")
        return

    ac = model.Outputs.ac
    pd.DataFrame(ac, columns=['ac']).to_csv(output_file, index=False)

if __name__ == '__main__':
    input_dir = '/Users/geetabhatta/DataScience/Tools/NREL_Output'
    output_dir = '/Users/geetabhatta/DataScience/Tools/SAM_Output'

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    files = os.listdir(input_dir)

    for file in files:
        if re.match(r'NREL_\d{4}_\d+\.\d+_\d+\.\d+\.csv', file):
            input_file = os.path.join(input_dir, file)
            processed_file = os.path.join(input_dir, f'Processed_{file}')
            output_file = os.path.join(output_dir, f'PVWatts_{file}')

            latitude, longitude, elevation = preprocess_weather_file(input_file, processed_file)
            
            run_pvwatts_simulation(processed_file, latitude, longitude, elevation, output_file)
            print(f'Simulation complete for {file}')
