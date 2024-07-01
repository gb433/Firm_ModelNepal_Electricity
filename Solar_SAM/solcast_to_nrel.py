import pandas as pd
import os

def convert_nrel(input_csv, latitude, longitude, elevation, output_dir):
    # Load the CSV data
    df = pd.read_csv(input_csv)

    # Rename the columns
    df.rename(columns={
        'AirTemp': 'Temperature',
        'Dhi': 'DHI',
        'Dni': 'DNI',
        'Ghi': 'GHI',
        'RelativeHumidity': 'Relative Humidity',
        'WindDirection10m': 'Wind Direction',
        'WindSpeed10m': 'Wind Speed'
    }, inplace=True)

    # Convert 'PeriodStart' to datetime, shift to UTC, then to Asia/Kathmandu time zone
    df['PeriodStart'] = pd.to_datetime(df['PeriodStart']).dt.tz_convert('UTC').dt.tz_convert('Asia/Kathmandu')

    # Change the datetime format to 'mm/dd/yyyy hh:mm'
    df['PeriodStart'] = df['PeriodStart'].dt.strftime('%m/%d/%Y %H:%M')

    # Add date columns
    df['PeriodStart'] = pd.to_datetime(df['PeriodStart'])
    df['Year'] = df['PeriodStart'].dt.year
    df['Month'] = df['PeriodStart'].dt.month
    df['Day'] = df['PeriodStart'].dt.day
    df['Hour'] = df['PeriodStart'].dt.hour
    df['Minute'] = df['PeriodStart'].dt.minute

    # Remove rows for 29th February
    df = df[~((df['Month'] == 2) & (df['Day'] == 29))]

    # Define header rows
    header1 = [
        'Source', 'Location ID', 'City', 'State', 'Country', 'Latitude', 'Longitude', 'Time Zone', 'Elevation',
        'Local Time Zone', 'DNI Units', 'DHI Units', 'GHI Units', 'Temperature Units', 'Relative Humidity Units',
        'Wind Direction Units', 'Wind Speed Units'
    ]
    header2 = [
        'Solcast', '-', '-', '-', '-', latitude, longitude, 5.75 , elevation, 5.75, 'w/m2', 'w/m2', 'w/m2',
        'c', '%', 'Degrees', 'm/s'
    ]

    # Filter data by year and write to CSV
    for year in range(2013, 2023):
        df_year = df[df['Year'] == year][[
            'Year', 'Month', 'Day', 'Hour', 'Minute', 'DNI', 'DHI', 'GHI', 'Temperature',
            'Relative Humidity', 'Wind Direction', 'Wind Speed'
        ]]
        
        # Write to CSV with header rows
        output_file = f'{output_dir}/NREL_{year}_{latitude}_{longitude}.csv'
        with open(output_file, 'w') as f:
            f.write(','.join(header1) + '\n')
            f.write(','.join(map(str, header2)) + '\n')
        df_year.to_csv(output_file, mode='a', index=False)

if __name__ == '__main__':
    input_dir = '/Users/geetabhatta/Documents/Firm_ModelNepal_Electricity/Solar_SAM/Solcast'
    output_dir = '/Users/geetabhatta/Documents/Firm_ModelNepal_Electricity/Solar_SAM/NREL_Output'

    # Create the output directory if it does not exist
    os.makedirs(output_dir, exist_ok=True)

    # Print the contents of the input directory for debugging
    print("Listing contents of input directory:")
    for root, dirs, files in os.walk(input_dir):
        for name in files:
            print(os.path.join(root, name))

    # Define a list of files and their corresponding latitudes, longitudes, and elevations
    file_info = [
        ('Node1_Site1_26.7908_87.6376_Solcast_PT60M.csv', 26.7908, 87.6376, 668),
        ('Node1_Site2_26.9784_87.0945_Solcast_PT60M.csv', 26.9784, 87.0945, 661),
        ('Node1_Site3_27.087_86.7587_Solcast_PT60M.csv', 27.087, 86.7587, 1081),
        ('Node1_Site4_27.3141_87.6968_Solcast_PT60M.csv', 27.3141, 87.6968, 1297),
        ('Node1_Site5_27.3141_87.1537_Solcast_PT60M.csv', 27.3141, 87.1537, 791),
        ('Node1_Site6_27.7179_87.3067_Solcast_PT60M.csv', 27.7179, 87.3067, 2192),
        ('Node2_Site1_26.9138_85.7204_Solcast_PT60M.csv', 26.9138, 85.7204, 112),
        ('Node2_Site2_26.9435_85.214_Solcast_PT60M.csv', 26.9435, 85.214, 91),
        ('Node2_Site3_26.5663_86.6735_Solcast_PT60M.csv', 26.5663, 86.6735, 95),
        ('Node3_Site1_27.5409_85.671_Solcast_PT60M.csv', 27.5409, 85.671, 1303),
        ('Node3_Site2_27.9373_85.1109_Solcast_PT60M.csv', 27.9373, 85.1109, 668),
        ('Node3_Site3_27.7551_86.1999_Solcast_PT60M.csv', 27.7551, 86.1999, 1374),
        ('Node4_Site1_27.8507_84.1951_Solcast_PT60M.csv', 27.8507, 84.1951, 289),
        ('Node4_Site3_28.3565_84.628_Solcast_PT60M.csv', 28.3565, 84.628, 4011),
        ('Node5_Site1_27.5328_83.1894_Solcast_PT60M.csv', 27.5328, 83.1894, 98),
        ('Node5_Site3_28.4229_82.7561_Solcast_PT60M.csv', 28.4229, 82.7561, 2951),
        ('Node6_Site1_28.4782_82.1175_Solcast_PT60M.csv', 28.4782, 82.1175, 1562),
        ('Node6_Site3_28.855_82.2588_Solcast_PT60M.csv', 28.855, 82.2588, 2214),
        ('Node7_Site1_28.9754_80.6335_Solcast_PT60M.csv', 28.9754, 80.6335, 1675)
    ]

    for file_name, latitude, longitude, elevation in file_info:
        input_csv = f'{input_dir}/{file_name}'
        if os.path.exists(input_csv):
            print(f'Converting {input_csv}...')
            convert_nrel(input_csv, latitude, longitude, elevation, output_dir)
            print('Conversion complete!')
        else:
            print(f'File not found: {input_csv}')
