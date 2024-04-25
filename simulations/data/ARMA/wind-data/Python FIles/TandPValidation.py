
import pandas as pd
import matplotlib.pyplot as plt
#used to check the influence on temperature or pressure on annual energy
#and creates a boxplot comparing the values
#will need to create separate CSV files containing the SAM output to use

Tfile= '/Users/qianna/python spyder/Wind Stats/Taffect.csv'
Pfile= '/Users/qianna/python spyder/Wind Stats/Paffect2.csv'
SAMfile= '/Users/qianna/python spyder/Wind Stats/SAM Data.csv'

Tdata = pd.read_csv(Tfile)
Pdata = pd.read_csv(Pfile)
SAMdata=pd.read_csv(SAMfile)

# For Temperature variance (25%)
TlowData_annualenergy=Tdata.iloc[0:98,1]
TnormalData_annualenergy=Tdata.iloc[0:98,4]
ThighData_annualenergy=Tdata.iloc[0:98,7]
SAMdata_annualenergy=SAMdata.iloc[0:7,1]

plt.boxplot([TlowData_annualenergy.values, TnormalData_annualenergy.values, ThighData_annualenergy.values,SAMdata_annualenergy.values])
plt.title('Varying Temperature (alpha = 0.17)')
plt.xticks([1,2,3,4], ['-25% T', 'Normal','+25% T','WIND Toolkit Data'])
plt.ylabel('Annual Energy Production / kWh')



# For pressure variance (2.5%)

PlowData_annualenergy=Pdata.iloc[0:98,1]
PnormalData_annualenergy=Pdata.iloc[0:98,4]
PhighData_annualenergy=Pdata.iloc[0:98,7]

fig, ax = plt.subplots()
plt.boxplot([PlowData_annualenergy.values, PnormalData_annualenergy.values, PhighData_annualenergy.values,SAMdata_annualenergy.values])
plt.title('Varying Pressure (alpha = 0.17)')
plt.xticks([1,2,3,4], ['-2.5% P', 'Normal','+2.5% P','WIND Toolkit Data'])
plt.ylabel('Annual Energy Production / kWh')


