# simplejob
This is simple job execution module.

# Overview
You can execute job with relationship using this module. Job execution time can be delayed until other jobs are finished.

# Getting Started

## install package

```
pip install simplejob
```

## Run with the JobManager class

If you want to run a related many jobs, use the JobManager class.

At first, import the JobManager from this module.

```
from simplejob.simplejob import SimpleJobManager
```

Prepare a job context consisting of job parameters and pass it as an argument to JobManager.entry().

id ... Job ID (arbitrary name, if omitted, the base name of the first command line argument)
command line ... command to execute and command line parameters
Waiting list of other job IDs ... List of job IDs waiting to run

```
jobContexts = [
    { "id": "hoge", "commandLine": r"timeout /t 1 /nobreak" },
    { "id": "piyo", "commandLine": r"timeout /t 3 /nobreak", "waits": [ "hoge" ] },
    { "id": "fuga", "commandLine": r"timeout /t 5 /nobreak", "waits": [ "hoge" ] },
    { "id": "moga", "commandLine": r"timeout /t 2 /nobreak", "waits": [ "piyo", "fuga" ] },
]
jobManager = SimpleJobManager()
jobManager.entry(jobContexts)
```

Run all jobs through JobManager.runAllReadyJobs() until all jobs are finished or an error occurs. If necessary, call an interval timer in the loop. The example calls a 1 second interval timer.

```
while True:
    jobManager.runAllReadyJobs()
    if jobManager.errorOccurred():
        print("error occurred")
        jobManager.join()
        break

    if jobManager.completed():
        break

    time.sleep(1)
```

It can be written on a single line using wait(). If error occred in the wait(), Raise CalledJobException.

```
jobManager.wait()
```

### report

You can output the execution result as a report by calling report(). Returns an empty result for jobs that have not run.

Example for SimpleJobManager.report()

```
{
    "results": [
        {
            "hoge": {
                "runnigStatus": "Completed",
                "exitCode": 0,
                "retried": null,
                "commandLine": "timeout /t 1 /nobreak",
                "startDateTime": "2023/05/27 05:42:16.595910",
                "finishDateTime": "2023/05/27 05:42:17.172984",
                "elapsedTime": "00:00:00.580679"
            }
        },
        {
            "piyo": {
                "runnigStatus": "Completed",
                "exitCode": 0,
                "retried": null,
                "commandLine": "timeout /t 3 /nobreak",
                "startDateTime": "2023/05/27 05:42:17.589688",
                "finishDateTime": "2023/05/27 05:42:20.131554",
                "elapsedTime": "00:00:02.537245"
            }
        },
        {
            "fuga": {
                "runnigStatus": "Completed",
                "exitCode": 0,
                "retried": null,
                "commandLine": "timeout /t 1 /nobreak",
                "startDateTime": "2023/05/27 05:42:17.597681",
                "finishDateTime": "2023/05/27 05:42:18.177357",
                "elapsedTime": "00:00:00.584966"
            }
        },
        {
            "moga": {
                "runnigStatus": "Completed",
                "exitCode": 0,
                "retried": null,
                "commandLine": "timeout /t 2 /nobreak",
                "startDateTime": "2023/05/27 05:42:20.636437",
                "finishDateTime": "2023/05/27 05:42:22.192478",
                "elapsedTime": "00:00:01.556920"
            }
        }
    ]
}
```

### Retry on timed out
If the job fails by timed out, it can be retried. The retry parameters are as follows.Retry parameters can be set for individual jobs.

retry ... Retry count (default is 0, no retry)
timeout ... Number of seconds to timeout the job (default is None, no timeout)
delay ... number of seconds to delay the job on retry (default 0, no delay)
backkoff ... power to back off the retry interval (default 1)

The report for a failed retry is shown below.

```
{
    "runnigStatus": "RetryOut",
    "exitCode": null,
    "retried": 1,
    "commandLine": "timeout /t 2 /nobreak",
    "startDateTime": "2023/05/18 21:47:38.528989",
    "finishDateTime": "2023/05/18 21:47:43.594701",
    "elapsedTime": "00:00:05.65712"
}
```

### rerun

After the cause of the error has been resolved, the job can be rerun using rerun(). The remaining jobs use wait() to run the job until all jobs have finished or until the error occurs again.

```
jobManager.rerun()
jobManager.wait()
```

## Output the job log

To output logs, specify the logOutputDirectory parameter to constructor of SimpleJobManager class. The log file name is the job id with a "log" extension.

```
jobManager = SimpleJobManager(r"C:\temp\log")
```
