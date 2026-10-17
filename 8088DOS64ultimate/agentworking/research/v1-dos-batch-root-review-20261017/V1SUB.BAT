@ECHO OFF
ECHO %1>C:\V1WORK\ARGS.TXT
SHIFT
ECHO %1>>C:\V1WORK\ARGS.TXT
REM The following marker requires return to the parent batch.
ECHO SUB_OK>>C:\V1.LOG
