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
        self.jobContexts = None

    def detectDuplicatedIds(self, jobContexts:list) -> list:
        return [ key for ( key, value ) in Counter([ context["id"] for context in jobContexts ]).items() if value > 1 ]

    def detectCircularReferencedIds(self, jobContexts:list) -> list:
        def traceGraph(id, graph, visited=set()) -> bool:
            visited.add(id)

            for neighbor in graph.get(id, []):
                if neighbor in visited or traceGraph(neighbor, graph, visited):
                    return True

            visited.remove(id)
            return False

        graph = { context["id"]: context.get("waits", []) for context in jobContexts }
        return [ id for id in graph.keys() if traceGraph(id, graph) ]
    
    def detectInvalidWaitsIds(self, jobContexts:list) -> list:
        ids = { context["id"] for context in jobContexts }
        waitsIds = { id for context in jobContexts for id in context.get("waits", []) }
        return waitsIds - ids
    
    def detectInvalidIds(self, jobContexts:list) -> list:
        return [ index for index, context in enumerate(jobContexts) if not context.get("id", None) ]

    def entry(self, jobContexts:list) -> None:
        elementIndices = self.detectInvalidIds(jobContexts)
        if len(elementIndices) > 0:
            raise ValueError(f"Invalid Id detected. element indices={elementIndices}")

        invalidWaitsIds = self.detectInvalidWaitsIds(jobContexts)
        if len(invalidWaitsIds) > 0:
            raise ValueError(f"Invalid waits. ids.={invalidWaitsIds}")

        dupKeys = self.detectDuplicatedIds(jobContexts)
        if len(dupKeys) > 0:
            raise ValueError(f"Id duplicated. ids={dupKeys}")

        circularIds = self.detectCircularReferencedIds(jobContexts)
        if len(circularIds) > 0:
            raise ValueError(f"Circular referenced. ids={circularIds}")

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

        self.jobContexts = jobContexts

    def rerun(self):
        self.join()

        for index, job in enumerate(self.jobs):
            if not job.hasError():
                continue

            job = SimpleJob()
            context = self.jobContexts[index]
            context["jobManager"] = self
            context["logOutputDirectory"] = self.logOutputDirecotry
            job.entry(**context)
            self.jobs[index] = job

    def runAllReadyJobs(self) -> None:
        [ job.start() for job in self.jobs if job.ready() and not job.ident]

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

    def getRunningStatus(self):
        return Counter([ job.runningStatus.name for job in self.jobs ])

class SimpleJob(threading.Thread):
    def entry(self, commandLine:str, id:str="", timeout:int=None, retry:int=1, delay:int=0, backoff:int=1, waits:list = [], logOutputDirectory:str="", jobManager:SimpleJobManager=None) -> None:
        if not jobManager and len(waits) > 0:
            raise ValueError("waits list can set the JobManager together.")

        self.commandLine:str = commandLine
        self.id:str = id if id != "" else uuid.uuid4()
        self.waits:list = waits
        self.logOutputDirectory:str = logOutputDirectory
        self.logFileName:str = "" if not self.logOutputDirectory else os.path.join(self.logOutputDirectory, f"{self.id}.log")
        self.jobManager:SimpleJobManager = jobManager
        self.exitCode:int = 0
        self.runningStatus:JobRunningStatus = JobRunningStatus.Ready
        self.startDateTime:datetime = None
        self.finishDateTime:datetime = None
        self.startTime:float = 0
        self.finishTime:float = 0

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

        if not self.waits:
            return True
        
        if self.jobManager:
            self.jobManager.lock.acquire()
            completed = [ job for job in self.jobManager.jobs if job.id in self.waits and job.completed() and not job.hasError() ]
            self.jobManager.lock.release()

            return len(completed) == len(self.waits)

    def running(self) -> JobRunningStatus:
        return self._runningStatus == JobRunningStatus.Running

    def completed(self) -> bool:
        return self._runningStatus in [ JobRunningStatus.Completed, JobRunningStatus.RetryOut ]

    def run(self) -> None:
        self.runningStatus = JobRunningStatus.Running
        self.startTime = time.perf_counter()
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
                self.exitCode = completePocess.returncode               # latest return code
                self.runningStatus = JobRunningStatus.Completed
                self.finishDateTime = datetime.now()
                self.finishTime = time.perf_counter()
                return

        self.exitCode = None
        self.runningStatus = JobRunningStatus.RetryOut
        self.finishDateTime = datetime.now()
        self.finishTime = time.perf_counter()

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
            "elapsedTime": self.getElapsedTime()
        }

    def getElapsedTime(self) -> str:
        totalMilleSeconds = self.finishTime - self.startTime
        if totalMilleSeconds == 0:
            return None

        hours = int(totalMilleSeconds / 3600)
        totalMilleSeconds -= hours * 3600
        minutes = int(totalMilleSeconds / 60)
        totalMilleSeconds -= minutes * 60
        seconds = int(totalMilleSeconds)
        totalMilleSeconds -= seconds
        totalMilleSeconds *= 1000000

        return f"{hours:02}:{minutes:02}:{seconds:02}.{int(totalMilleSeconds)}"
