# simplejob
# https://github.com/Hajime-Saitou/simplejob
#
# Copyright (c) 2023 Hajime Saito
# MIT License
import subprocess
import threading
import time
from datetime import datetime, timedelta
import enum
import os
import uuid
from collections import Counter

class JobRunningStatus(enum.IntEnum):
    Ready = 0
    Running = 1
    Completed = 2
    RetryOut = 3

class SimpleJobManager:
    def __init__(self, logOutputDirectory:str="") -> None:
        self.lock:threading.Lock = threading.Lock()
        self.allJobRunningStatus:dict = {}
        self.jobs:list = []
        self.logOutputDirecotry:str = logOutputDirectory

    def checkDuplicatedIds(self, jobContexts:list):
        dupKeys = [ key for ( key, value ) in Counter([ context["id"] for context in jobContexts ]).items() if value > 1 ]
        if len(dupKeys) > 0:
            raise ValueError(f"Id duplicated. ids={dupKeys}")

    def checkCircularReferencedIds(self, jobContexts:list):
        def traceGraph(id, graph, visited=None) -> bool:
            if not visited:
                visited = set()

            visited.add(id)

            for neighbor in graph.get(id, []):
                if neighbor in visited or traceGraph(neighbor, graph, visited):
                    return True

            visited.remove(id)
            return False

        graph = { context["id"]: context.get("waiting", []) for context in jobContexts }
        circularIds = []
        for id in graph:
            if traceGraph(id, graph, None):
                circularIds.append(id)

        if len(circularIds) > 0:
            raise ValueError(f"Circular referenced. ids={circularIds}")

    def entry(self, jobContexts:list) -> None:
        self.checkDuplicatedIds(jobContexts)
        self.checkCircularReferencedIds(jobContexts)

        self.join()

        self.lock.acquire()
        self.allJobRunningStatus.clear()
        self.lock.release()

        self.jobs.clear()
        for context in jobContexts:
            job = SimpleJob()
            context["jobManager"] = self
            context["logOutputDirectory"] = self.logOutputDirecotry
            job.entry(**context)
            self.jobs.append(job)

    def runAllReadyJobs(self) -> None:
        [ job.start() for job in self.jobs if job.ready() ]

    def running(self) -> bool:
        return len([ job for job in self.jobs if job.running() ]) >= 1

    def join(self, interval:int=1) -> None:
        while self.running():
            time.sleep(interval)

    def completed(self) -> bool:
        return len([ job for job in self.jobs if job.completed() ]) == len(self.jobs)

    def errorOccurred(self) -> bool:
        return len([ job for job in self.jobs if job.completed() and job.hasError() ]) >= 1

    def report(self) -> dict:
        report = { "results": [] }
        for job in self.jobs:
            report["results"].append({ job.id: job.report() })

        return report

class SimpleJob(threading.Thread):
    def entry(self, commandLine:str, id:str="", timeout:int=None, retry:int=1, delay:int=0, backoff:int=1, waiting:list = [], logOutputDirectory:str="", jobManager:SimpleJobManager=None) -> None:
        if not jobManager and len(waiting) > 0:
            raise ValueError("Waiting list can set the JobManager together.")

        self.commandLine:str = commandLine
        self.id:str = id if id != "" else uuid.uuid4()
        self.waiting:list = waiting
        self.logOutputDirectory:str = logOutputDirectory
        self.logFileName:str = "" if not self.logOutputDirectory else os.path.join(self.logOutputDirectory, f"{self.id}.log")
        self.jobManager:SimpleJobManager = jobManager
        self.exitCode:int = 0
        self.runningStatus:JobRunningStatus = JobRunningStatus.Ready
        self.startDateTime:datetime = None
        self.finishDateTime:datetime = None

        # retry parameters
        self.retry:int = retry
        self.timeout:int = timeout
        self.delay:int = delay
        self.backoff:int = backoff
        self.retried:int = 0

    @property
    def runningStatus(self) -> JobRunningStatus:
        return self._runningStatus

    @runningStatus.setter
    def runningStatus(self, value:JobRunningStatus) -> None:
        self._runningStatus = value

        if self.jobManager:
            self.jobManager.lock.acquire()
            self.jobManager.allJobRunningStatus[self.id] = value
            self.jobManager.lock.release()

    def hasError(self) -> bool:
        return self.exitCode != 0

    def ready(self) -> bool:
        if self.runningStatus != JobRunningStatus.Ready:
            return False

        if not self.waiting:
            return True
        
        if self.jobManager:
            self.jobManager.lock.acquire()
            completed = [ job for job in self.jobManager.jobs if job.id in self.waiting and job.completed() and not job.hasError() ]
            self.jobManager.lock.release()

            return len(completed) == len(self.waiting)

    def running(self) -> JobRunningStatus:
        return self._runningStatus == JobRunningStatus.Running

    def completed(self) -> bool:
        return self._runningStatus in [ JobRunningStatus.Completed, JobRunningStatus.RetryOut ]

    def run(self) -> None:
        self.runningStatus = JobRunningStatus.Running
        self.startDateTime = datetime.now()

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
                self.finishDateTime = datetime.now()
                self.exitCode = completePocess.returncode               # latest return code
                self.runningStatus = JobRunningStatus.Completed
                return

        self.exitCode = None
        self.finishDateTime = datetime.now()
        self.runningStatus = JobRunningStatus.RetryOut

    def writeLog(self, text) -> None:
        if not self.logOutputDirectory:
            return

        with open(self.logFileName, "a", encoding="utf-8") as f:
            f.writelines(text)

    def report(self) -> dict:
        return {
            "runnigStatus": self.runningStatus.name,
            "retried": self.retried if self.timeout is not None else None,
            "exitCode": self.exitCode  if self.completed() else None,
            "startDateTime": self.startDateTime.strftime('%Y/%m/%d %H:%M:%S.%f') if self.startDateTime is not None else None,
            "finishDateTime": self.finishDateTime.strftime('%Y/%m/%d %H:%M:%S.%f') if self.finishDateTime is not None else None,
            "elapsedTime": self.__timedeltaToStr(self.finishDateTime - self.startDateTime) if self.finishDateTime is not None else None
        }

    def __timedeltaToStr(self, delta:timedelta) -> str:
        totalSeconds = delta.total_seconds()
        hours = int(totalSeconds / 3600)
        totalSeconds -= hours * 3600
        minutes = int(totalSeconds / 60)
        totalSeconds -= minutes * 60
        seconds = int(totalSeconds)
        totalSeconds -= seconds
        totalSeconds *= 1000000

        return f"{hours:02}:{minutes:02}:{seconds:02}.{int(totalSeconds)}"
