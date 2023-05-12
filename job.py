import subprocess
import threading
import time
import os

class JobRunningStatus:
    Ready = 0
    Running = 1
    Completed = 2

class JobManager:
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

            job = Job()
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

class Job(threading.Thread):
    def entry(self, commandLine, id="", waiting = [], logOutputDirectory="", jobManager=None):
        self.commandLine = commandLine
        self.id = id if id != "" else self.__getBaseNameWithoutExtension(self.commandLine.split(' ')[0])
        self.waiting = waiting
        self.logOutputDirectory = logOutputDirectory
        self.jobManager = jobManager
        self.exitCode = 0
        self.runningStatus = JobRunningStatus.Ready

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
        return self._runningStatus == JobRunningStatus.Completed

    def run(self):
        self.runningStatus = JobRunningStatus.Running
        completePocess = subprocess.run(self.commandLine, capture_output=True, text=True)
        self.exitCode = completePocess.returncode
        self.runningStatus = JobRunningStatus.Completed

        if self.logOutputDirectory:
            if not os.path.exists(self.logOutputDirectory):
                os.makedirs(self.logOutputDirectory)

            logFileName = os.path.join(self.logOutputDirectory, f"{self.id}.log")
            with open(logFileName, "w", encoding="utf-8") as f:
                f.writelines(completePocess.stdout)
