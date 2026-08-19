; Remove only the legacy directory junction before electron-builder recursively
; removes the installation directory. `rmdir` without /S removes a junction
; itself and never traverses into the Electron userData target.
!macro customInit
  nsExec::ExecToLog '"$SYSDIR\cmd.exe" /C rmdir "$INSTDIR\resources\backend\_internal\data"'
!macroend

!macro customUnInit
  nsExec::ExecToLog '"$SYSDIR\cmd.exe" /C rmdir "$INSTDIR\resources\backend\_internal\data"'
!macroend
