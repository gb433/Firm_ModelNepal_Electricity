import pandas as pd
import os

def create_profiles(lats, longs, years, input_dir, output_file):
    # Initialize an empty DataFrame for the final output
    final_df = pd.DataFrame()

    for i in range(len(lats)):
        latitude = lats[i]
        longitude = longs[i]
        combo_str = latitude + '_' + longitude

        # Initialize an empty DataFrame for the current location
        location_df = pd.DataFrame()

        # Loop through each year and append the data to location_df
        for year in years:
            file_path = os.path.join(input_dir, f'PVWatts_{year}_{combo_str}.csv')
            if os.path.exists(file_path):
                temp_df = pd.read_csv(file_path)
                location_df = location_df.append(temp_df, ignore_index=True)
            else:
                print(f"File {file_path} does not exist.")

        # Normalize the 'ac' values by dividing by 4000
        if 'ac' in location_df.columns:
            location_df['ac'] = location_df['ac'] / 4000
        else:
            print(f"'ac' column not found in {combo_str} data.")
            continue

        # Add this location's data as a new column in the final DataFrame
        final_df[combo_str] = location_df['ac']

    # Write the resulting DataFrame to a new CSV file
    final_df.to_csv(output_file, index=False)
    print(f"Output written to {output_file}")

if __name__ == '__main__':
    input_dir = '/Users/geetabhatta/Documents/Firm_ModelNepal_Electricity/Solar_SAM/SAM_Output'
    output_dir = '/Users/geetabhatta/Documents/Firm_ModelNepal_Electricity/Solar_SAM/PV_Output'
    output_file = os.path.join(output_dir, 'pv_combined_profile.csv')

    lats = [str(x) for x in [26.7908, 26.9784, 27.087, 27.3141, 27.3141, 27.7179, 26.9138, 26.9435, 26.5663, 27.5409, 27.9373, 27.7551, 27.8507, 28.3565, 27.5328, 28.4229, 28.4782, 28.855, 28.9754]]
    longs = [str(x) for x in [87.6376, 87.0945, 86.7587, 87.6968, 87.1537, 87.3067, 85.7204, 85.214, 86.6735, 85.671, 85.1109, 86.1999, 84.1951, 84.628, 83.1894, 82.7561, 82.1175, 82.2588, 80.6335]]
    years = list(range(2013, 2022))  # From 2013 to 2021 inclusive

    create_profiles(lats, longs, years, input_dir, output_file)
