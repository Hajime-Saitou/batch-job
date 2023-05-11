import subprocess
import threading
import time
import os

class JobRunningStatus:
    Ready = 0
    Running = 1
    Completed = 2

class JobManager:
    def __init__(self, logOutputPath=""):
        self.lock = threading.Lock()
        self.allJobRunningStatus = {}
        self.jobs = []
        self.logOutputPath = logOutputPath

    def entry(self, jobContexts):
        self.lock.acquire()
        self.allJobRunningStatus.clear()
        self.lock.release()

        self.jobs = []
        for context in jobContexts:
            job = Job()
            context["logOutputPath"] = self.logOutputPath
            job.entry(self, **context)
            self.jobs.append(job)

    def runAllReadyJobs(self):
        ready = [ job for job in self.jobs if job.ready() ]
        [ job.start() for job in ready ]

    def running(self):
        return len([ job for job in self.jobs if job.running() ]) >= 1

    def wait(self, interval=1):
        while self.running():
            time.sleep(interval)

    def completed(self):
        self.lock.acquire()
        completed = [ job for job in self.jobs if job.completed() ]
        self.lock.release()

        return len(completed) == len(self.jobs)

    def errorOccurred(self):
        return len([ job for job in self.jobs if job.completed() and job.exitCode != 0 ]) >= 1

class Job(threading.Thread):
    def entry(self, jobManager, id, commandLine="", waiting = [],  logOutputPath="./log"):
        self.jobManager = jobManager
        self.id = id
        self.commandLine = commandLine
        self.exitCode = 0
        self.waiting = waiting
        self.runningStatus = JobRunningStatus.Ready
        self.logOutputPath = logOutputPath

    @property
    def runningStatus(self):
        return self._runningStatus

    @runningStatus.setter
    def runningStatus(self, value):
        self._runningStatus = value

        self.jobManager.lock.acquire()
        self.jobManager.allJobRunningStatus[self.id] = value
        self.jobManager.lock.release()

    def ready(self):
        if self.runningStatus != JobRunningStatus.Ready:
            return False

        if not self.waiting:
            return True
        
        self.jobManager.lock.acquire()
        completed = [ job for job in self.jobManager.jobs if job.id in self.waiting and job.completed() and job.exitCode == 0 ]
        self.jobManager.lock.release()

        return len(completed) == len(self.waiting)

    def running(self):
        return self._runningStatus == JobRunningStatus.Running

    def completed(self):
        return self._runningStatus == JobRunningStatus.Completed

    def run(self):
        self.runningStatus = JobRunningStatus.Running
        completePocess = subprocess.run(self.commandLine, capture_output=True, text=True)
        self.exitCode = completePocess.returncode
        self.runningStatus = JobRunningStatus.Completed

        if not self.logOutputPath:
            return

        if not os.path.exists(self.logOutputPath):
            os.makedirs(self.logOutputPath)

        logFileName = os.path.join(self.logOutputPath, f"{self.id}.log")
        with open(logFileName, "w", encoding="utf-8") as f:
            f.writelines(completePocess.stdout)
