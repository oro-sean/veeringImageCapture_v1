import csv
import pandas as pd
import datetime

class VeeringLog:
    def __init__(self, logPath):
        self.logPath = logPath

    def Expedition_To_DF(self):
        with open('/Users/sean/mbp_storage/log-2024Apr03.csv', newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            labels = next(reader)
            num = next(reader)
            del labels[0]
            del num[0]
            columnLabels = dict(zip(num,labels))
            next(reader)
            values = []

            for row in reader:
                record ={}
                for i in range(0,(len(row)-1),2):
                    try:
                        key = row[i]
                        value = float(row[i+1])
                        record[key] = value

                    except:
                        break

                values.append(record)

        df = pd.DataFrame.from_records(values)
        df = df.rename(columns=columnLabels)
        self.log_df = df

    def Select_Variables(self, variables):
        self.log_df = self.log_df[variables].dropna()

    def Add_Time_Zone(self,timeZone):
        self.timeZone = datetime.timedelta(hours=timeZone)

    def Add_Time_Stamp(self):
        conv = lambda x: (datetime.datetime(1899,12,30) + datetime.timedelta(days=x)) + self.timeZone
        self.log_df['timeStamp'] = self.log_df['Utc'].apply(conv)

    def Get_Filter_TS(self,heighLimit,lowLimit):
        upwindPort = self.log_df['timeStamp'].loc[(self.log_df['TWA'] < heighLimit*-1) & (self.log_df['TWA'] > lowLimit*-1)]
        upwindStb = self.log_df['timeStamp'].loc[(self.log_df['TWA'] < lowLimit) & (self.log_df['TWA'] > heighLimit)]
        self.upwindStb =[]
        for ts in list(upwindStb):
            self.upwindStb.append(ts.to_pydatetime().replace(microsecond=0))
        self.upwindPort =[]
        for ts in list(upwindPort):
            self.upwindPort.append(ts.to_pydatetime().replace(microsecond=0))

