import os
import pandas as pd
import datetime
import ffmpeg
import csv
import cv2
from PIL import Image
import piexif
import asyncio
import numpy as np
#from open_gopro import WiredGoPro

class Video_TimeStamping:
    def __init__(self,folder):
        self.folder = folder

    def GetFiles(self):
        self.files = os.listdir(self.folder)

    def SortFiles(self):
        videos = []
        chapters = []
        prefix = []
        suffix = []
        s=''
        for file in self.files:
            if file.endswith('.MP4'):
                videos.append(s.join(list(file)[4:8]))
                chapters.append(s.join(list(file)[2:4]))
                prefix.append(s.join(list(file)[:2]))
                suffix.append(s.join(list(file)[8:]))

        df = pd.DataFrame({'video': videos, 'chapter': chapters, 'prefix': prefix, 'suffix':suffix})
        df.sort_values(by=['video', 'chapter'],inplace=True, ignore_index=True)

        files = []
        currentVideo = []
        firstChapters_ind = []
        otherChapters_ind = []
        for i in range(len(df)):
            if currentVideo != str(df['video'][i]):
                currentVideo = str(df['video'][i])
                firstChapters_ind.append(i)
            else:
                otherChapters_ind.append(i)
            files.append(str(df['prefix'][i])+str(df['chapter'][i])+str(df['video'][i])+str(df['suffix'][i]))

        self.files_sorted = files
        self.firstChapters_ind = firstChapters_ind
        self.otherChapters_ind = otherChapters_ind

    def GetTimeStamps(self):

        timeStamps = []
        timeDeltas = []
        for i in range(len(self.files_sorted)):
            metaData = ffmpeg.probe(os.path.join(self.folder,self.files_sorted[i]))
            if i in self.firstChapters_ind:
                origin = datetime.datetime.strptime(metaData['streams'][0]['tags']['creation_time'], '%Y-%m-%dT%H:%M:%S.%fZ')
                timeStamp = datetime.datetime.strptime(metaData['streams'][0]['tags']['creation_time'], '%Y-%m-%dT%H:%M:%S.%fZ')
                duration =  datetime.timedelta(seconds=float(metaData['streams'][0]['duration']))
                timeSince = datetime.timedelta(seconds=float(metaData['streams'][0]['duration']))
                timeDeltas.append(datetime.timedelta(seconds=0))
                timeStamps.append(timeStamp)
            else:
                timeStamp = origin + timeSince
                duration =  datetime.timedelta(seconds=float(metaData['streams'][0]['duration']))
                timeDeltas.append(timeSince)
                timeStamps.append(timeStamp)
                timeSince = timeSince + duration
        self.timeStamps = timeStamps
        self.timeDeltas = timeDeltas

    def Write_CSV(self):
        with open(os.path.join(self.folder,'timeStamping.csv'), 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=',')
            writer.writerow(['File', 'TimeStamp', 'NjordOffset'])
            for i in range(len(self.timeStamps)):
                writer.writerow([self.files_sorted[i], str(self.timeStamps[i]), str(self.timeDeltas[i].seconds)+'.'+str(self.timeDeltas[i].microseconds) ])

        csvfile.close()

    def Add_CSV(self):
        self.GetFiles()
        self.SortFiles()
        self.GetTimeStamps()
        self.Write_CSV()

class SailTimeLapse:
    def __init__(self,path_mp4, sail):
        self.path_mp4 = path_mp4
        file, extension = os.path.splitext(self.path_mp4)
        self.extension = extension
        self.sail = sail

    def Get_TS_info(self):
        s=''
        fileList = list(os.path.split(self.path_mp4)[-1])
        year = int(s.join(fileList[0:4]))
        month = int(s.join(fileList[4:6]))
        day = int(s.join(fileList[6:8]))
        hour = int(s.join(fileList[9:11]))
        minute = int(s.join(fileList[11:13]))
        second = int(s.join(fileList[13:15]))
        timeStep = int(s.join(fileList[16:18]))

        self.timeLapse_endTime = datetime.datetime(year, month, day, hour, minute, second)
        self.timeLapse_timeStep = datetime.timedelta(seconds=timeStep)

    def Make_JPG(self):
        self.exportFolder = os.path.join(list(os.path.split(self.path_mp4))[0],'jpg')
        if not os.path.exists(self.exportFolder):
            os.makedirs(self.exportFolder)

        tl_capture = cv2.VideoCapture(self.path_mp4)
        image_counter = 0
        file_names = []
        while(tl_capture.isOpened()):
            ret,cv2_im = tl_capture.read()
            if not ret:
                tl_capture.release()
                break

            converted = cv2.cvtColor(cv2_im,cv2.COLOR_BGR2RGB)
            if self.sail == 'stbJib':
                converted = np.flip(converted,axis=0)
            if self.sail == 'stbMain':
                converted = np.flip(converted,axis=1)
            #if self.sail == 'portJib':
                #converted = np.flip(converted,axis=0)
                #converted = np.flip(converted,axis=1)

            pil_im = Image.fromarray(converted)
            fileName = str(image_counter)+str(self.timeLapse_endTime)+'.jpg'
            file_names.append(fileName)
            pil_im.save(os.path.join(self.exportFolder, fileName))
            image_counter += 1

        self.file_names = file_names


    def Update_TS(self):

        self.timeLapse_startTime = self.timeLapse_endTime - self.timeLapse_timeStep * len(self.file_names)
        for i in range(len(self.file_names)):
            timeStamp = self.timeLapse_startTime+self.timeLapse_timeStep*(i+1)
            timeStamp_str = (str(timeStamp.year)+':'+
                     str(timeStamp.month)+':'+
                     str(timeStamp.day)+(' ')+
                     str(timeStamp.hour)+':'+
                     str(timeStamp.minute)+':'+
                     str(timeStamp.second))

            exif_dict = {'0th': {306: bytes(timeStamp_str,encoding = 'utf-8')}}

            exif_bytes = piexif.dump(exif_dict)
            filePath = os.path.join(self.exportFolder,self.file_names[i])
            piexif.insert(exif_bytes, filePath)
            s = ''
            fileName_new = s.join(list(str(timeStamp.year)) + list(str('-')) + list(str(timeStamp.month)) +
                                  list(str('-')) + list(str(timeStamp.day)) +
                              list(str('_')) + list(str(timeStamp.hour)) +
                                  list(str('-')) + list(str(timeStamp.minute)) +
                                  list(str('-')) + list(str(timeStamp.second)) +
                                  list(str('_')) + list(str(self.sail)))
            fileName_new = os.path.join(self.exportFolder, fileName_new+str('.jpg'))
            os.rename(filePath,fileName_new)

    def TimeLapse_To_JPG(self):

        if (self.extension == '.mp4') or (self.extension == '.MP4'):
            self.Get_TS_info()
            self.Make_JPG()
            self.Update_TS()
            print(str(self.path_mp4)+ "Complete")

class Rename_GP_TimeLapse:
    def __init__(self,file,timeZone,timeStep):
        self.file = file
        self.timeZone = datetime.timedelta(hours=int(timeZone))
        self.timeStep = timeStep
        file, extension = os.path.splitext(self.file)
        self.extension = extension

    def Get_TS(self):
        metaData = ffmpeg.probe(self.file)
        startTime = datetime.datetime.strptime(metaData['streams'][0]['tags']['creation_time'], '%Y-%m-%dT%H:%M:%S.%fZ')
        frames = metaData['streams'][0]['nb_frames']
        runTime = datetime.timedelta(seconds=int(frames)*2)
        self.finishTime = startTime + runTime + self.timeZone

    def Change_File_Name(self):
        s=''
        year = str(self.finishTime.year)

        if len(str(self.finishTime.month)) < 2:
            month = s.join(['0',str(self.finishTime.month)])

        else:
            month = str(self.finishTime.day)

        if len(str(self.finishTime.day)) < 2:
            day = s.join(['0',str(self.finishTime.day)])

        else:
            day = str(self.finishTime.day)

        if len(str(self.finishTime.hour)) < 2:
            hour = s.join(['0',str(self.finishTime.hour)])

        else:
            hour = str(self.finishTime.hour)

        if len(str(self.finishTime.minute)) < 2:
            minute = s.join(['0',str(self.finishTime.minute)])

        else:
            minute = str(self.finishTime.minute)

        if len(str(self.finishTime.second)) < 2:
            second = s.join(['0',str(self.finishTime.second)])

        else:
            second = str(self.finishTime.second)

        if len(str(self.timeStep)) < 2:
            timeStep = s.join(['0',str(self.timeStep)])

        else:
            day = str(self.finishTime.day)

        fileName = s.join([year,month,day,'_',hour,minute,second,'_',timeStep,'.mp4'])
        directory = os.path.dirname(self.file)
        fileName = os.path.join(directory,fileName)
        os.rename(self.file,fileName)

    def Rename(self):
        if (self.extension == '.mp4') or (self.extension == '.MP4'):
            self.Get_TS()
            self.Change_File_Name()

class goPro_Import:
    def __init__(self,serialNo, destinationPath):
        self.serialNo = serialNo
        self.destinationPath = destinationPath

    def Download_hiResolution(self):
        async def main(gp) -> None:
            async with WiredGoPro(gp) as gopro:
                response = await (gopro.http_command.get_media_list())
                fileNames = []
                for i in range(len(response.data.media[0].file_system)):
                    fileNames.append(response.data.media[0].file_system[i].filename)

                for file in fileNames:
                    print('downloading: '+str(file)+' from: '+str(gp))
                await gopro.http_command.download_file(camera_file=file,file=self.destinationPath)

        asyncio.run(main(self.serialNo))

    def Download_LowResolution(self):
        async def main(gp) -> None:
            async with WiredGoPro(gp) as gopro:
                response = await (gopro.http_command.get_media_list())
                fileNames = []
                for i in range(len(response.data.media[0].file_system)):
                    filename = response.data.media[0].file_system[i].filename
                    filename = list(filename)
                    filename[-3:] = ['l','r','v']
                    filename = str(fileNames)
                    fileNames.append(response.data.media[0].file_system[i].filename)

                for file in fileNames:
                    print('downloading: '+str(file)+' from: '+str(gp))
                await gopro.http_command.download_file(camera_file=file,file=self.destinationPath)

        asyncio.run(main(self.serialNo))

class Filter_JPG:
    def __init__(self,path,timeStamps):
        self.path = path
        self.timeStamps = timeStamps

    def Remove_Files(self):
        files = os.listdir(self.path)
        fileTS = []
        for file in files:
            ts = piexif.load(os.path.join(self.path,file))['0th'][306]
            ts = datetime.datetime.strptime(ts.decode('UTF-8'), '%Y:%m:%d %H:%M:%S')
            fileTS.append(ts)
            if ts not in self.timeStamps:
                os.remove(os.path.join(self.path,file))









#%%
