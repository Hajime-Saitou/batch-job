# simplejob
# https://github.com/Hajime-Saitou/simplejob
#
# Copyright (c) 2023 Hajime Saito
import subprocess
import threading
import time
import datetime
import enum
import os

class JobRunningStatus(enum.IntEnum):
    Ready = 0
    Running = 1
    Completed = 2
    RetryOut = 3

class SimpleJobManager:
    def __init__(self, logOutputDirectory=""):
        self.lock = threading.Lock()
        self.allJobRunningStatus = {}
        self.jobs = []
        self.logOutputDirecotry = logOutputDirectory

    def entry(self, jobContexts):
        self.join()

        self.lock.acquire()
        self.allJobRunningStatus.clear()
        self.lock.release()

        self.jobs = []
        for context in jobContexts:
            if context["id"] in self.allJobRunningStatus.keys():
                raise ValueError(f"Duplicate key. id: {context['id']}")

            job = SimpleJob()
            context["jobManager"] = self
            context["logOutputDirectory"] = self.logOutputDirecotry
            job.entry(**context)
            self.jobs.append(job)

    def runAllReadyJobs(self):
        ready = [ job for job in self.jobs if job.ready() ]
        [ job.start() for job in ready ]

    def running(self):
        return len([ job for job in self.jobs if job.running() ]) >= 1

    def join(self, interval=1):
        while self.running():
            time.sleep(interval)

    def completed(self):
        self.lock.acquire()
        completed = [ job for job in self.jobs if job.completed() ]
        self.lock.release()

        return len(completed) == len(self.jobs)

    def errorOccurred(self):
        return len([ job for job in self.jobs if job.completed() and job.exitCode != 0 ]) >= 1
    
    def report(self):
        report = { "results": [] }
        for job in self.jobs:
            report["results"].append({ job.id: job.report() })

        return report

class SimpleJob(threading.Thread):
    def entry(self, commandLine, id="", timeout=None, retry=1, delay=0,backoff=1, waiting = [], logOutputDirectory="", jobManager=None):
        self.commandLine = commandLine
        self.id = id if id != "" else self.__getBaseNameWithoutExtension(self.commandLine.split(' ')[0])
        self.waiting = waiting
        self.logOutputDirectory = logOutputDirectory
        self.logFileName = "" if not self.logOutputDirectory else os.path.join(self.logOutputDirectory, f"{self.id}.log")
        self.jobManager = jobManager
        self.exitCode = None
        self.runningStatus = JobRunningStatus.Ready
        self.startDateTime = None
        self.finishDateTime = None

        # retry parameters
        self.retry = retry
        self.timeout = timeout
        self.delay = delay
        self.backoff = backoff
        self.retried = 0

    def __getBaseNameWithoutExtension(self, filename):
        return f"{os.path.basename(filename).split('.')[0]}"

    @property
    def runningStatus(self):
        return self._runningStatus

    @runningStatus.setter
    def runningStatus(self, value):
        self._runningStatus = value

        if self.jobManager:
            self.jobManager.lock.acquire()
            self.jobManager.allJobRunningStatus[self.id] = value
            self.jobManager.lock.release()

    def ready(self):
        if self.runningStatus != JobRunningStatus.Ready:
            return False

        if not self.waiting:
            return True
        
        if self.jobManager:
            self.jobManager.lock.acquire()
            completed = [ job for job in self.jobManager.jobs if job.id in self.waiting and job.completed() and job.exitCode == 0 ]
            self.jobManager.lock.release()

            return len(completed) == len(self.waiting)

    def running(self):
        return self._runningStatus == JobRunningStatus.Running

    def completed(self):
        return self._runningStatus in [ JobRunningStatus.Completed, JobRunningStatus.RetryOut ]

    def run(self):
        self.runningStatus = JobRunningStatus.Running
        self.startDateTime = datetime.datetime.now()

        for trialCounter in range(0, self.retry + 1):
            try:
                completePocess = subprocess.run(self.commandLine, capture_output=True, text=True, timeout=self.timeout)
                self.writeLog(completePocess.stdout)
            except subprocess.TimeoutExpired as e:
                self.writeLog(e.output)
                self.writeLog(f"Error: Timed out({trialCounter}/{self.retry})")

                self.retried = trialCounter
                time.sleep((trialCounter + 1) ** self.backoff + self.delay)       # Exponential backoff
            else:
                self.finishDateTime = datetime.datetime.now()
                self.exitCode = completePocess.returncode               # latest return code
                self.runningStatus = JobRunningStatus.Completed
                return

        self.finishDateTime = datetime.datetime.now()
        self.runningStatus = JobRunningStatus.RetryOut

    def writeLog(self, text):
        if not self.logOutputDirectory:
            return

        with open(self.logFileName, "a", encoding="utf-8") as f:
            f.writelines(text)

    def report(self):
        return {
            "runnigStatus": self.runningStatus.name,
            "retried": self.retried,
            "exitCode": self.exitCode  if self.exitCode is not None else "",
            "startDateTime": self.startDateTime.strftime('%Y/%m/%d %H:%M:%S.%f') if self.startDateTime is not None else "",
            "finishDateTime": self.finishDateTime.strftime('%Y/%m/%d %H:%M:%S.%f') if self.finishDateTime is not None else "",
            "elapsedTime": self.__timedeltaToStr(self.finishDateTime - self.startDateTime) if self.finishDateTime is not None else ""
        }

    def __timedeltaToStr(self, delta):
        totalSeconds = delta.total_seconds()
        hours = int(totalSeconds / 3600)
        totalSeconds -= hours * 3600
        minutes = int(totalSeconds / 60)
        totalSeconds -= minutes * 60
        seconds = int(totalSeconds)
        totalSeconds -= seconds
        totalSeconds *= 1000000

        return f"{hours:02}:{minutes:02}:{seconds:02}.{int(totalSeconds)}"