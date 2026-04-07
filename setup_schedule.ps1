$action = New-ScheduledTaskAction -Execute "pythonw.exe" -Argument "c:\Users\hspt8\Desktop\test\sales_report_app\kapt_reserve_sync.py" -WorkingDirectory "c:\Users\hspt8\Desktop\test\sales_report_app"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 9:00AM
# Remove existing task if any
Unregister-ScheduledTask -TaskName "Kapt_Reserve_Sync" -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "Kapt_Reserve_Sync" -Description "K-apt Auto Sync Task"
