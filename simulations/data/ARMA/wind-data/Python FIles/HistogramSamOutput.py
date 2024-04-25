
import pandas as pd
import matplotlib.pyplot as plt

#will need to set up csv file in a way that it can extract SAM outputs 
#and create boxplots this way

file= '/Users/qianna/python spyder/Wind Stats/0.16 Wind Statistics.csv'
data = pd.read_csv(file)

synData_annualenergy=data.iloc[0:98,1]
realData_annualenergy=data.iloc[0:22,6]

SAMGen_annualenergy=data.iloc[0:7,11]
#
synData_CapacityFactor=data.iloc[0:98,2]
realData_CapacityFactor=data.iloc[0:22,7]
SAMGen_CapacityFactor=data.iloc[0:7,12]

synData_NPV=data.iloc[0:98,3]
realData_NPV=data.iloc[0:22,8]
SAMGen_NPV=data.iloc[0:7,13]

plt.boxplot([synData_annualenergy.values, realData_annualenergy.values, SAMGen_annualenergy.values], labels=['Synthetic Data','Real Data','SAM Data'])
plt.title('Alpha 0.16')
plt.xticks([1,2,3], ['Scaled Synthetic Data', 'Scaled Real Data','WIND Toolkit Data'])
plt.ylabel('Annual Energy Production / kWh')


fig, ax = plt.subplots()

# Annual Energy Production
ax.hist(synData_annualenergy, bins=10, alpha=0.5, label='Scaled Synthetic Data',histtype='bar',edgecolor='blue',color='white')
ax.hist(realData_annualenergy, bins=10, alpha=0.5, label='Scaled Real Data',histtype='bar',edgecolor='red',color='white')
ax.hist(SAMGen_annualenergy, bins=10, alpha=0.5, label='WIND Toolkit Data',histtype='bar',edgecolor='green',color='white')
plt.title('Histogram for each year Annual Energy Production')
plt.xlabel('Annual Energy Production / kWh')
plt.ylabel('Frequency')
plt.legend()

plt.show()

fig, ax = plt.subplots()

# Capacity Factor
ax.hist(synData_CapacityFactor, bins=10, alpha=0.5, label='Scaled Synthetic Data',edgecolor='blue',color='white')
ax.hist(realData_CapacityFactor, bins=10, alpha=0.5, label='Scaled Real Data',edgecolor='red',color='white')
ax.hist(SAMGen_CapacityFactor, bins=10, alpha=0.5, label='WIND Toolkit Data',edgecolor='green',color='white')
plt.title('Histogram for each year Capacity Factor')
plt.xlabel('Capacity Factor (%)')
plt.ylabel('Frequency')
plt.legend()

plt.show()

# NPV
fig, ax = plt.subplots()
ax.hist(synData_NPV, bins=10, alpha=0.5, label='Scaled Synthetic Data',edgecolor='blue',color='white')
ax.hist(realData_NPV, bins=10, alpha=0.5, label='Scaled Real Data',edgecolor='red',color='white')
ax.hist(SAMGen_NPV, bins=10, alpha=0.5, label='WIND Toolkit Data',edgecolor='green',color='white')
plt.title('Histogram for each year NPV')
plt.xlabel('NPV')
plt.ylabel('Frequency')
plt.legend()

plt.show()
