import pandas as pd
import csv
import numpy as np
import os
import matplotlib.pyplot as plt
from scipy.stats import kurtosis
from scipy.stats import skew

# makes a set of boxplots containing the means, STD, skew and kurtosis of
# all the data from the real and synthetic original files by editing and scaling
# the windspeed.
# for SAM comparison, it will need a csv file with all of the years of the
# generated data on it. 



realfile = '/Users/qianna/python spyder/Proof Of Concept/Real Data'
synfile = '/Users/qianna/python spyder/Proof Of Concept/Synthetic Data'
SAMdata= '/Users/qianna/python spyder/Wind Stats/SAM Gen Windspeed.csv'

wind_speed_means_real = []
wind_speed_means_syn = []
wind_speed_means_SAM = []
wind_speed_std_real = []
wind_speed_std_syn = []
wind_speed_std_SAM = []
wind_speed_skew_real=[]
wind_speed_skew_syn=[]
wind_speed_skew_SAM=[]
wind_speed_kurt_real=[]
wind_speed_kurt_syn=[]
wind_speed_kurt_SAM=[]

# Process Real Data
for filename in os.listdir(realfile):
    if filename.endswith('.csv'):
        input_file_path = os.path.join(realfile, filename)
        
        # to delete every other row (for hourly data)
        with open(input_file_path, 'r',encoding='latin-1') as csvfile:
            csv_reader = csv.reader(csvfile)
            data = list(csv_reader)
            n = range(len(data)-1, 2, -2)
            for i in n:
                del data[i]
            
        df1 = pd.DataFrame(data[1:], columns=data[0])
        
        # adjust windspeed
        windspeedcolumn1 = df1['DNI Units']
        wsvalues1 = windspeedcolumn1[2:]
        Uanem1 = pd.to_numeric(wsvalues1)
    
        zhub1 = 100
        zanem1 = 2
        alpha1 = 0.17
        adjusted_windspeedreal = Uanem1 * (zhub1 / zanem1) ** alpha1
        
        # mean windspeed 
        wind_speed_mean = np.mean(adjusted_windspeedreal)
        wind_speed_means_real.append(wind_speed_mean)
        
        #standard deviation
        wind_speed_std = np.std(adjusted_windspeedreal)
        wind_speed_std_real.append(wind_speed_std)
        
        # skewness
        wind_speed_skew = skew(adjusted_windspeedreal)
        wind_speed_skew_real.append(wind_speed_skew)
        
        # kurtosis 
        wind_speed_kurt = kurtosis(adjusted_windspeedreal)
        wind_speed_kurt_real.append(wind_speed_kurt)

        
# Process Synthetic Data
for filename in os.listdir(synfile):
    if filename.endswith('.csv'):
        input_file_path = os.path.join(synfile, filename)
        
        # to delete every other row (for hourly data)
        with open(input_file_path, 'r',encoding='latin-1') as csvfile:
            csv_reader = csv.reader(csvfile)
            data = list(csv_reader)
            n = range(len(data)-1, 2, -2)
            for i in n:
                del data[i]
            
        df1 = pd.DataFrame(data[1:], columns=data[0])
        
        # adjust windspeed
        windspeedcolumn1 = df1['DNI Units']
        wsvalues1 = windspeedcolumn1[2:]
        Uanem1 = pd.to_numeric(wsvalues1)
    
        zhub1 = 100
        zanem1 = 2
        alpha1 = 0.17
        adjusted_windspeedsyn = Uanem1 * (zhub1 / zanem1) ** alpha1
        
        # mean windspeed 
        wind_speed_mean = np.mean(adjusted_windspeedsyn)
        wind_speed_means_syn.append(wind_speed_mean)
        
        #standard deviation
        wind_speed_std = np.std(adjusted_windspeedsyn)
        wind_speed_std_syn.append(wind_speed_std)
        
        # skewness
        wind_speed_skew = skew(adjusted_windspeedsyn)
        wind_speed_skew_syn.append(wind_speed_skew)
        
        # kurtosis 
        wind_speed_kurt = kurtosis(adjusted_windspeedsyn)
        wind_speed_kurt_syn.append(wind_speed_kurt)

#For Obtaining SAM Data from my compiled sheet
SAMdata1 = pd.read_csv(SAMdata)
#Names of the columns
SAM_column_names = list(SAMdata1.columns[::2])
# Extract every other column (assuming columns are 0-indexed)
SAM_wind_data = SAMdata1.iloc[:, ::2]  # Select every other column

# Calculate statistics for each column of SAM data
wind_speed_means_SAM = list(np.mean(SAM_wind_data, axis=0))
wind_speed_std_SAM = np.std(SAM_wind_data, axis=0)
wind_speed_skew_SAM = skew(SAM_wind_data, axis=0)
wind_speed_kurt_SAM = kurtosis(SAM_wind_data, axis=0)


# # Plotting boxplots
plt.boxplot([wind_speed_means_real, wind_speed_means_syn, wind_speed_means_SAM])
plt.title('Distribution of the Mean')
plt.ylabel('Mean Windspeed (m/s)')
plt.xticks([1, 2, 3], ['Scaled Real Data', 'Scaled Synthetic Data','WIND Toolkit Data'])
plt.show()

fig, ax = plt.subplots()
plt.boxplot([wind_speed_std_real, wind_speed_std_syn,wind_speed_std_SAM])
plt.title('Distribution of the Standard Deviation')
plt.ylabel('Standard Deviation (m/s)')
plt.xticks([1, 2, 3], ['Scaled Real Data', 'Scalded Synthetic Data','WIND Toolkit Data'])
plt.show()

fig, ax = plt.subplots()
plt.boxplot([wind_speed_skew_real, wind_speed_skew_syn,wind_speed_skew_SAM])
plt.title('Distribution of the Skewness')
plt.ylabel('Skewness')
plt.xticks([1, 2, 3], ['Scaled Real Data', 'Scaled Synthetic Data','WIND Toolkit Data'])
plt.show()

fig, ax = plt.subplots()
plt.boxplot([wind_speed_kurt_real, wind_speed_kurt_syn,wind_speed_kurt_SAM])
plt.title('Distribution of the Kurtosis')
plt.ylabel('Kurtosis')
plt.xticks([1, 2, 3], ['Scaled Real Data', 'Scaled Synthetic Data','WIND Toolkit Data'])
plt.show()

# Creating CSV File for the Means
# Create DataFrames for real, synthetic, and SAM means
# real_means_df = pd.DataFrame({'Real File Name': os.listdir(realfile), 'Real Mean': wind_speed_means_real})
# synthetic_means_df = pd.DataFrame({'Synthetic File Name': os.listdir(synfile), 'Synthetic Mean': wind_speed_means_syn})
# SAM_means_df = pd.DataFrame({'SAM File Name': SAM_column_names, 'SAM Mean': wind_speed_means_SAM})

# #Define output path and write to the file 
# means_output_file = '/Users/qianna/python spyder/Proof Of Concept/Means_Data.csv'

# means_final_df = pd.concat([real_means_df, synthetic_means_df, SAM_means_df], axis=1)
# means_final_df.to_csv(means_output_file, index=False)


# # Creating CSV file for the STD
# # Create DataFrames for real, synthetic, and SAM STD
# real_std_df = pd.DataFrame({'Real File Name': os.listdir(realfile), 'Scaled Real STD': wind_speed_std_real})
# synthetic_std_df = pd.DataFrame({'Synthetic File Name': os.listdir(synfile), 'Scaled Synthetic STD': wind_speed_std_syn})
# SAM_std_df = pd.DataFrame({'SAM File Name': SAM_column_names, 'SAM STD': wind_speed_std_SAM})

# #Define and write
# std_output_file = '/Users/qianna/python spyder/Proof Of Concept/STD_Data.csv'

# std_final_df = pd.concat([real_std_df, synthetic_std_df, SAM_std_df], axis=1)
# std_final_df.to_csv(std_output_file, index=False)

# # Creating CSV file for the Kurtosis

# real_kurt_df = pd.DataFrame({'Real File Name': os.listdir(realfile), 'Real Kurtosis': wind_speed_kurt_real})
# synthetic_kurt_df = pd.DataFrame({'Synthetic File Name': os.listdir(synfile), 'Synthetic Kurtosis': wind_speed_kurt_syn})
# SAM_kurt_df = pd.DataFrame({'SAM File Name': SAM_column_names, 'SAM Kurtosis': wind_speed_kurt_SAM})

# #Define and write
# kurt_output_file = '/Users/qianna/python spyder/Proof Of Concept/Kurtosis_Data.csv'

# kurt_final_df = pd.concat([real_kurt_df, synthetic_kurt_df, SAM_kurt_df], axis=1)
# kurt_final_df.to_csv(kurt_output_file, index=False)



# # Creating CSV file for the Skew
# real_skew_df = pd.DataFrame({'Real File Name': os.listdir(realfile), 'Real Skew': wind_speed_skew_real})

# synthetic_skew_df = pd.DataFrame({'Synthetic File Name': os.listdir(synfile), 'Synthetic Skew': wind_speed_skew_syn})
# SAM_skew_df = pd.DataFrame({'SAM File Name': SAM_column_names, 'SAM Skew': wind_speed_skew_SAM})

# #Define and write
# skew_output_file = '/Users/qianna/python spyder/Proof Of Concept/Skew_Data.csv'

# skew_final_df = pd.concat([real_skew_df, synthetic_skew_df, SAM_skew_df], axis=1)
# skew_final_df.to_csv(skew_output_file, index=False)


