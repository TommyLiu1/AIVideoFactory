@echo off
_internal\Scripts\rq.exe worker runway_generate_videos_queue --worker-class rq_win.WindowsWorker 
pause