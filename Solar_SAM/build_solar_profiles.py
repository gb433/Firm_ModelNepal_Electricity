import pandas as pd

def create_profiles(lats, longs, years, output_file):
    # Initialize an empty DataFrame
    final_df = pd.DataFrame()

    for i in range(0,len(lats)):
        latitude = lats[i]
        longitude = longs[i]

        combo_str = latitude+'_'+longitude

        site_files = []
        for year in years:
            site_files.append(input_dir+'/PVWatts_' + str(year)+'_'+combo_str+'.csv')

        location_df = pd.DataFrame()

        # Loop through all files and append them to the DataFrame
        for file in site_files:
            temp_df = pd.read_csv(file)
            location_df = location_df.append(temp_df, ignore_index=True)

        # Divide all the values by 4000
        location_df['ac'] = location_df['ac'] / 4000

        # Add this location's data as a new column in the final DataFrame
        final_df[str(i)] = location_df['ac']

    # Write the resulting DataFrame to a new CSV file
    final_df.to_csv(output_file, index=False)  

if __name__ == '__main__':
    input_dir = '/Users/geetabhatta/Documents/Firm_ModelNepal_Electricity/Solar_SAM/SAM_Output'
    output_dir = '/Users/geetabhatta/Documents/Firm_ModelNepal_Electricity/Solar_SAM/PV_Output'

    lats = [str(x) for x in [26.7908, 26.9784, 27.087, 27.3141, 27.3141, 27.7179, 26.9138, 26.9435, 26.5663, 27.5409, 27.9373, 27.7551, 27.8507, 28.3565, 27.5328, 28.4229, 28.4782, 28.855, 28.9754]]
    longs = [str(x) for x in [87.6376, 87.0945, 86.7587, 87.6968, 87.1537, 87.3067, 85.7204, 85.214, 86.6735, 85.671, 85.1109, 86.1999, 84.1951, 84.628, 83.1894, 82.7561, 82.1175, 82.2588, 80.6335]]
    years = list(range(2013, 2023))  # Adjusted to include up to 2022


    output_file = output_dir + '/pv.csv'

    create_profiles(lats, longs, years, output_file)

    
        
        