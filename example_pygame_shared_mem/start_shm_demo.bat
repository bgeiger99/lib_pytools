@REM pushd %~dp1
echo WINPYDIR = %WINPYDIR%
call %WINPYDIR%\..\scripts\env.bat   


rem remove the /min option to see error printouts on startup
set START_CMD=start 
rem set START_CMD=start  /min



echo "Starting app1..."
%START_CMD% python app1.py 

echo "Starting app2..."
%START_CMD% python app2.py 



timeout /t 10