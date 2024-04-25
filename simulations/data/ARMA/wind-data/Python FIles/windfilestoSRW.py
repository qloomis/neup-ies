

import pandas as pd
import csv
import numpy as np
import os

#creates a CSV file from a folder containing ARMA files

input_directory1 = '/Users/qianna/python spyder/Proof Of Concept/Input2'
output_directory1 = '/Users/qianna/python spyder/Proof Of Concept/P Data'
counter=1
for filename in os.listdir(input_directory1):
    if filename.endswith('.csv'):
        input_file_path = os.path.join(input_directory1, filename)
        output_file_path = os.path.join(output_directory1, f'decreasedPwinddata._{filename[:-4]}.srw') 
        
        #to delete every other row (for hourly data)
        with open(input_file_path, 'r',encoding='latin-1') as csvfile:
            csv_reader = csv.reader(csvfile)
            data = list(csv_reader)
            n=range(len(data)-1, 2, -2)
            for i in n:
                del data[i]
            
        df1 = pd.DataFrame(data[1:], columns=data[0])
        degreefile1='/Users/qianna/python spyder/degrees.csv'
        df_degrees1=pd.read_csv(degreefile1, header=None)
        degrees1 = df_degrees1.iloc[:8761, 0].values
        #degrees120 = df_degrees.iloc[:8761, 1].values
    
    #adjust windspeed
        windspeedcolumn1=df1['DNI Units']
        wsvalues1=windspeedcolumn1[2:]
        Uanem1=pd.to_numeric(wsvalues1)
    
        zhub1=100
        zanem1=2
        alpha1= 0.17
        adjusted_windspeed1= Uanem1*(zhub1/zanem1)**alpha1
    
    #adjust temperature for 100m
    
        temperaturecolumn1=df1['Temperature Units']
        Tvalues1=temperaturecolumn1[2:]
        T_C1=pd.to_numeric(Tvalues1)
    
        adjusted_temperature1= (T_C1-0.65) #per /100m
    
    #adjust pressure
    
        pressurecolumn1=df1['Pressure Units']
        pvalues1=pressurecolumn1[2:]
        pressure_mbar1=pd.to_numeric(pvalues1)
        pressure_pa1=pressure_mbar1*100
    
        Tb1= T_C1 + 273.15
        h1=zhub1 #height of hub
        hb1=zanem1 #height of ground
        Lb1=0.0065 #lapse rate
        g=9.80665  #gravity (m/s)
        M=0.028964 #molar mass of atmosphere (mols/L)
        R=8.3144 #ideal gas constant (J/K*mol)
        adjusted_pressure= pressure_pa1*((Tb1-(h1-hb1)*Lb1)/Tb1)**(g*M/(R*Lb1))
        patoatm=(adjusted_pressure/101300)*0.975
        # i cant for the life of me figure out the error so here i am
    
    #write file
    
    #specifications
        siteID1=413052
        Timezone1=-8
        Long1=-115.1441193
        Lat1=36.17682648
        Year1=2004
        Height1=100
    
    # Convert integers to floating-point numbers
        
        degrees1 = np.array(degrees1, dtype=float).reshape(-1, 1)
        adjusted_windspeed1 = np.array(adjusted_windspeed1, dtype=float).reshape(-1, 1)
        adjusted_temperature1 = np.array(adjusted_temperature1, dtype=float).reshape(-1, 1)
        adjusted_pressure1 = np.array(patoatm, dtype=float).reshape(-1, 1)
    
    # Concatenate arrays
        data1 = np.concatenate((adjusted_temperature1, adjusted_pressure1, adjusted_windspeed1, degrees1), axis=1)
    # write file
    #<location id>,<city>,<state>,<country>,<year>,<latitude>,<longitude>,<elevation>,<time step in
    #hours>,<number of rows>
        with open(output_file_path,'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([siteID1,'Las Vegas','NV','country??',Year1, Lat1, Long1, 'N/A', 1, 8760])
            writer.writerow([f'Las Vegas Location {counter}'])
            writer.writerow(['Temperature', 'Pressure','Speed','Direction'])
            writer.writerow(['C','atm','m/s','Degrees'])
            writer.writerow([Height1, Height1, Height1, Height1])
            for row in data1:
                writer.writerow(row)
        counter= counter + 1
        print('Export Complete')
